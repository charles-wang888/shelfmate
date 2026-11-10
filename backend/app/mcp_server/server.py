"""ShelfMate MCP server — exposes retail ops tools over stdio.

Run standalone:
  python -m app.mcp_server.server

The FastAPI agent host connects to this process via the MCP Python SDK.
"""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from app.mcp_server import tool_impl

mcp = FastMCP("shelfmate-tools")


@mcp.tool()
def search_policies(query: str, limit: int = 3) -> str:
    """Search NovaMart policy and product documents. Use this before answering policy, returns, warranty, shipping, or discount questions. Returns grounded excerpts only."""
    result = tool_impl.search_policies(query=query, limit=limit)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def get_order_status(order_id: str) -> str:
    """Look up live (mock) order status by order id such as ORD-10042. Use when the user asks about shipment, ETA, cancellation, or delivery state."""
    result = tool_impl.get_order_status(order_id=order_id)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def create_escalation(
    question: str,
    reason: str,
    store_id: str = "unknown",
    priority: str = "normal",
    context_json: str = "[]",
) -> str:
    """Create an Ops escalation ticket when the assistant cannot answer reliably. Pass a short reason and optional recent chat context as JSON list of {role, content}."""
    context: list[dict[str, Any]]
    try:
        parsed = json.loads(context_json) if context_json else []
        context = parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        context = []
    result = tool_impl.create_escalation(
        question=question,
        reason=reason,
        store_id=store_id,
        priority=priority,
        context=context,
    )
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def list_escalations(status: str = "open") -> str:
    """List Ops escalation tickets filtered by status (open|resolved|empty for all)."""
    filt = status if status in {"open", "resolved"} else None
    if status == "":
        filt = None
    result = tool_impl.list_escalations(status=filt)
    return json.dumps(result, ensure_ascii=False)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
