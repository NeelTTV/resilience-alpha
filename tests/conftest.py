import hashlib
import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

TEST_DIR = tempfile.TemporaryDirectory(prefix="resilience-tests-")
os.environ["DATABASE_URL"] = "sqlite:///" + (Path(TEST_DIR.name) / "test.db").as_posix()
os.environ["JWT_SECRET"] = "test-only-signing-key-with-at-least-thirty-two-bytes"
salt = bytes.fromhex("0123456789abcdef0123456789abcdef")
os.environ["DEMO_PASSWORD_HASH"] = salt.hex() + ":" + hashlib.scrypt(
    b"test-password", salt=salt, n=16384, r=8, p=1,
).hex()
os.environ["DEMO_USERNAME"] = "operator"

from services.auth.main import app as auth_app  # noqa: E402
from services.payment.main import Base, app, engine  # noqa: E402


@pytest.fixture
def clients():
    Base.metadata.drop_all(engine)
    with TestClient(auth_app) as auth, TestClient(app) as api:
        yield auth, api


@pytest.fixture
def headers(clients):
    auth, _ = clients
    token = auth.post("/token", json={
        "username": "operator", "password": "test-password",
    }).json()["access_token"]
    return {"Authorization": f"Bearer {token}", "Idempotency-Key": "payment-1"}

