"""Settings API — chat model, embedding model, vector store."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.model_settings import load_model_settings, public_model_settings, save_model_settings
from app.rag import weaviate_store
from app.rag.ingest import reindex_policies

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsPatch(BaseModel):
    llm: dict[str, Any] | None = None
    embedding: dict[str, Any] | None = None
    vector_store: dict[str, Any] | None = None


@router.get("/models")
def get_models() -> dict:
    """Return editable model settings with masked secrets."""
    return public_model_settings()


@router.put("/models")
def put_models(body: SettingsPatch) -> dict:
    """Persist settings; empty api_key keeps the previous secret."""
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    save_model_settings(patch)
    return public_model_settings()


@router.get("/vector-store/health")
def vector_health() -> dict:
    return weaviate_store.health()


@router.post("/vector-store/reindex")
async def vector_reindex() -> dict:
    """Chunk policies, embed with configured model, load Weaviate."""
    try:
        result = await reindex_policies()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error") or "reindex failed")
    return result
