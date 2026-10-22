"""Package sources, model provenance and evidence using an explicit allowlist."""

import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = {"apps", "services", "infra", "scripts", "tests", "docs", "security", ".github"}
ROOT_FILES = {
    "README.md",
    "compose.yaml",
    "project.json",
    "pyproject.toml",
    ".env.example",
    ".gitignore",
    ".gitattributes",
    ".dockerignore",
    ".editorconfig",
    ".sops.yaml",
    "requirements-dev.in",
    "requirements-dev.lock",
}
EXCLUDED = {"node_modules", "dist", "__pycache__", ".pytest_cache", ".ruff_cache", ".pio"}


def package():
    project = json.loads((ROOT / "project.json").read_text(encoding="utf-8"))
    evidence = ROOT / "output/evidence"
    recovery = json.loads((evidence / "recovery.json").read_text())
    security = json.loads((evidence / "security.json").read_text())
    if not recovery["passed"] or not all(security.values()):
        raise RuntimeError("Passing recovery and security evidence required")
    subprocess.run(
        ["docker", "compose", "cp", "supervisor:/state/model", str(evidence)],
        cwd=ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    output = ROOT / "output" / project["delivery_slug"]
    output.mkdir(parents=True, exist_ok=True)
    archive = output / (project["delivery_slug"] + "-Code.zip")
    entries = []
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if path.is_symlink() or not path.is_file() or EXCLUDED.intersection(relative.parts):
            continue
        if relative.as_posix() == "infra/esp8266/include/lab_config.h":
            continue
        if relative.parts[0] in DIRECTORIES or relative.as_posix() in ROOT_FILES:
            entries.append((path, Path("resilience-alpha") / relative))
    for path in evidence.rglob("*"):
        if (
            path.is_file()
            and path.suffix in {".json", ".png", ".joblib"}
            and path.name != "delivery-readiness.json"
        ):
            entries.append((path, Path("resilience-alpha/evidence") / path.relative_to(evidence)))
    # Match complete real secret values, never print their values on a failure.
    sensitive = []
    for name in [
        "camera_key",
        "camera_tls_key",
        "device_key",
        "demo_password",
        "postgres_password",
        "grafana_password",
        "jwt_private_key",
        "recovery_password",
        "remediation_key",
        "tls_key",
        "lab.agekey",
    ]:
        path = ROOT / ".secrets" / name
        if path.exists():
            sensitive.append((name, path.read_text().strip().encode()))
            if name == "lab.agekey":
                sensitive.extend(
                    (name, line.encode())
                    for line in path.read_text().splitlines()
                    if line.startswith("AGE-SECRET-KEY-")
                )
    manifest = {}
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for source, target in sorted(entries, key=lambda entry: str(entry[1])):
            content = source.read_bytes()
            for name, value in sensitive:
                if value and value in content:
                    raise RuntimeError(f"Plaintext secret {name} found in {target}")
            bundle.writestr(target.as_posix(), content)
            manifest[target.as_posix()] = hashlib.sha256(content).hexdigest()
        bundle.writestr("resilience-alpha/MANIFEST.sha256.json", json.dumps(manifest, indent=2))
    with zipfile.ZipFile(archive) as bundle:
        if bundle.testzip() is not None:
            raise RuntimeError("ZIP integrity test failed")
    (output / "README-RENDU.txt").write_text(
        "Groupe 3.\n"
        "Dossier PDF et présentation PPTX : résultats de recette locale en conteneurs.\n"
        "Code ZIP : sources, déploiement, modèle/provenance et preuves ; aucun secret en clair.\n"
        "La clé age privée n'est pas incluse. Le setup peut générer de nouveaux secrets.\n"
        "À réaliser sur les machines du groupe : essai du second PC, réseau, vidéo continue.\n"
        "Travaux attribués : docs/contributions.md ; validation personnelle à confirmer.\n"
        "Recette terrain : docs/recette-terrain.md ; pitch : docs/soutenance.md.\n"
        "Contrôle final : python scripts/delivery_check.py (mode --strict avant remise).\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "archive": str(archive),
                "files": len(manifest),
                "plaintext_secrets_check": "passed",
                "zip_integrity": "passed",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    package()
