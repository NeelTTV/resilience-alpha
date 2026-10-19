"""Generate local, ignored lab secrets without printing their values."""
import hashlib
import secrets
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
directory = ROOT / ".secrets"
directory.mkdir(exist_ok=True)


def create(name, value):
    path = directory / name
    if not path.exists():
        path.write_bytes((value + "\n").encode("utf-8"))
        path.chmod(0o600)


create("postgres_password", secrets.token_urlsafe(32))
create("jwt_secret", secrets.token_urlsafe(64))
create("grafana_password", secrets.token_urlsafe(24))
create("demo_password", secrets.token_urlsafe(18))
password = (directory / "demo_password").read_text().strip()
salt = secrets.token_bytes(16)
hashed = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1).hex()
create("demo_password_hash", salt.hex() + ":" + hashed)
if not (ROOT / ".env").exists():
    shutil.copyfile(ROOT / ".env.example", ROOT / ".env")
print("Local configuration ready. Credentials are in .secrets/ (never commit or archive).")

