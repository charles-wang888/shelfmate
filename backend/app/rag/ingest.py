"""Build policy chunks, embed them, and load Weaviate."""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings
from app.core.model_settings import load_model_settings
from app.rag.chunking import chunk_policy_dir
from app.rag.embeddings import embed_texts
from app.rag import weaviate_store

logger = logging.getLogger(__name__)


async def reindex_policies() -> dict[str, Any]:
    """Chunk all policies, embed, and replace Weaviate contents."""
    chunks = chunk_policy_dir(settings.policies_dir)
    if not chunks:
        return {"ok": False, "error": "No policy documents found", "chunk_count": 0}

    # Embed in small batches to stay friendly to local Ollama.
    batch_size = 8
    vectors: list[list[float]] = []
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        vectors.extend(await embed_texts([c["text"] for c in batch]))

    emb_cfg = load_model_settings()["embedding"]
    count = weaviate_store.replace_all_chunks(chunks, vectors)
    return {
        "ok": True,
        "chunk_count": count,
        "doc_count": len({c["doc_id"] for c in chunks}),
        "embedding_model": emb_cfg.get("model"),
        "dimensions": len(vectors[0]) if vectors else emb_cfg.get("dimensions"),
    }


def list_documents() -> list[dict[str, Any]]:
    """List policy files with chunk counts (computed from filesystem chunking)."""
    chunks = chunk_policy_dir(settings.policies_dir)
    by_doc: dict[str, dict[str, Any]] = {}
    for chunk in chunks:
        doc = by_doc.setdefault(
            chunk["doc_id"],
            {
                "doc_id": chunk["doc_id"],
                "title": chunk["title"],
                "chunk_count": 0,
            },
        )
        doc["chunk_count"] += 1
    return list(by_doc.values())


def get_document(doc_id: str) -> dict[str, Any] | None:
    path = settings.policies_dir / f"{doc_id}.md"
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    chunks = chunk_policy_dir(settings.policies_dir)
    doc_chunks = [c for c in chunks if c["doc_id"] == doc_id]
    return {
        "doc_id": doc_id,
        "title": path.stem.replace("-", " "),
        "text": text,
        "chunks": doc_chunks,
    }
