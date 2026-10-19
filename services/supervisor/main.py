import asyncio
import json
import logging
import os
import socket
import time
import uuid
from contextlib import asynccontextmanager, suppress

import httpx
from fastapi import Depends, FastAPI, HTTPException

from services.common.config import secret
from services.common.security import current_user
from services.common.telemetry import instrument
from services.supervisor.model import WINDOW, load, quarantine_candidate, vector
from services.supervisor.store import connect, incidents, ingest, transition

log = logging.getLogger("uvicorn.error")
runtime = {"model": None, "last_cycle": 0, "last_error": None, "loki_cursor": 0}


async def verify_business(client):
    gateway = os.getenv("GATEWAY_URL", "http://waf:8080")
    login = await client.post(
        gateway + "/auth/token",
        json={
            "username": "recovery-check",
            "password": secret("RECOVERY_PASSWORD"),
        },
    )
    login.raise_for_status()
    headers = {"Authorization": "Bearer " + login.json()["access_token"]}
    before = await client.get(gateway + "/api/transactions", headers=headers)
    before.raise_for_status()
    prior = {t["id"]: (t["amount_cents"], t["currency"], t["status"]) for t in before.json()[:20]}
    key = str(uuid.uuid4())
    payment = await client.post(
        gateway + "/api/transactions",
        headers={
            **headers,
            "Idempotency-Key": key,
        },
        json={"amount_cents": 101, "currency": "EUR"},
    )
    payment.raise_for_status()
    after = await client.get(gateway + "/api/transactions", headers=headers)
    after.raise_for_status()
    rows = {t["id"]: (t["amount_cents"], t["currency"], t["status"]) for t in after.json()}
    if rows.get(payment.json()["id"]) != (101, "EUR", "completed"):
        raise ValueError("New transaction not persisted correctly")
    if any(rows.get(key) != value for key, value in prior.items()):
        raise ValueError("Previous transactions changed after recovery")
    return {
        "transaction_id": payment.json()["id"],
        "idempotency_key": key,
        "previous_verified": len(prior),
        "gateway": gateway,
    }


async def recover(incident_id, source):
    with connect() as db:
        transition(db, incident_id, "recovering", {"action": "quarantine_source", "ip": source})
        try:
            async with httpx.AsyncClient(timeout=30, trust_env=False) as client:
                result = await client.post(
                    os.getenv("EXECUTOR_URL", "http://executor:8000") + "/quarantine",
                    json={
                        "incident_id": incident_id,
                        "source_ip": source,
                    },
                    headers={"X-Remediation-Key": secret("REMEDIATION_KEY")},
                )
                result.raise_for_status()
                transition(db, incident_id, "verifying", result.json())
                proof = None
                for attempt in range(1, 6):
                    await asyncio.sleep(2)
                    try:
                        proof = await verify_business(client)
                        break
                    except (httpx.HTTPError, ValueError, KeyError) as exc:
                        transition(
                            db,
                            incident_id,
                            "verifying",
                            {
                                "attempt": attempt,
                                "error": type(exc).__name__,
                            },
                        )
                if proof is None:
                    raise ValueError("Business verification failed after 5 attempts")
                transition(db, incident_id, "recovered", proof)
        except Exception as exc:
            log.exception("Recovery failed")
            transition(db, incident_id, "failed", {"reason": type(exc).__name__})


async def push_loki(client, db):
    checkpoint = db.execute("SELECT value FROM checkpoints WHERE name='loki'").fetchone()
    cursor = checkpoint["value"] if checkpoint else 0
    runtime["loki_cursor"] = cursor
    rows = db.execute(
        "SELECT * FROM events WHERE id>? ORDER BY id LIMIT 1000", (cursor,)
    ).fetchall()
    if not rows:
        return
    streams = {}
    for event in rows:
        streams.setdefault(event["service"], []).append(
            [
                str(int(event["timestamp"] * 1_000_000_000)),
                json.dumps(dict(event)),
            ]
        )
    response = await client.post(
        os.getenv("LOKI_URL", "http://loki:3100") + "/loki/api/v1/push",
        json={
            "streams": [
                {"stream": {"service": key, "job": "resilience"}, "values": values}
                for key, values in streams.items()
            ]
        },
    )
    response.raise_for_status()
    runtime["loki_cursor"] = rows[-1]["id"]
    db.execute("INSERT OR REPLACE INTO checkpoints VALUES('loki',?)", (rows[-1]["id"],))
    db.commit()


async def monitor():
    active = {}
    consecutive = {}
    model_version = None
    model = metadata = None
    infrastructure_sources = set()
    for hostname in ("supervisor", "dashboard", "waf"):
        try:
            infrastructure_sources.update(socket.gethostbyname_ex(hostname)[2])
        except OSError:
            pass
    # A restart cannot safely replay partially applied actions without business verification.
    with connect() as db:
        for row in db.execute("SELECT id FROM incidents WHERE state NOT IN ('recovered','failed')"):
            transition(db, row["id"], "failed", {"reason": "supervisor_restarted; inspect policy"})
    async with httpx.AsyncClient(timeout=8, trust_env=False) as client:
        while True:
            try:
                with connect() as db:
                    ingest(db)
                    ingest(db, os.getenv("WAF_LOG_DIR", "/waf-logs"))
                    try:
                        loaded, meta = load()
                        if meta["version"] != model_version:
                            model, metadata, model_version = loaded, meta, meta["version"]
                        runtime["model"] = metadata
                    except FileNotFoundError:
                        runtime["model"] = None
                    try:
                        await push_loki(client, db)
                        runtime["loki_error"] = None
                    except httpx.HTTPError as exc:
                        runtime["loki_error"] = type(exc).__name__
                    now = time.time()
                    rows = db.execute(
                        "SELECT * FROM events WHERE timestamp>=? AND service='payment' "
                        "AND route='/transactions'",
                        (now - WINDOW,),
                    ).fetchall()
                    if model:
                        sources = {r["client_ip"] for r in rows} - {"internal"}
                        candidate = quarantine_candidate(
                            rows,
                            metadata["protected_sources"],
                            infrastructure_sources,
                        )
                        for source in sources:
                            events = [r for r in rows if r["client_ip"] == source]
                            features = vector(events)
                            score = float(model.decision_function([features])[0])
                            suspect = score < metadata["threshold"]
                            consecutive[source] = consecutive.get(source, 0) + 1 if suspect else 0
                            recent = db.execute(
                                "SELECT id FROM incidents WHERE source_ip=? AND created_at>? "
                                "AND (state!='failed' OR created_at>?)",
                                (source, now - 300, now - 30),
                            ).fetchone()
                            # Confirm novelty across two model decisions.
                            safe_to_quarantine = source == candidate
                            if (
                                consecutive[source] >= 2
                                and not recent
                                and source not in active
                                and safe_to_quarantine
                            ):
                                incident_id = str(uuid.uuid4())
                                evidence = {
                                    "model_version": model_version,
                                    "score": score,
                                    "threshold": metadata["threshold"],
                                    "features": features,
                                    "window_seconds": WINDOW,
                                    "soc": {
                                        "errors": sum(r["status"] >= 400 for r in events),
                                        "requests": len(events),
                                    },
                                }
                                db.execute(
                                    "INSERT INTO incidents"
                                    "(id,source_ip,state,created_at,updated_at,payload) "
                                    "VALUES(?,?,?,?,?,?)",
                                    (
                                        incident_id,
                                        source,
                                        "detected",
                                        now,
                                        now,
                                        json.dumps(evidence),
                                    ),
                                )
                                transition(db, incident_id, "detected", evidence)
                                active[source] = asyncio.create_task(recover(incident_id, source))
                    active = {source: task for source, task in active.items() if not task.done()}
                    runtime["last_cycle"] = time.time()
                    runtime["last_error"] = None
            except Exception as exc:
                runtime["last_error"] = type(exc).__name__
                log.exception("Monitoring cycle failed")
            await asyncio.sleep(1)


@asynccontextmanager
async def lifespan(app):
    secret("JWT_PUBLIC_KEY")
    task = asyncio.create_task(monitor())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


app = FastAPI(title="Resilience control plane", lifespan=lifespan)
instrument(app, "supervisor")


@app.get("/health")
def health():
    if runtime["last_error"] or time.time() - runtime["last_cycle"] > 20:
        raise HTTPException(503, "Monitoring loop unavailable")
    return {"status": "ok", "trained": runtime["model"] is not None}


@app.get("/status")
def status(user=Depends(current_user)):
    with connect() as db:
        count = db.execute("SELECT count(*) FROM events").fetchone()[0]
        soc = [
            dict(r)
            for r in db.execute(
                "SELECT service,status,count(*) AS count FROM events WHERE timestamp>? "
                "GROUP BY service,status",
                (time.time() - 60,),
            )
        ]
        return {
            **runtime,
            "events_collected": count,
            "soc_last_minute": soc,
            "incidents": incidents(db),
        }
