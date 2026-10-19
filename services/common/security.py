import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from services.common.config import secret

bearer = HTTPBearer(auto_error=False)


def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> str:
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
        return payload["sub"]
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid or expired token") from None
