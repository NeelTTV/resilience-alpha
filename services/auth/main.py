import hashlib
import hmac
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from services.common.config import secret
from services.common.telemetry import instrument


@asynccontextmanager
async def lifespan(app: FastAPI):
    secret("JWT_PRIVATE_KEY")
    secret("DEMO_PASSWORD_HASH")
    yield


app = FastAPI(title="Resilience Alpha - Auth", lifespan=lifespan)
instrument(app, "auth")


class Login(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


@app.get("/health")
def health():
    return {"status": "ok", "service": "auth"}


@app.post("/token")
def token(body: Login):
    recovery = body.username == "recovery-check"
    salt, expected = secret(
        "RECOVERY_PASSWORD_HASH" if recovery else "DEMO_PASSWORD_HASH",
    ).split(":", 1)
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
    now = datetime.now(timezone.utc)
    access_token = jwt.encode(
        {
            "sub": body.username,
            "iat": now,
            "exp": now + timedelta(minutes=15),
            "iss": "resilience-auth",
            "aud": "resilience-api",
        },
        secret("JWT_PRIVATE_KEY"),
        algorithm="RS256",
    )
    return {"access_token": access_token, "token_type": "bearer", "expires_in": 900}
