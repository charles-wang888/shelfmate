"""Chat and health endpoints for the ShelfMate agent."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agent import ollama_client
from app.agent.llm import LLMError
from app.agent.orchestrator import run_chat
from app.core.model_settings import load_model_settings, public_model_settings
from app.rag import weaviate_store

router = APIRouter(tags=["chat"])


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1)
    store_id: str | None = "NM-204"


@router.get("/health")
async def health() -> dict:
    """Liveness probe plus model / vector-store reachability."""
    ollama = await ollama_client.ping()
    return {
        "ok": True,
        "service": "shelfmate",
        "ollama": ollama,
        "llm": public_model_settings()["llm"],
        "embedding": {
            "provider": load_model_settings()["embedding"]["provider"],
            "model": load_model_settings()["embedding"]["model"],
        },
        "weaviate": weaviate_store.health(),
    }


@router.post("/chat")
async def chat(body: ChatRequest) -> dict:
    """Run one grounded assistant turn via configured LLM + MCP tools."""
    payload = [m.model_dump() for m in body.messages]
    try:
        return await run_chat(payload, store_id=body.store_id)
    except LLMError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}") from exc
