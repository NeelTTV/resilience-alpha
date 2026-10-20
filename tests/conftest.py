import hashlib
import os
import tempfile
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

TEST_DIR = tempfile.TemporaryDirectory(prefix="resilience-tests-")
os.environ["DATABASE_URL"] = "sqlite:///" + (Path(TEST_DIR.name) / "test.db").as_posix()
key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
os.environ["JWT_PRIVATE_KEY"] = key.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption(),
).decode()
os.environ["JWT_PUBLIC_KEY"] = (
    key.public_key()
    .public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    .decode()
)
os.environ["SUPERVISOR_STATE"] = str(Path(TEST_DIR.name) / "supervisor")
os.environ["AUTH_STATE"] = str(Path(TEST_DIR.name) / "auth.db")
os.environ["CAMERA_KEY"] = "test-camera-key"
os.environ["DEVICE_KEY"] = "test-device-key"
os.environ["REMEDIATION_KEY"] = "test-only-executor-key"
salt = bytes.fromhex("0123456789abcdef0123456789abcdef")
os.environ["DEMO_PASSWORD_HASH"] = (
    salt.hex()
    + ":"
    + hashlib.scrypt(
        b"test-password",
        salt=salt,
        n=16384,
        r=8,
        p=1,
    ).hex()
)
os.environ["DEMO_USERNAME"] = "operator"
os.environ["RECOVERY_PASSWORD_HASH"] = os.environ["DEMO_PASSWORD_HASH"]

from services.auth.main import app as auth_app  # noqa: E402
from services.payment.main import Base, app, engine  # noqa: E402


@pytest.fixture
def clients():
    from services.auth.physical import database

    with database() as db:
        db.execute("DELETE FROM sessions")
        db.execute("DELETE FROM users")
        db.execute("UPDATE kiosk SET failures=0,blocked_until=0")
    Base.metadata.drop_all(engine)
    with TestClient(auth_app) as auth, TestClient(app) as api:
        with database() as db:
            db.execute("UPDATE users SET enrolled=1 WHERE username='operator'")
        yield auth, api


@pytest.fixture
def headers(clients):
    from services.auth.main import issue

    token = issue("operator", "admin")["access_token"]
    return {"Authorization": f"Bearer {token}", "Idempotency-Key": "payment-1"}
