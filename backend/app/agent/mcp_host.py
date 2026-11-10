"""MCP host client that talks to the shelfmate-tools stdio server."""

from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _mcp_child_env() -> dict[str, str]:
    """Inherit the full parent environment for the MCP stdio subprocess.

    The MCP SDK default env is a small whitelist. In Docker that drops
    TOKENHUB_API_KEY / WEAVIATE_URL / POLICIES_DIR, so vector search fails and
    keyword fallback cannot find policy files either — every answer becomes
    "I don't know".
    """
    env = {k: v for k, v in os.environ.items() if isinstance(v, str)}
    py_path = env.get("PYTHONPATH", "")
    parts = [p for p in py_path.split(os.pathsep) if p]
    root = str(BACKEND_ROOT)
    if root not in parts:
        parts.insert(0, root)
    env["PYTHONPATH"] = os.pathsep.join(parts)
    return env


def server_params() -> StdioServerParameters:
    """Launch parameters for the ShelfMate MCP server subprocess."""
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "app.mcp_server.server"],
        cwd=str(BACKEND_ROOT),
        env=_mcp_child_env(),
    )


@asynccontextmanager
async def mcp_session() -> AsyncIterator[ClientSession]:
    """Open a short-lived MCP client session against shelfmate-tools."""
    params = server_params()
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def list_mcp_tools() -> list[dict[str, Any]]:
    """Return MCP tools converted into Ollama/OpenAI-style function schemas."""
    async with mcp_session() as session:
        listed = await session.list_tools()
        tools: list[dict[str, Any]] = []
        for tool in listed.tools:
            schema = tool.inputSchema or {
                "type": "object",
                "properties": {},
            }
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description or tool.name,
                        "parameters": schema,
                    },
                }
            )
        return tools


async def call_mcp_tool(name: str, arguments: dict[str, Any]) -> str:
    """Invoke one MCP tool and flatten the content into a string payload."""
    async with mcp_session() as session:
        result = await session.call_tool(name, arguments=arguments)
        chunks: list[str] = []
        for block in result.content:
            text = getattr(block, "text", None)
            if text:
                chunks.append(text)
            else:
                chunks.append(str(block))
        payload = "\n".join(chunks).strip()
        if result.isError:
            logger.warning("MCP tool %s returned error: %s", name, payload)
            return json_error(payload or "MCP tool error")
        return payload or "{}"


def json_error(message: str) -> str:
    import json

    return json.dumps({"error": message})
