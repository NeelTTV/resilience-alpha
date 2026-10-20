"""Verify the business flow through the public gateway. No third-party packages."""

import http.client
import json
import os
import ssl
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
BASE = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
address = urlsplit(BASE)


def request(path, data=None, headers=None):
    # Human accounts always follow the same physical protocol as the UI.
    if (
        path == "/auth/token"
        and data
        and data.get("username") != "recovery-check"
        and not data.get("challenge")
    ):
        challenge = request("/auth/identify", {"username": data["username"]})["challenge"]
        print("Présentez votre visage devant la caméra USB du PC hôte.", flush=True)
        for _ in range(160):
            state = request("/auth/session/" + challenge)
            if state["phase"] == "password":
                break
            if state["phase"] in {"failed", "face_rejected"}:
                raise RuntimeError("Reconnaissance faciale refusée sur le PC hôte")
            time.sleep(0.25)
        else:
            raise RuntimeError("Caméra du PC hôte : délai expiré")
        result = request(path, {**data, "challenge": challenge}, headers)
        if result["phase"] != "success":
            raise RuntimeError("Mot de passe refusé : recommencez l'identification")
        for _ in range(140):
            if request("/auth/session/" + challenge)["phase"] == "done":
                return request("/auth/session/" + challenge + "/complete", {})
            time.sleep(0.25)
        raise RuntimeError("Temporisation de connexion non terminée")
    # Long recipes must not reuse a connection after the gateway's keep-alive limit.
    if address.scheme == "https":
        context = ssl.create_default_context(cafile=str(ROOT / ".secrets/tls_cert"))
        connection = http.client.HTTPSConnection(
            address.hostname, address.port or 443, timeout=15, context=context
        )
    else:
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
    technical = os.getenv("SMOKE_SERVICE_ACCOUNT") == "1"
    token = request(
        "/auth/token",
        {
            "username": "recovery-check" if technical else os.getenv("DEMO_USERNAME", "operator"),
            "password": (
                ROOT / ".secrets" / ("recovery_password" if technical else "demo_password")
            )
            .read_text()
            .strip(),
        },
    )["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": str(uuid.uuid4())}
    payment = request("/api/transactions", {"amount_cents": 1234, "currency": "EUR"}, headers)
    assert payment["status"] == "completed"
    retry = request("/api/transactions", {"amount_cents": 1234, "currency": "EUR"}, headers)
    assert retry["id"] == payment["id"]
    assert any(t["id"] == payment["id"] for t in request("/api/transactions", headers=headers))
    print("PASS: health, authentication, new payment, idempotent retry, persisted history.")
    if technical:
        print("Technical payment account only; physical back-office login NOT tested.")
