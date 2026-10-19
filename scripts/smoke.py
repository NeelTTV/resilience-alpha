"""Verify the business flow through the public gateway. No third-party packages."""

import http.client
import json
import os
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
BASE = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
address = urlsplit(BASE)


def request(path, data=None, headers=None):
    # Long recipes must not reuse a connection after the gateway's keep-alive limit.
    connection = http.client.HTTPConnection(address.hostname, address.port or 80, timeout=15)
    try:
        connection.request(
            "POST" if data is not None else "GET",
            path,
            body=json.dumps(data).encode() if data is not None else None,
            headers={"Content-Type": "application/json", **(headers or {})},
        )
        response = connection.getresponse()
        body = response.read()
        if response.status >= 400:
            raise HTTPError(BASE + path, response.status, response.reason, response.headers, None)
        return json.loads(body)
    finally:
        connection.close()


if __name__ == "__main__":
    assert request("/api/health")["database"] == "ok"
    token = request(
        "/auth/token",
        {
            "username": os.getenv("DEMO_USERNAME", "operator"),
            "password": (ROOT / ".secrets/demo_password").read_text().strip(),
        },
    )["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": str(uuid.uuid4())}
    payment = request("/api/transactions", {"amount_cents": 1234, "currency": "EUR"}, headers)
    assert payment["status"] == "completed"
    retry = request("/api/transactions", {"amount_cents": 1234, "currency": "EUR"}, headers)
    assert retry["id"] == payment["id"]
    assert any(t["id"] == payment["id"] for t in request("/api/transactions", headers=headers))
    print("PASS: health, authentication, new payment, idempotent retry, persisted history.")
