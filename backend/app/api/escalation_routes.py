"""REST helpers for Ops escalation tickets (UI panel)."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agent import mcp_host
from app.mcp_server import tool_impl

router = APIRouter(prefix="/escalations", tags=["escalations"])


class EscalateRequest(BaseModel):
    question: str = Field(min_length=1)
    reason: str = "Associate requested human follow-up"
    store_id: str | None = "NM-204"
    priority: str = "normal"
    context: list[dict[str, str]] = Field(default_factory=list)


@router.get("")
def list_tickets(status: str | None = "open") -> dict:
    """List escalation tickets for the workspace side panel."""
    filt = status if status in {"open", "resolved"} else None
    return tool_impl.list_escalations(status=filt)


@router.post("")
async def create_ticket(body: EscalateRequest) -> dict:
    """Create an escalation through the MCP tool (same path as the agent)."""
    result_text = await mcp_host.call_mcp_tool(
        "create_escalation",
        {
            "question": body.question,
            "reason": body.reason,
            "store_id": body.store_id or "unknown",
            "priority": body.priority,
            "context_json": json.dumps(body.context),
        },
    )
    return json.loads(result_text)


@router.post("/{ticket_id}/resolve")
def resolve_ticket(ticket_id: str) -> dict:
    """Mark a ticket resolved from the Ops panel."""
    result = tool_impl.resolve_escalation(ticket_id)
    if not result.get("updated"):
        raise HTTPException(status_code=404, detail="Ticket not found")
    return result
