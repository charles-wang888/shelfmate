"""Multi-provider chat LLM adapter (DeepSeek / Ollama / OpenAI / Anthropic / Google)."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.core.model_settings import load_model_settings

logger = logging.getLogger(__name__)


class LLMError(RuntimeError):
    """Raised when the configured chat model fails."""


async def chat(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    *,
    temperature: float = 0.2,
) -> dict[str, Any]:
    """Return an assistant message dict compatible with the orchestrator."""
    cfg = load_model_settings()["llm"]
    provider = (cfg.get("provider") or "deepseek").lower()
    if provider == "ollama":
        return await _chat_ollama(messages, tools, cfg, temperature=temperature)
    if provider in {"openai", "deepseek"}:
        if provider == "deepseek":
            cfg = {
                **cfg,
                "base_url": cfg.get("base_url") or "https://api.deepseek.com",
                "model": cfg.get("model") or "deepseek-chat",
            }
        return await _chat_openai(messages, tools, cfg, temperature=temperature)
    if provider == "anthropic":
        return await _chat_anthropic(messages, tools, cfg, temperature=temperature)
    if provider == "google":
        return await _chat_google(messages, tools, cfg, temperature=temperature)
    raise LLMError(f"Unsupported LLM provider: {provider}")


async def _chat_ollama(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None,
    cfg: dict[str, Any],
    *,
    temperature: float,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": cfg.get("model") or "qwen3:8b",
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if tools:
        body["tools"] = tools
    url = f"{str(cfg.get('base_url') or 'http://127.0.0.1:11434').rstrip('/')}/api/chat"
    timeout = float(cfg.get("timeout_seconds") or 120)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=body)
        try:
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMError(f"Ollama chat failed: {exc}") from exc
        message = resp.json().get("message")
        if not isinstance(message, dict):
            raise LLMError("Unexpected Ollama chat response")
        return message


def _openai_tools(tools: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
    return tools


async def _chat_openai(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None,
    cfg: dict[str, Any],
    *,
    temperature: float,
) -> dict[str, Any]:
    base = str(cfg.get("base_url") or "https://api.openai.com/v1").rstrip("/")
    if not base.endswith("/v1"):
        base = f"{base}/v1"
    headers = {"Authorization": f"Bearer {cfg.get('api_key') or ''}"}
    # Flatten tool role messages for OpenAI.
    oai_messages = []
    for msg in messages:
        role = msg.get("role")
        if role == "tool":
            oai_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": msg.get("tool_call_id") or msg.get("tool_name") or "tool",
                    "content": msg.get("content") or "",
                }
            )
        else:
            oai_messages.append({"role": role, "content": msg.get("content") or ""})
            if msg.get("tool_calls"):
                oai_messages[-1]["tool_calls"] = msg["tool_calls"]

    body: dict[str, Any] = {
        "model": cfg.get("model") or "gpt-4o-mini",
        "messages": oai_messages,
        "temperature": temperature,
    }
    if tools:
        body["tools"] = _openai_tools(tools)
    timeout = float(cfg.get("timeout_seconds") or 120)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(f"{base}/chat/completions", headers=headers, json=body)
        try:
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMError(f"OpenAI chat failed: {exc}") from exc
        choice = resp.json()["choices"][0]["message"]
        return {
            "role": "assistant",
            "content": choice.get("content") or "",
            "tool_calls": choice.get("tool_calls") or [],
        }


async def _chat_anthropic(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None,
    cfg: dict[str, Any],
    *,
    temperature: float,
) -> dict[str, Any]:
    """Anthropic Messages API with optional tool use."""
    system = ""
    converted: list[dict[str, Any]] = []
    for msg in messages:
        role = msg.get("role")
        if role == "system":
            system = f"{system}\n{msg.get('content') or ''}".strip()
            continue
        if role == "tool":
            converted.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg.get("tool_call_id") or "tool",
                            "content": msg.get("content") or "",
                        }
                    ],
                }
            )
            continue
        if role == "assistant" and msg.get("tool_calls"):
            content_blocks: list[dict[str, Any]] = []
            if msg.get("content"):
                content_blocks.append({"type": "text", "text": msg["content"]})
            for call in msg["tool_calls"]:
                fn = call.get("function") or {}
                args = fn.get("arguments") or {}
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {"raw": args}
                content_blocks.append(
                    {
                        "type": "tool_use",
                        "id": call.get("id") or "call",
                        "name": fn.get("name"),
                        "input": args,
                    }
                )
            converted.append({"role": "assistant", "content": content_blocks})
            continue
        converted.append({"role": "user" if role == "user" else "assistant", "content": msg.get("content") or ""})

    anth_tools = None
    if tools:
        anth_tools = []
        for tool in tools:
            fn = tool.get("function") or {}
            anth_tools.append(
                {
                    "name": fn.get("name"),
                    "description": fn.get("description") or "",
                    "input_schema": fn.get("parameters")
                    or {"type": "object", "properties": {}},
                }
            )

    body: dict[str, Any] = {
        "model": cfg.get("model") or "claude-3-5-haiku-latest",
        "max_tokens": 1024,
        "temperature": temperature,
        "messages": converted,
    }
    if system:
        body["system"] = system
    if anth_tools:
        body["tools"] = anth_tools

    base = str(cfg.get("base_url") or "https://api.anthropic.com").rstrip("/")
    headers = {
        "x-api-key": cfg.get("api_key") or "",
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    timeout = float(cfg.get("timeout_seconds") or 120)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(f"{base}/v1/messages", headers=headers, json=body)
        try:
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMError(f"Anthropic chat failed: {exc}") from exc
        data = resp.json()
        text_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []
        for block in data.get("content") or []:
            if block.get("type") == "text":
                text_parts.append(block.get("text") or "")
            elif block.get("type") == "tool_use":
                tool_calls.append(
                    {
                        "id": block.get("id"),
                        "type": "function",
                        "function": {
                            "name": block.get("name"),
                            "arguments": json.dumps(block.get("input") or {}),
                        },
                    }
                )
        return {
            "role": "assistant",
            "content": "\n".join(text_parts).strip(),
            "tool_calls": tool_calls,
        }


async def _chat_google(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None,
    cfg: dict[str, Any],
    *,
    temperature: float,
) -> dict[str, Any]:
    """Google Gemini generateContent (API key). Tool calling is best-effort."""
    model = cfg.get("model") or "gemini-2.0-flash"
    api_key = cfg.get("api_key") or ""
    base = str(cfg.get("base_url") or "https://generativelanguage.googleapis.com").rstrip("/")
    # Flatten to Gemini contents; system becomes a user preamble.
    system_bits = [m.get("content") or "" for m in messages if m.get("role") == "system"]
    contents: list[dict[str, Any]] = []
    if system_bits:
        contents.append({"role": "user", "parts": [{"text": "System:\n" + "\n".join(system_bits)}]})
        contents.append({"role": "model", "parts": [{"text": "Understood."}]})
    for msg in messages:
        if msg.get("role") == "system":
            continue
        role = "user" if msg.get("role") in {"user", "tool"} else "model"
        text = msg.get("content") or ""
        if msg.get("role") == "tool":
            text = f"Tool {msg.get('tool_name')}: {text}"
        contents.append({"role": role, "parts": [{"text": text}]})

    body: dict[str, Any] = {
        "contents": contents,
        "generationConfig": {"temperature": temperature},
    }
    # Gemini function declarations
    if tools:
        decls = []
        for tool in tools:
            fn = tool.get("function") or {}
            decls.append(
                {
                    "name": fn.get("name"),
                    "description": fn.get("description") or "",
                    "parameters": fn.get("parameters")
                    or {"type": "object", "properties": {}},
                }
            )
        body["tools"] = [{"functionDeclarations": decls}]

    url = f"{base}/v1beta/models/{model}:generateContent?key={api_key}"
    timeout = float(cfg.get("timeout_seconds") or 120)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=body)
        try:
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMError(f"Google Gemini chat failed: {exc}") from exc
        data = resp.json()
        parts = data["candidates"][0]["content"]["parts"]
        text_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []
        for part in parts:
            if "text" in part:
                text_parts.append(part["text"])
            if "functionCall" in part:
                fc = part["functionCall"]
                tool_calls.append(
                    {
                        "id": f"call_{fc.get('name')}",
                        "type": "function",
                        "function": {
                            "name": fc.get("name"),
                            "arguments": json.dumps(fc.get("args") or {}),
                        },
                    }
                )
        return {
            "role": "assistant",
            "content": "\n".join(text_parts).strip(),
            "tool_calls": tool_calls,
        }
