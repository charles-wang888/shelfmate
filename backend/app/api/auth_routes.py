"""Authentication endpoints."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.core.auth import decode_token, extract_bearer, issue_token
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class LoginResponse(BaseModel):
    token: str
    username: str
    role: str
    display_name: str


def _users() -> list[dict]:
    path: Path = settings.data_dir / "users.json"
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest) -> LoginResponse:
    """Validate demo credentials and return a bearer token."""
    for user in _users():
        if user["username"] == body.username and user["password"] == body.password:
            token = issue_token(
                username=user["username"],
                role=user["role"],
                display_name=user["display_name"],
            )
            return LoginResponse(
                token=token,
                username=user["username"],
                role=user["role"],
                display_name=user["display_name"],
            )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid username or password",
    )


@router.post("/logout")
def logout() -> dict[str, bool]:
    """Client-side logout helper (stateless JWT)."""
    return {"ok": True}


@router.get("/me")
def me(authorization: str | None = Header(default=None)) -> dict:
    """Return the current user from the bearer token, if present."""
    token = extract_bearer(authorization)
    if not token:
        return {"authenticated": False}
    try:
        payload = decode_token(token)
    except HTTPException:
        return {"authenticated": False}
    return {
        "authenticated": True,
        "username": payload.get("sub"),
        "role": payload.get("role"),
        "display_name": payload.get("name"),
    }
