"""Thin async client for the local Ollama chat API (with tool calling)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class OllamaError(RuntimeError):
    """Raised when Ollama is unreachable or returns an unexpected payload."""


async def chat(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    *,
    temperature: float = 0.2,
) -> dict[str, Any]:
    """Call Ollama /api/chat and return the assistant message object."""
    body: dict[str, Any] = {
        "model": settings.ollama_model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if tools:
        body["tools"] = tools

    url = f"{settings.ollama_base_url.rstrip('/')}/api/chat"
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=body)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        raise OllamaError(
            f"Ollama request failed ({settings.ollama_base_url}, "
            f"model={settings.ollama_model}): {exc}"
        ) from exc

    message = data.get("message")
    if not isinstance(message, dict):
        raise OllamaError(f"Unexpected Ollama response: {data!r}")
    return message


async def ping() -> dict[str, Any]:
    """Health check against the local Ollama daemon."""
    url = f"{settings.ollama_base_url.rstrip('/')}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
        models = [m.get("name") for m in data.get("models", [])]
        return {
            "ok": True,
            "base_url": settings.ollama_base_url,
            "configured_model": settings.ollama_model,
            "models": models,
            "model_present": any(
                settings.ollama_model == m or (m or "").startswith(settings.ollama_model)
                for m in models
            ),
        }
    except httpx.HTTPError as exc:
        return {
            "ok": False,
            "base_url": settings.ollama_base_url,
            "configured_model": settings.ollama_model,
            "error": str(exc),
        }
