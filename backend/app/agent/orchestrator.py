"""Chat agent: Ollama reasoning loop grounded by MCP tools."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.agent import llm, mcp_host
from app.agent.llm import LLMError
from app.core.config import settings
from app.core.model_settings import load_model_settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are ShelfMate, NovaMart's internal store assistant.

Rules:
1. Answer only from MCP tool results (policy search or order lookup). Never invent policies, prices, or order states.
2. For policy / returns / warranty / discount / shipping / privacy questions, call search_policies first.
3. For order / shipment / ETA / delivery questions, call get_order_status with the order id.
4. If tools return nothing useful, or the question is outside NovaMart store operations (PII, gossip, personal contacts, unrelated topics), refuse clearly. Prefer phrasing like "I don't know" or "I cannot provide that from NovaMart tools/docs." Do not guess.
5. When refusing, offer to escalate to Ops. Do NOT invent phone numbers, emails, salaries, or personal details.
6. Keep answers concise and operational. Cite document titles when using policy excerpts.
7. Prefer tools over memory. If unsure, use a tool or refuse.
"""

CANONICAL_REFUSAL = (
    "I don't know — that is outside what NovaMart store tools and policy docs can answer. "
    "I will not invent personal or confidential details. "
    "You can Escalate to Ops from the workspace if a human needs to follow up."
)

REFUSAL_MARKERS = (
    "i don't know",
    "i do not know",
    "cannot find",
    "can't find",
    "cannot provide",
    "can't provide",
    "no information",
    "not available through",
    "unable to answer",
    "outside my",
    "outside what novamart",
    "strictly confidential",
    "do not have access",
    "don't have access",
    "will not invent",
)

# Deterministic out-of-scope gate — keeps refuse demos stable without relying on the LLM.
_OUT_OF_SCOPE_PATTERNS = [
    re.compile(p, re.I)
    for p in [
        r"\bceo\b.*\b(phone|mobile|cell|email|address|salary|home)\b",
        r"\b(phone|mobile|cell|email|address|salary)\b.*\bceo\b",
        r"\bpersonal\s+(mobile|phone|cell|email|number)\b",
        r"\bhome\s+address\b",
        r"\bsocial\s+security\b",
        r"\bpassword\b",
        r"\bgossip\b",
        r"\bwho\s+is\s+dating\b",
        r"\bwrite\s+(me\s+)?(a\s+)?poem\b",
        r"\bweather\s+in\b",
        r"\bstock\s+price\b",
    ]
]

ORDER_ID_RE = re.compile(r"\bORD-\d+\b", re.I)


def _latest_user_text(messages: list[dict[str, str]]) -> str:
    for msg in reversed(messages):
        if msg.get("role") == "user":
            return (msg.get("content") or "").strip()
    return ""


def _is_out_of_scope(question: str) -> bool:
    """Return True when the ask is clearly outside store ops / policy / orders."""
    text = question.strip()
    if not text:
        return True
    return any(pat.search(text) for pat in _OUT_OF_SCOPE_PATTERNS)


def _extract_citations(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build UI citations from search_policies hits (similarity + confidence)."""
    citations: list[dict[str, Any]] = []
    seen: set[str] = set()
    for call in tool_calls:
        if call.get("name") != "search_policies":
            continue
        raw = call.get("result") or ""
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        mode = payload.get("mode")
        for hit in payload.get("results", []):
            key = str(hit.get("chunk_id") or hit.get("doc_id") or "")
            if key in seen:
                continue
            seen.add(key)
            citations.append(
                {
                    "doc_id": str(hit.get("doc_id", "")),
                    "title": str(hit.get("title", "")),
                    "chunk_id": hit.get("chunk_id"),
                    "excerpt": hit.get("excerpt") or "",
                    "similarity": hit.get("similarity"),
                    "score": hit.get("score"),
                    "confidence": hit.get("confidence") or "low",
                    "mode": mode,
                }
            )
    return citations


def _extract_sources(tool_calls: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Backward-compatible doc-level source list."""
    citations = _extract_citations(tool_calls)
    seen: set[str] = set()
    sources: list[dict[str, str]] = []
    for c in citations:
        if c["doc_id"] in seen:
            continue
        seen.add(c["doc_id"])
        sources.append({"doc_id": c["doc_id"], "title": c["title"]})
    return sources


def _looks_like_refusal(text: str) -> bool:
    lower = text.lower()
    return any(marker in lower for marker in REFUSAL_MARKERS)


def _search_was_empty(tool_trace: list[dict[str, Any]]) -> bool:
    used = False
    empty = True
    for t in tool_trace:
        if t["name"] != "search_policies":
            continue
        used = True
        try:
            payload = json.loads(t["result"])
            if payload.get("count", 0) > 0:
                empty = False
        except json.JSONDecodeError:
            pass
    return used and empty


def _normalize_tool_calls(message: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize Ollama tool_calls into [{id,name,arguments}]."""
    raw = message.get("tool_calls") or []
    normalized: list[dict[str, Any]] = []
    for idx, item in enumerate(raw):
        fn = item.get("function") if isinstance(item, dict) else None
        if not isinstance(fn, dict):
            continue
        name = fn.get("name")
        if not name:
            continue
        arguments = fn.get("arguments", {})
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments) if arguments else {}
            except json.JSONDecodeError:
                arguments = {"raw": arguments}
        if not isinstance(arguments, dict):
            arguments = {}
        normalized.append(
            {
                "id": item.get("id") or f"call_{idx}",
                "name": name,
                "arguments": arguments,
            }
        )
    return normalized


def _active_model_label() -> str:
    cfg = load_model_settings()["llm"]
    return f"{cfg.get('provider')}:{cfg.get('model')}"


def _refusal_payload(*, model_note: str | None = None) -> dict[str, Any]:
    answer = CANONICAL_REFUSAL
    if model_note:
        answer = f"{CANONICAL_REFUSAL}\n\n(Note: {model_note})"
    return {
        "answer": answer,
        "sources": [],
        "citations": [],
        "confidence": None,
        "tool_calls": [],
        "refused": True,
        "escalation": None,
        "model": _active_model_label(),
        "refuse_reason": "out_of_scope_gate",
    }


async def run_chat(
    messages: list[dict[str, str]],
    *,
    store_id: str | None = None,
) -> dict[str, Any]:
    """Run a grounded chat turn and return answer metadata for the API/UI."""
    question = _latest_user_text(messages)

    # Hard gate: do not invent PII / off-topic answers; keep eval demos stable.
    if _is_out_of_scope(question):
        logger.info("Out-of-scope gate fired for question=%r", question[:120])
        return _refusal_payload()

    tools = await mcp_host.list_mcp_tools()
    # Block create_escalation during normal grounded Q&A unless the model insists;
    # UI escalate button covers the creative loop. Keep tool available for agent choice.
    history: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in messages:
        history.append({"role": msg["role"], "content": msg["content"]})

    if store_id:
        history.insert(
            1,
            {
                "role": "system",
                "content": (
                    f"Current store context store_id={store_id}. "
                    "Include it when creating escalations."
                ),
            },
        )

    tool_trace: list[dict[str, Any]] = []
    assistant_text = ""
    refused = False
    escalation = None
    refuse_reason: str | None = None

    try:
        for _round in range(settings.max_tool_rounds):
            message = await llm.chat(history, tools=tools)
            tool_calls = _normalize_tool_calls(message)
            content = (message.get("content") or "").strip()

            if tool_calls:
                history.append(message)
                for call in tool_calls:
                    args = dict(call["arguments"])
                    if call["name"] == "create_escalation":
                        args.setdefault("store_id", store_id or "unknown")
                        if "context_json" not in args:
                            slim = [
                                {"role": m["role"], "content": m["content"][:400]}
                                for m in messages[-4:]
                            ]
                            args["context_json"] = json.dumps(slim)

                    result_text = await mcp_host.call_mcp_tool(call["name"], args)
                    tool_trace.append(
                        {
                            "name": call["name"],
                            "arguments": args,
                            "result": result_text,
                        }
                    )
                    if call["name"] == "create_escalation":
                        try:
                            escalation = json.loads(result_text).get("ticket")
                        except json.JSONDecodeError:
                            escalation = None

                    history.append(
                        {
                            "role": "tool",
                            "tool_name": call["name"],
                            "tool_call_id": call.get("id"),
                            "content": result_text,
                        }
                    )
                continue

            assistant_text = content
            break
        else:
            message = await llm.chat(history, tools=None)
            assistant_text = (message.get("content") or "").strip()
    except LLMError:
        raise

    used_order = any(t["name"] == "get_order_status" for t in tool_trace)
    used_search = any(t["name"] == "search_policies" for t in tool_trace)
    order_found = False
    for t in tool_trace:
        if t["name"] != "get_order_status":
            continue
        try:
            if json.loads(t["result"]).get("found"):
                order_found = True
        except json.JSONDecodeError:
            pass
    grounded = order_found or (used_search and not _search_was_empty(tool_trace))

    if not assistant_text:
        assistant_text = CANONICAL_REFUSAL
        refused = True
        refuse_reason = "empty_model_answer"
    elif grounded:
        # Evidence from tools — do not false-positive on words like "escalate" in policy text.
        refused = False
        refuse_reason = None
    elif _search_was_empty(tool_trace) and not used_order:
        refused = True
        refuse_reason = "empty_policy_search"
        assistant_text = CANONICAL_REFUSAL
    elif not used_search and not used_order:
        refused = True
        refuse_reason = "ungrounded_answer"
        assistant_text = CANONICAL_REFUSAL
    elif _looks_like_refusal(assistant_text):
        refused = True
        refuse_reason = "model_refusal_language"
        if "i don't know" not in assistant_text.lower():
            assistant_text = f"{CANONICAL_REFUSAL}\n\n{assistant_text}"
    else:
        refused = True
        refuse_reason = "ungrounded_answer"
        assistant_text = CANONICAL_REFUSAL

    sources = _extract_sources(tool_trace)
    citations = _extract_citations(tool_trace)
    top_conf = None
    if citations:
        order = {"high": 3, "medium": 2, "low": 1}
        top_conf = max(
            (c.get("confidence") or "low" for c in citations),
            key=lambda x: order.get(str(x), 0),
        )
    return {
        "answer": assistant_text,
        "sources": sources,
        "citations": citations,
        "confidence": None if refused else top_conf,
        "tool_calls": [
            {
                "name": t["name"],
                "arguments": t["arguments"],
                "result_preview": (t["result"] or "")[:500],
            }
            for t in tool_trace
        ],
        "refused": refused,
        "escalation": escalation,
        "model": _active_model_label(),
        "refuse_reason": refuse_reason,
    }


async def run_eval_case(case: dict[str, Any]) -> dict[str, Any]:
    """Execute one evaluation case and compute a simple pass/fail."""
    result = await run_chat(
        [{"role": "user", "content": case["question"]}],
        store_id=case.get("store_id"),
    )
    checks: list[dict[str, Any]] = []
    expect = case.get("expect", {})
    tool_names = [t["name"] for t in result["tool_calls"]]

    if "refused" in expect:
        ok = bool(result["refused"]) == bool(expect["refused"])
        checks.append({"name": "refused", "ok": ok, "actual": result["refused"]})

    if "tool" in expect:
        ok = expect["tool"] in tool_names
        checks.append({"name": "tool", "ok": ok, "actual": tool_names})

    if "forbid_tools" in expect:
        forbidden = set(expect["forbid_tools"])
        hit = sorted(forbidden.intersection(tool_names))
        ok = len(hit) == 0
        checks.append({"name": "forbid_tools", "ok": ok, "actual": tool_names})

    if "answer_contains" in expect:
        needle = str(expect["answer_contains"]).lower()
        ok = needle in result["answer"].lower()
        checks.append({"name": "answer_contains", "ok": ok})

    if expect.get("has_sources"):
        ok = len(result["sources"]) > 0
        checks.append({"name": "has_sources", "ok": ok, "actual": result["sources"]})

    passed = all(c["ok"] for c in checks) if checks else True
    return {
        "id": case.get("id"),
        "question": case["question"],
        "passed": passed,
        "checks": checks,
        "result": {
            "answer": result["answer"],
            "sources": result["sources"],
            "tool_calls": result["tool_calls"],
            "refused": result["refused"],
            "refuse_reason": result.get("refuse_reason"),
            "model": result["model"],
        },
    }
