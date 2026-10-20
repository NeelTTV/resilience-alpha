import os

import httpx
import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from services.common.config import secret

bearer = HTTPBearer(auto_error=False)


def current_user(
    request: Request, credentials: HTTPAuthorizationCredentials = Depends(bearer)
) -> str:
    if credentials is None:
        raise HTTPException(401, "Authentication required")
    try:
        payload = jwt.decode(
            credentials.credentials,
            secret("JWT_PUBLIC_KEY"),
            algorithms=["RS256"],
            audience="resilience-api",
            issuer="resilience-auth",
            options={"require": ["exp", "iat", "sub", "aud", "iss"]},
        )
        if payload["sub"] == "recovery-check":
            if request.url.path not in {"/transactions", "/introspect"}:
                raise HTTPException(403, "Compte technique limité aux preuves de paiement")
        else:
            if payload.get("amr") != ["face", "pwd"]:
                raise HTTPException(401, "Authentification physique requise")
            if os.getenv("AUTH_STATE"):
                from services.auth.physical import database

                with database() as db:
                    user = db.execute(
                        "SELECT * FROM users WHERE username=?", (payload["sub"],)
                    ).fetchone()
                    if (
                        not user
                        or not user["enabled"]
                        or not user["enrolled"]
                        or user["version"] != payload.get("version")
                    ):
                        raise HTTPException(401, "Habilitation révoquée")
            elif os.getenv("AUTH_INTROSPECTION_URL"):
                try:
                    result = httpx.get(
                        os.environ["AUTH_INTROSPECTION_URL"],
                        headers={"Authorization": "Bearer " + credentials.credentials},
                        timeout=3,
                        trust_env=False,
                    )
                    if result.status_code != 200:
                        raise HTTPException(401, "Habilitation révoquée")
                except httpx.HTTPError:
                    raise HTTPException(
                        503, "Vérification des habilitations indisponible"
                    ) from None
        return payload["sub"]
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid or expired token") from None
