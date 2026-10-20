import asyncio
import hashlib
import hmac
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from services.auth import physical
from services.common.config import secret
from services.common.security import current_user
from services.common.telemetry import instrument


@asynccontextmanager
async def lifespan(app: FastAPI):
    secret("JWT_PRIVATE_KEY")
    secret("DEMO_PASSWORD_HASH")
    physical.initialize()

    async def watchdog():
        while True:
            await asyncio.to_thread(physical.tick)
            await asyncio.sleep(0.5)

    task = asyncio.create_task(watchdog())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Resilience Alpha - Auth", lifespan=lifespan)
instrument(app, "auth")


class Login(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)
    challenge: str | None = None


@app.get("/health")
def health():
    return {"status": "ok", "service": "auth"}


@app.post("/token")
def token(body: Login):
    recovery = body.username == "recovery-check"
    if not recovery:
        return physical_password(body)
    salt, expected = secret("RECOVERY_PASSWORD_HASH").split(":", 1)
    actual = hashlib.scrypt(
        body.password.encode(),
        salt=bytes.fromhex(salt),
        n=16384,
        r=8,
        p=1,
    ).hex()
    valid_password = hmac.compare_digest(actual, expected)
    valid_user = hmac.compare_digest(
        body.username,
        "recovery-check" if recovery else os.getenv("DEMO_USERNAME", "operator"),
    )
    if not (valid_password and valid_user):
        raise HTTPException(401, "Invalid credentials")
    return issue(body.username, "service")


def issue(username, role, version=None):
    now = datetime.now(timezone.utc)
    if role == "service":
        version = "service"
    elif version is None:
        with physical.database() as db:
            version = db.execute(
                "SELECT version FROM users WHERE username=?", (username,)
            ).fetchone()[0]
    access_token = jwt.encode(
        {
            "sub": username,
            "role": role,
            "version": version,
            "amr": ["pwd"] if role == "service" else ["face", "pwd"],
            "iat": now,
            "exp": now + timedelta(minutes=15),
            "iss": "resilience-auth",
            "aud": "resilience-api",
        },
        secret("JWT_PRIVATE_KEY"),
        algorithm="RS256",
    )
    return {"access_token": access_token, "token_type": "bearer", "expires_in": 900}


class Identification(BaseModel):
    username: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")


@app.post("/identify")
def identify(body: Identification, tasks: BackgroundTasks):
    session = physical.identify(body.username)
    tasks.add_task(physical.recognize, session, body.username)
    return {"challenge": session, "phase": "camera"}


@app.get("/session/{challenge}")
def session_status(challenge: str):
    return physical.status(challenge)


def physical_password(body):
    physical.tick()
    with physical.database() as db:
        row = db.execute("SELECT * FROM sessions WHERE id=?", (body.challenge,)).fetchone()
        user = db.execute("SELECT * FROM users WHERE username=?", (body.username,)).fetchone()
        if (
            not row
            or row["phase"] != "password"
            or row["username"] != body.username
            or row["deadline"] <= time.time()
            or not user
            or not user["enabled"]
            or not user["enrolled"]
        ):
            raise HTTPException(403, "Reconnaissance faciale requise")
        salt, expected = user["password_hash"].split(":", 1)
        actual = hashlib.scrypt(
            body.password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1
        ).hex()
        valid = hmac.compare_digest(actual, expected)
        phase = "success" if valid else "password_rejected"
        deadline = time.time() + (30 if valid else 10)
        db.execute(
            "UPDATE sessions SET phase=?,deadline=? WHERE id=?", (phase, deadline, body.challenge)
        )
        if valid:
            db.execute("UPDATE kiosk SET failures=0,blocked_until=0")
        else:
            failures = db.execute("SELECT failures FROM kiosk").fetchone()[0] + 1
            db.execute(
                "UPDATE kiosk SET failures=?,blocked_until=?",
                (failures, deadline + 300 if failures >= 2 else 0),
            )
    # Camera is shut down after rejection animation, or after success delay, by watchdog.
    return {"phase": phase, "remaining": 30 if valid else 10}


@app.post("/session/{challenge}/complete")
def complete(challenge: str):
    physical.tick()
    with physical.database() as db:
        row = db.execute("SELECT * FROM sessions WHERE id=?", (challenge,)).fetchone()
        if not row or row["phase"] != "done" or row["expires"] < time.time():
            raise HTTPException(403, "Attendez la fin du voyant vert (30 secondes)")
        user = db.execute("SELECT * FROM users WHERE username=?", (row["username"],)).fetchone()
        if not user or not user["enabled"] or not user["enrolled"]:
            raise HTTPException(403, "Habilitation révoquée")
        db.execute("UPDATE sessions SET phase='failed' WHERE id=?", (challenge,))
        username, role, version = user["username"], user["role"], user["version"]
    return issue(username, role, version)


@app.get("/device/status")
def device_status(authorization: str = Header(default="")):
    if not hmac.compare_digest(authorization, "Bearer " + secret("DEVICE_KEY")):
        raise HTTPException(401, "Module non autorisé")
    return physical.led()


@app.get("/introspect")
def introspect(user: str = Depends(current_user)):
    if user == "recovery-check":
        return {"active": True}
    with physical.database() as db:
        row = db.execute("SELECT * FROM users WHERE username=?", (user,)).fetchone()
        if not row or not row["enabled"] or not row["enrolled"]:
            raise HTTPException(401, "Habilitation révoquée")
    return {"active": True}


def administrator(user: str = Depends(current_user)):
    with physical.database() as db:
        row = db.execute("SELECT * FROM users WHERE username=?", (user,)).fetchone()
        if not row or row["role"] != "admin" or not row["enabled"] or not row["enrolled"]:
            raise HTTPException(403, "Administrateur requis")
    return user


class UserSettings(Identification):
    password: str | None = Field(default=None, min_length=12, max_length=256)
    role: str = Field(default="operator", pattern=r"^(admin|operator)$")
    enabled: bool = True


@app.get("/users")
def users(admin: str = Depends(administrator)):
    with physical.database() as db:
        return [
            dict(row)
            for row in db.execute(
                "SELECT username,role,enabled,enrolled FROM users ORDER BY username"
            )
        ]


@app.put("/users")
def save_user(body: UserSettings, admin: str = Depends(administrator)):
    if body.username == "recovery-check":
        raise HTTPException(400, "Compte technique réservé")
    with physical.database() as db:
        existing = db.execute("SELECT * FROM users WHERE username=?", (body.username,)).fetchone()
        if body.username == admin and (not body.enabled or body.role != "admin"):
            raise HTTPException(400, "Conservez votre accès administrateur")
        if not existing and not body.password:
            raise HTTPException(400, "Mot de passe initial requis (12 caractères minimum)")
        hashed = existing["password_hash"] if existing else ""
        if body.password:
            salt = os.urandom(16)
            hashed = (
                salt.hex()
                + ":"
                + hashlib.scrypt(body.password.encode(), salt=salt, n=16384, r=8, p=1).hex()
            )
        db.execute(
            """INSERT INTO users(username,password_hash,role,enabled) VALUES(?,?,?,?)
                      ON CONFLICT(username) DO UPDATE SET password_hash=excluded.password_hash,
                      role=excluded.role,enabled=excluded.enabled""",
            (body.username, hashed, body.role, body.enabled),
        )
        db.execute("UPDATE sessions SET phase='failed' WHERE username=?", (body.username,))
        db.execute(
            "UPDATE users SET version=? WHERE username=?", (os.urandom(16).hex(), body.username)
        )
    return {"saved": True}


@app.post("/users/{username}/enroll")
def enroll(username: str, admin: str = Depends(administrator)):
    with physical.database() as db:
        if not db.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
            raise HTTPException(404, "Utilisateur inconnu")
        if db.execute("SELECT 1 FROM sessions WHERE phase NOT IN ('done','failed')").fetchone():
            raise HTTPException(409, "Identification en cours")
        physical.camera("enroll", username)
        db.execute("UPDATE users SET enrolled=1 WHERE username=?", (username,))
        db.execute("UPDATE users SET version=? WHERE username=?", (os.urandom(16).hex(), username))
    return {"enrolled": True}


@app.delete("/users/{username}")
def delete_user(username: str, admin: str = Depends(administrator)):
    if username == admin:
        raise HTTPException(400, "Ne supprimez pas votre propre accès")
    physical.camera("delete", username)
    with physical.database() as db:
        db.execute("DELETE FROM users WHERE username=?", (username,))
        db.execute("UPDATE sessions SET phase='failed' WHERE username=?", (username,))
    return {"deleted": True}
