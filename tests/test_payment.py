from datetime import datetime, timedelta, timezone

import jwt
import pytest


def test_auth_rejects_wrong_credentials(clients):
    auth, _ = clients
    assert auth.post("/token", json={
        "username": "operator", "password": "wrong",
    }).status_code == 401


def test_auth_required(clients):
    _, api = clients
    assert api.get("/transactions").status_code == 401
    assert api.post("/transactions", json={"amount_cents": 100}).status_code == 401


def test_transaction_and_idempotent_retry(clients, headers):
    _, api = clients
    first = api.post("/transactions", headers=headers, json={"amount_cents": 1250})
    assert first.status_code == 201
    assert first.json()["status"] == "completed"
    retry = api.post("/transactions", headers=headers, json={"amount_cents": 1250})
    assert retry.json()["id"] == first.json()["id"]
    assert len(api.get("/transactions", headers=headers).json()) == 1
    conflict = api.post("/transactions", headers=headers, json={"amount_cents": 1300})
    assert conflict.status_code == 409


@pytest.mark.parametrize("payload", [
    {"amount_cents": 0}, {"amount_cents": -1}, {"amount_cents": 1.1},
    {"amount_cents": True}, {"amount_cents": 100_000_001},
    {"amount_cents": 100, "currency": "USD"},
])
def test_invalid_money_rejected(clients, headers, payload):
    _, api = clients
    assert api.post("/transactions", headers=headers, json=payload).status_code == 422


def test_missing_idempotency_key(clients, headers):
    _, api = clients
    headers.pop("Idempotency-Key")
    assert api.post("/transactions", headers=headers, json={"amount_cents": 10}).status_code == 422


def test_expired_token_rejected(clients):
    _, api = clients
    now = datetime.now(timezone.utc)
    token = jwt.encode({
        "sub": "operator", "iat": now - timedelta(hours=1),
        "exp": now - timedelta(minutes=1), "iss": "resilience-auth", "aud": "resilience-api",
    }, "test-only-signing-key-with-at-least-thirty-two-bytes", algorithm="HS256")
    assert api.get("/transactions", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_health_and_metrics(clients):
    auth, api = clients
    assert auth.get("/health").status_code == 200
    assert api.get("/health").json()["database"] == "ok"
    assert "http_requests_total" in api.get("/metrics").text


def test_data_survives_new_client(clients, headers):
    from fastapi.testclient import TestClient

    from services.payment.main import app

    _, api = clients
    first = api.post("/transactions", headers=headers, json={"amount_cents": 250})
    with TestClient(app) as restarted:
        history = restarted.get("/transactions", headers=headers).json()
        assert history[0]["id"] == first.json()["id"]
        headers["Idempotency-Key"] = "fresh-payment-after-restart"
        assert restarted.post("/transactions", headers=headers, json={
            "amount_cents": 500,
        }).status_code == 201

