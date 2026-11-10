"""Knowledge base browse + trial search APIs."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.mcp_server import tool_impl
from app.rag.ingest import get_document, list_documents

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/documents")
def documents() -> dict:
    docs = list_documents()
    return {"count": len(docs), "documents": docs}


@router.get("/documents/{doc_id}")
def document_detail(doc_id: str) -> dict:
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get("/search")
def knowledge_search(q: str = Query(min_length=1), limit: int = 5) -> dict:
    """Trial retrieval used by the Knowledge page debugger."""
    return tool_impl.search_policies(query=q, limit=limit)
