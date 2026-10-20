"""Persistent, single-kiosk authentication state. No biometric images in Docker."""

import math
import os
import secrets
import sqlite3
import ssl
import threading
import time
from contextlib import closing, contextmanager
from pathlib import Path

import httpx
from fastapi import HTTPException

from services.common.config import secret

lock = threading.RLock()
device_seen = 0.0


@contextmanager
def database():
    path = Path(os.getenv("AUTH_STATE", "/state/auth.db"))
    path.parent.mkdir(parents=True, exist_ok=True)
    with lock, closing(sqlite3.connect(path)) as db, db:
        db.row_factory = sqlite3.Row
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY, password_hash TEXT NOT NULL,
                role TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1,
                enrolled INTEGER NOT NULL DEFAULT 0, version TEXT NOT NULL DEFAULT 'initial');
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY, username TEXT NOT NULL, phase TEXT NOT NULL,
                deadline REAL NOT NULL, expires REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS kiosk (
                id INTEGER PRIMARY KEY CHECK(id=1), failures INTEGER NOT NULL,
                blocked_until REAL NOT NULL);
            INSERT OR IGNORE INTO kiosk VALUES (1, 0, 0);
        """)
        yield db


def initialize():
    with database() as db:
        db.execute(
            "INSERT OR IGNORE INTO users(username,password_hash,role,enrolled) VALUES(?,?,?,0)",
            (os.getenv("DEMO_USERNAME", "operator"), secret("DEMO_PASSWORD_HASH"), "admin"),
        )


def camera(action, username="", session=""):
    try:
        response = httpx.post(
            os.getenv("CAMERA_URL", "https://host.docker.internal:8765") + "/" + action,
            headers={"Authorization": "Bearer " + secret("CAMERA_KEY")},
            json={"username": username, "session": session},
            timeout=25,
            trust_env=False,
            verify=ssl.create_default_context(cafile=os.environ["CAMERA_CERT_FILE"]),
        )
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError, RuntimeError, OSError, KeyError):
        raise HTTPException(503, "Caméra du PC hôte indisponible") from None


def tick():
    """Called by the watchdog even when the browser is closed."""
    now = time.time()
    closing = []
    with database() as db:
        for row in db.execute("SELECT * FROM sessions WHERE phase NOT IN ('done','failed')"):
            phase = row["phase"]
            disconnected = phase in {"password", "success"} and now - device_seen > 5
            if now >= row["deadline"] or disconnected:
                target = {
                    "success": "done",
                    "face_rejected": "failed",
                    "password_rejected": "failed",
                }.get(phase, "failed")
                if disconnected:
                    target = "failed"
                db.execute("UPDATE sessions SET phase=? WHERE id=?", (target, row["id"]))
                closing.append(row["id"])
        db.execute("DELETE FROM sessions WHERE expires < ?", (now - 86400,))
    for session in closing:
        try:
            camera("close", session=session)
        except HTTPException:
            pass  # Host has an independent camera timeout.


def identify(username):
    tick()
    now = time.time()
    with database() as db:
        kiosk = db.execute("SELECT * FROM kiosk").fetchone()
        if kiosk["blocked_until"] > now:
            raise HTTPException(
                429,
                "Identification bloquée cinq minutes",
                headers={"Retry-After": str(max(1, math.ceil(kiosk["blocked_until"] - now)))},
            )
        if kiosk["blocked_until"]:
            db.execute("UPDATE kiosk SET failures=0,blocked_until=0")
        if now - device_seen > 5:
            raise HTTPException(503, "ESP8266 non connecté : vérifiez la LED du PC hôte")
        if db.execute("SELECT 1 FROM sessions WHERE phase NOT IN ('done','failed')").fetchone():
            raise HTTPException(409, "La caméra du PC hôte est déjà utilisée")
        session = secrets.token_urlsafe(32)
        db.execute(
            "INSERT INTO sessions VALUES(?,?,?,?,?)",
            (session, username, "camera", now + 35, now + 180),
        )
        return session


def recognize(session, username):
    try:
        matched = camera("verify", username, session).get("matched") is True
    except HTTPException:
        matched = False
    with database() as db:
        row = db.execute("SELECT * FROM sessions WHERE id=?", (session,)).fetchone()
        if not row or row["phase"] != "camera" or time.time() >= row["deadline"]:
            return
        user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        bootstrap = (
            user is not None
            and user["role"] == "admin"
            and user["version"] == "initial"
            and username == os.getenv("DEMO_USERNAME", "operator")
        )
        matched = (
            matched and user is not None and user["enabled"] and (user["enrolled"] or bootstrap)
        )
        if matched:
            db.execute("UPDATE users SET enrolled=1 WHERE username=?", (username,))
            phase, deadline = "password", time.time() + 90
        else:
            phase, deadline = "face_rejected", time.time() + 30
            failures = db.execute("SELECT failures FROM kiosk").fetchone()[0] + 1
            db.execute(
                "UPDATE kiosk SET failures=?,blocked_until=?",
                (failures, deadline + 300 if failures >= 2 else 0),
            )
        db.execute("UPDATE sessions SET phase=?,deadline=? WHERE id=?", (phase, deadline, session))


def status(session):
    tick()
    with database() as db:
        row = db.execute("SELECT * FROM sessions WHERE id=?", (session,)).fetchone()
        if not row or row["expires"] < time.time():
            raise HTTPException(404, "Identification expirée")
        kiosk = db.execute("SELECT * FROM kiosk").fetchone()
        return {
            "phase": row["phase"],
            "remaining": max(0, row["deadline"] - time.time()),
            "blocked_seconds": max(0, kiosk["blocked_until"] - time.time()),
        }


def led():
    global device_seen
    device_seen = time.time()
    tick()
    with database() as db:
        row = db.execute(
            "SELECT * FROM sessions WHERE phase NOT IN ('done','failed') "
            "ORDER BY rowid DESC LIMIT 1"
        ).fetchone()
        modes = {
            "password": "green_blink",
            "success": "green",
            "face_rejected": "red",
            "password_rejected": "red_blink",
        }
        return {
            "mode": modes.get(row["phase"], "off") if row else "off",
            "event": row["id"] + row["phase"] if row else "idle",
            "remaining_ms": max(0, int((row["deadline"] - time.time()) * 1000)) if row else 0,
        }
