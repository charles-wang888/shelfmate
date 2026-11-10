"""JWT issuance and verification for demo login."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import HTTPException, status

from app.core.config import settings


def issue_token(username: str, role: str, display_name: str) -> str:
    """Create a signed bearer token for an authenticated user."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": username,
        "role": role,
        "name": display_name,
        "iat": now,
        "exp": now + timedelta(minutes=settings.auth_token_ttl_minutes),
    }
    return jwt.encode(payload, settings.auth_secret, algorithm="HS256")


def decode_token(token: str) -> dict[str, Any]:
    """Validate and decode a bearer token."""
    try:
        return jwt.decode(token, settings.auth_secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc


def extract_bearer(authorization: str | None) -> str | None:
    """Pull the raw token from an Authorization header."""
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None
