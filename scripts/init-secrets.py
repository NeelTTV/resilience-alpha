"""Generate local, ignored lab secrets without printing their values."""

import hashlib
import ipaddress
import os
import secrets
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

ROOT = Path(__file__).resolve().parents[1]
directory = ROOT / ".secrets"
directory.mkdir(exist_ok=True)
directory.chmod(0o700)


def create(name, value):
    path = directory / name
    if not path.exists():
        path.write_bytes((value + "\n").encode("utf-8"))
        path.chmod(0o640)


create("postgres_password", secrets.token_urlsafe(32))
create("grafana_password", secrets.token_urlsafe(24))
create("remediation_key", secrets.token_urlsafe(48))
create("recovery_password", secrets.token_urlsafe(24))
create("demo_password", secrets.token_urlsafe(18))
password = (directory / "demo_password").read_text().strip()
salt = secrets.token_bytes(16)
hashed = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1).hex()
create("demo_password_hash", salt.hex() + ":" + hashed)
recovery = (directory / "recovery_password").read_text().strip()
recovery_salt = secrets.token_bytes(16)
create(
    "recovery_password_hash",
    recovery_salt.hex()
    + ":"
    + hashlib.scrypt(
        recovery.encode(),
        salt=recovery_salt,
        n=16384,
        r=8,
        p=1,
    ).hex(),
)
if not (directory / "jwt_private_key").exists():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    create(
        "jwt_private_key",
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        .decode()
        .strip(),
    )
    create(
        "jwt_public_key",
        key.public_key()
        .public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
        .strip(),
    )
if not (directory / "tls_key").exists():
    tls_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Resilience Alpha Lab")])
    now = datetime.now(timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(tls_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=90))
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("localhost"),
                    x509.DNSName("waf"),
                    x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
                    x509.IPAddress(ipaddress.ip_address("192.168.137.1")),
                ]
            ),
            critical=False,
        )
        .sign(tls_key, hashes.SHA256())
    )
    create(
        "tls_key",
        tls_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        .decode()
        .strip(),
    )
    create("tls_cert", certificate.public_bytes(serialization.Encoding.PEM).decode().strip())
if not (ROOT / ".env").exists():
    shutil.copyfile(ROOT / ".env.example", ROOT / ".env")
environment_path = ROOT / ".env"
environment_text = environment_path.read_text(encoding="utf-8")
if "SECRET_GID=" not in environment_text:
    with environment_path.open("a", encoding="utf-8") as stream:
        stream.write(f"\nSECRET_GID={os.getgid() if hasattr(os, 'getgid') else 0}\n")
print("Local configuration ready. Credentials are in .secrets/ (never commit or archive).")
