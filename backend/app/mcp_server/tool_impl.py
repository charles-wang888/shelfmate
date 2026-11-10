"""Business implementations behind ShelfMate MCP tools.

These functions are the single source of truth used by both the MCP server
process and (optionally) direct tests. The agent must call them through MCP.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings

_WORD_RE = re.compile(r"[a-z0-9]+", re.I)


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _escalations_path() -> Path:
    path = settings.storage_dir / "escalations" / "tickets.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("[]", encoding="utf-8")
    return path


def list_policy_documents() -> list[dict[str, str]]:
    """Return metadata for each policy markdown file."""
    docs: list[dict[str, str]] = []
    if not settings.policies_dir.exists():
        return docs
    for path in sorted(settings.policies_dir.glob("*.md")):
        docs.append(
            {
                "doc_id": path.stem,
                "title": path.stem.replace("-", " "),
                "path": str(path),
            }
        )
    return docs


def _confidence_label(similarity: float) -> str:
    if similarity >= 0.72:
        return "high"
    if similarity >= 0.55:
        return "medium"
    return "low"


def _keyword_search_policies(query: str, limit: int = 3) -> dict[str, Any]:
    """Fallback keyword retrieval when Weaviate / embeddings are unavailable."""
    tokens = {t.lower() for t in _WORD_RE.findall(query) if len(t) > 2}
    scored: list[tuple[int, dict[str, Any]]] = []

    for path in sorted(settings.policies_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        lower = text.lower()
        score = sum(1 for t in tokens if t in lower)
        score += sum(2 for t in tokens if t in path.stem.lower())
        if score <= 0 and tokens:
            continue
        if not tokens:
            score = 1
        excerpt = text.strip()
        if len(excerpt) > 900:
            excerpt = excerpt[:900] + "…"
        # Map crude keyword score into a 0-1 band for UI parity.
        similarity = min(0.95, 0.35 + 0.08 * score)
        scored.append(
            (
                score,
                {
                    "doc_id": path.stem,
                    "title": path.stem.replace("-", " "),
                    "chunk_id": f"{path.stem}::kw",
                    "score": round(similarity, 4),
                    "similarity": round(similarity, 4),
                    "confidence": _confidence_label(similarity),
                    "excerpt": excerpt,
                },
            )
        )

    scored.sort(key=lambda item: (-item[0], item[1]["doc_id"]))
    hits = [item[1] for item in scored[: max(1, limit)]]
    return {
        "query": query,
        "count": len(hits),
        "mode": "keyword_fallback",
        "results": hits,
    }


def search_policies(query: str, limit: int = 5) -> dict[str, Any]:
    """Retrieve grounded policy chunks via Weaviate + embeddings (MCP tool)."""
    try:
        from app.rag.embeddings import embed_query_sync
        from app.rag import weaviate_store

        vector = embed_query_sync(query)
        hits = weaviate_store.near_vector_search(vector, limit=max(1, limit))
        results = []
        for hit in hits:
            excerpt = (hit.get("text") or "").strip()
            if len(excerpt) > 900:
                excerpt = excerpt[:900] + "…"
            sim = float(hit.get("similarity") or 0.0)
            results.append(
                {
                    "doc_id": hit.get("doc_id"),
                    "title": hit.get("title"),
                    "chunk_id": hit.get("chunk_id"),
                    "chunk_index": hit.get("chunk_index"),
                    "score": hit.get("score"),
                    "similarity": sim,
                    "confidence": _confidence_label(sim),
                    "excerpt": excerpt,
                }
            )
        return {
            "query": query,
            "count": len(results),
            "mode": "weaviate_vector",
            "results": results,
        }
    except Exception as exc:  # noqa: BLE001
        fallback = _keyword_search_policies(query, limit=limit)
        fallback["warning"] = f"Vector search unavailable ({exc}); used keyword fallback."
        return fallback


def get_order_status(order_id: str) -> dict[str, Any]:
    """Look up a mock order by id (case-insensitive)."""
    orders = _load_json(settings.data_dir / "orders.json")
    needle = order_id.strip().upper()
    for order in orders:
        if str(order.get("order_id", "")).upper() == needle:
            return {"found": True, "order": order}
    return {
        "found": False,
        "order_id": order_id,
        "message": "No order found for that id in the mock OMS.",
    }


def create_escalation(
    question: str,
    reason: str,
    store_id: str | None = None,
    priority: str = "normal",
    context: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Open an Ops escalation ticket and persist it locally."""
    path = _escalations_path()
    tickets: list[dict[str, Any]] = _load_json(path)
    ticket = {
        "id": f"ESC-{uuid.uuid4().hex[:8].upper()}",
        "question": question.strip(),
        "reason": reason.strip(),
        "store_id": store_id or "unknown",
        "priority": priority if priority in {"low", "normal", "high"} else "normal",
        "context": context or [],
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    tickets.insert(0, ticket)
    path.write_text(json.dumps(tickets, indent=2), encoding="utf-8")
    return {"created": True, "ticket": ticket}


def list_escalations(status: str | None = "open") -> dict[str, Any]:
    """List escalation tickets, optionally filtered by status."""
    path = _escalations_path()
    tickets: list[dict[str, Any]] = _load_json(path)
    if status:
        tickets = [t for t in tickets if t.get("status") == status]
    return {"count": len(tickets), "tickets": tickets}


def resolve_escalation(ticket_id: str) -> dict[str, Any]:
    """Mark an escalation ticket as resolved."""
    path = _escalations_path()
    tickets: list[dict[str, Any]] = _load_json(path)
    for ticket in tickets:
        if ticket.get("id") == ticket_id:
            ticket["status"] = "resolved"
            ticket["resolved_at"] = datetime.now(timezone.utc).isoformat()
            path.write_text(json.dumps(tickets, indent=2), encoding="utf-8")
            return {"updated": True, "ticket": ticket}
    return {"updated": False, "ticket_id": ticket_id, "message": "Ticket not found"}
