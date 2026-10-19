import json
import time
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from services.assistant.main import retrieve
from services.executor.main import app as executor_app
from services.payment.capacity import Budget, blocked
from services.supervisor.model import load, train, vector
from services.supervisor.store import connect, ingest


def test_capacity_and_expiring_quarantine(tmp_path, monkeypatch):
    budget = Budget(rate=0, burst=1)
    assert budget.admit()
    assert not budget.admit()
    path = tmp_path / "policy.json"
    monkeypatch.setenv("POLICY_FILE", str(path))
    path.write_text(
        json.dumps(
            [
                {"ip": "192.168.137.2", "expires_at": time.time() + 60},
                {"ip": "192.168.137.3", "expires_at": time.time() - 1},
            ]
        )
    )
    assert blocked("192.168.137.2")
    assert not blocked("192.168.137.3")


def test_executor_cannot_be_used_without_auth_or_outside_lab():
    with TestClient(executor_app) as client:
        payload = {"incident_id": str(uuid4()), "source_ip": "192.168.137.2"}
        assert client.post("/quarantine", json=payload).status_code == 401
        for source in ["8.8.8.8", "127.0.0.1", "0.0.0.0", "169.254.1.1"]:
            payload["source_ip"] = source
            assert (
                client.post(
                    "/quarantine",
                    json=payload,
                    headers={
                        "X-Remediation-Key": "test-only-executor-key",
                    },
                ).status_code
                == 422
            )


def test_executor_replay_does_not_repeat_action(tmp_path, monkeypatch):
    incident_id = str(uuid4())
    path = tmp_path / "blocks.json"
    path.write_text(
        json.dumps(
            [
                {
                    "ip": "192.168.137.2",
                    "incident_id": incident_id,
                    "expires_at": time.time() + 60,
                }
            ]
        )
    )
    monkeypatch.setenv("POLICY_FILE", str(path))
    with TestClient(executor_app) as client, patch("asyncio.create_subprocess_exec") as spawn:
        response = client.post(
            "/quarantine",
            headers={
                "X-Remediation-Key": "test-only-executor-key",
            },
            json={"incident_id": incident_id, "source_ip": "192.168.137.2"},
        )
        assert response.json()["replayed"] is True
        spawn.assert_not_called()


def test_log_collector_is_idempotent_and_retries_partial_lines(tmp_path):
    path = tmp_path / "test.jsonl"
    event = json.dumps({"timestamp": time.time(), "service": "test", "status": 200})
    path.write_text(event + "\n" + event)
    with connect() as db:
        assert ingest(db, tmp_path) == 1
        assert ingest(db, tmp_path) == 0
        with path.open("a") as stream:
            stream.write("\n")
        assert ingest(db, tmp_path) == 1


def test_model_is_trained_on_windows_and_detects_novel_flood(tmp_path):
    start = time.time() - 90
    with connect() as db:
        for window in range(24):
            for index in range(1 + window % 12):
                db.execute(
                    "INSERT INTO events(timestamp,service,client_ip,status,duration,route) "
                    "VALUES(?,?,?,?,?,?)",
                    (
                        start + window * 3 + index * 0.01,
                        "payment",
                        "192.168.137.1",
                        200,
                        0.005,
                        "/transactions",
                    ),
                )
        db.commit()
        meta = train(db, start, start + 72, tmp_path)
        model, loaded = load(tmp_path)
        assert meta["version"] == loaded["version"]
        assert meta["train_windows"] >= 12
        flood = [{"status": 401, "duration": 0.005} for _ in range(210)]
        assert model.decision_function([vector(flood)])[0] < meta["threshold"]
        for latency in (0.001, 0.02):
            normal = [{"status": 200, "duration": latency}]
            assert model.decision_function([vector(normal)])[0] >= meta["threshold"]


def test_rag_retrieves_local_procedure_and_handles_unknown_topic(tmp_path):
    (tmp_path / "recovery.md").write_text(
        "Quarantaine de la source. La reprise est vérifiée par une nouvelle "
        "transaction de paiement.",
        encoding="utf-8",
    )
    results = retrieve("Comment vérifier la reprise du paiement ?", tmp_path)
    assert results[0][0].metadata["source"] == "recovery.md"
    assert retrieve("xyzzqv", tmp_path) == []


def test_failed_verification_is_not_reported_as_recovered():
    from services.supervisor.main import verify_business

    async def run():
        client = AsyncMock()
        response = AsyncMock()
        response.raise_for_status = lambda: None
        response.json = lambda: {"access_token": "test"}
        client.post.return_value = response
        invalid = AsyncMock()
        invalid.raise_for_status = lambda: None
        invalid.json = lambda: []
        client.get.return_value = invalid
        with patch("services.supervisor.main.secret", return_value="test"):
            try:
                await verify_business(client)
            except (KeyError, ValueError):
                return
            raise AssertionError("Invalid business result accepted")

    import asyncio

    asyncio.run(run())


def test_quarantine_selects_source_not_victim_and_protects_control_plane():
    from services.supervisor.model import quarantine_candidate

    events = [{"client_ip": "192.168.137.2"}] * 80 + [{"client_ip": "192.168.137.1"}] * 3
    assert quarantine_candidate(events, {"192.168.137.1"}, set()) == "192.168.137.2"
    assert quarantine_candidate(events, {"192.168.137.2"}, set()) is None
    assert quarantine_candidate(events, set(), {"192.168.137.2"}) is None
    assert quarantine_candidate(events[:1] + events[-1:], set(), set()) is None
    assert quarantine_candidate(events[:2], set(), set()) is None
    assert quarantine_candidate(events[:12] + events[-1:] * 12, set(), set()) is None


def test_rag_reports_missing_model_as_retrieval_only(tmp_path):
    import asyncio

    import httpx
    from langchain_core.documents import Document
    from langchain_core.runnables import RunnableLambda

    from services.assistant.main import Question, ask

    def unavailable(_):
        raise httpx.ConnectError("Local model unavailable")

    with (
        patch(
            "services.assistant.main.retrieve",
            return_value=[
                (
                    Document(
                        page_content="Procédure de reprise", metadata={"source": "runbook.md"}
                    ),
                    0.8,
                )
            ],
        ),
        patch("services.assistant.main.ChatOllama", return_value=RunnableLambda(unavailable)),
    ):
        response = asyncio.run(ask(Question(question="Comment vérifier la reprise ?"), "operator"))
        assert response["mode"] == "retrieval_only"
        assert response["sources"][0]["source"] == "runbook.md"
