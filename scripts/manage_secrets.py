"""SOPS/age workflow. Plaintext and the private age key stay in ignored .secrets/."""

import argparse
import hashlib
import io
import json
import os
import platform
import shutil
import subprocess
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / ".tools"
SECRET_DIR = ROOT / ".secrets"
BUNDLE = ROOT / "security/secrets.enc.json"
NAMES = [
    "postgres_password",
    "grafana_password",
    "jwt_private_key",
    "jwt_public_key",
    "demo_password",
    "demo_password_hash",
    "recovery_password",
    "recovery_password_hash",
    "remediation_key",
    "tls_cert",
    "tls_key",
]


def download_asset(repo, tag, name):
    req = Request(
        f"https://api.github.com/repos/{repo}/releases/tags/{tag}",
        headers={"User-Agent": "resilience-alpha-setup"},
    )
    with urlopen(req, timeout=30) as response:
        release = json.load(response)
    asset = next(a for a in release["assets"] if a["name"] == name)
    with urlopen(asset["browser_download_url"], timeout=90) as response:
        data = response.read()
    digest = asset.get("digest", "")
    if digest != "sha256:" + hashlib.sha256(data).hexdigest():
        raise RuntimeError("Release asset SHA256 missing or mismatched; refusing to execute")
    return data


def bootstrap():
    if platform.system() != "Windows":
        raise SystemExit(
            "Install sops and age using your OS package manager, then run encrypt/decrypt"
        )
    TOOLS.mkdir(exist_ok=True)
    (TOOLS / "sops.exe").write_bytes(
        download_asset(
            "getsops/sops",
            "v3.13.3",
            "sops-v3.13.3.amd64.exe",
        )
    )
    archive = download_asset("FiloSottile/age", "v1.3.2", "age-v1.3.2-windows-amd64.zip")
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        entry = next(n for n in bundle.namelist() if n.endswith("/age-keygen.exe"))
        (TOOLS / "age-keygen.exe").write_bytes(bundle.read(entry))
    print("SOPS and age installed in .tools/ with verified release-asset SHA256 digests.")


def executable(name):
    local = TOOLS / (name + (".exe" if os.name == "nt" else ""))
    result = str(local) if local.exists() else shutil.which(name)
    if not result:
        raise SystemExit("Missing " + name + "; run: python scripts/manage_secrets.py bootstrap")
    return result


def run_sops(*args):
    environment = {**os.environ, "SOPS_AGE_KEY_FILE": str(SECRET_DIR / "lab.agekey")}
    return subprocess.check_output([executable("sops"), *args], cwd=ROOT, env=environment)


def encrypt():
    key = SECRET_DIR / "lab.agekey"
    if not key.exists():
        subprocess.run(
            [executable("age-keygen"), "-o", str(key)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        key.chmod(0o600)
    recipient = subprocess.check_output([executable("age-keygen"), "-y", str(key)]).decode().strip()
    (ROOT / ".sops.yaml").write_text(
        f"creation_rules:\n  - path_regex: 'secrets\\.enc\\.json$'\n    age: '{recipient}'\n",
        encoding="utf-8",
    )
    values = {name: (SECRET_DIR / name).read_text().strip() for name in NAMES}
    temporary = SECRET_DIR / "bundle.json"
    try:
        temporary.write_text(json.dumps(values), encoding="utf-8")
        encrypted = run_sops(
            "encrypt",
            "--filename-override",
            "security/secrets.enc.json",
            "--age",
            recipient,
            "--input-type",
            "json",
            "--output-type",
            "json",
            str(temporary),
        )
        BUNDLE.write_bytes(encrypted)
        decoded = json.loads(run_sops("decrypt", str(BUNDLE)))
        if decoded != values:
            raise RuntimeError("Encrypted bundle did not round-trip")
    finally:
        temporary.unlink(missing_ok=True)
    print(
        "Encrypted bundle verified. Private key stays in .secrets/lab.agekey, outside the archive."
    )


def decrypt():
    values = json.loads(run_sops("decrypt", str(BUNDLE)))
    if set(values) != set(NAMES):
        raise ValueError("Unexpected secret names")
    SECRET_DIR.mkdir(exist_ok=True)
    SECRET_DIR.chmod(0o700)
    for name, value in values.items():
        path = SECRET_DIR / name
        # Avoid silently replacing a machine's active credentials/database password.
        if path.exists() and path.read_text().strip() != value:
            raise RuntimeError(f"Refusing to replace existing local secret: {name}")
    for name, value in values.items():
        path = SECRET_DIR / name
        path.write_bytes((value + "\n").encode())
        path.chmod(0o640)
    print("Secrets restored into ignored .secrets/. No credentials printed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["bootstrap", "encrypt", "decrypt"])
    args = parser.parse_args()
    {"bootstrap": bootstrap, "encrypt": encrypt, "decrypt": decrypt}[args.action]()
