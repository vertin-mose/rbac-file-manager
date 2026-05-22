"""JWT token handling, password hashing, and auth dependency."""

import base64
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import HTTPException, Request

from config import settings

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def _get_signing_key() -> bytes:
    raw = settings.JWT_SECRET
    try:
        return base64.b64decode(raw)
    except Exception:
        return raw.encode()


def create_token(user_id: int, username: str, roles: list[str]) -> str:
    payload = {
        "sub": username,
        "userId": user_id,
        "roles": roles,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(seconds=settings.JWT_EXPIRATION),
    }
    return jwt.encode(payload, _get_signing_key(), algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, _get_signing_key(), algorithms=[ALGORITHM])
    except Exception:
        return None


async def get_current_user(request: Request) -> dict:
    """FastAPI dependency: extract JWT user from Authorization header."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    payload = decode_token(auth[7:])
    if payload is None:
        raise HTTPException(status_code=401, detail="Token expired or invalid")

    request.state.user_id = payload["userId"]
    request.state.username = payload["sub"]
    request.state.roles = payload.get("roles", [])
    return payload
