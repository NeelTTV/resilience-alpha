"""Verify the business flow through the public gateway. No third-party packages."""
import json
import os
import uuid
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
BASE = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8080").rstrip("/")


def request(path, data=None, headers=None):
    req = Request(
        BASE + path, data=json.dumps(data).encode() if data is not None else None,
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    with urlopen(req, timeout=10) as response:
        return json.load(response)


assert request("/api/health")["database"] == "ok"
token = request("/auth/token", {
    "username": os.getenv("DEMO_USERNAME", "operator"),
    "password": (ROOT / ".secrets/demo_password").read_text().strip(),
})["access_token"]
headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": str(uuid.uuid4())}
payment = request("/api/transactions", {"amount_cents": 1234, "currency": "EUR"}, headers)
assert payment["status"] == "completed"
retry = request("/api/transactions", {"amount_cents": 1234, "currency": "EUR"}, headers)
assert retry["id"] == payment["id"]
assert any(t["id"] == payment["id"] for t in request("/api/transactions", headers=headers))
print("PASS: health, authentication, new payment, idempotent retry, persisted history.")
