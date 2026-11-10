"""Lightweight evaluation harness for the take-home case."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.agent.llm import LLMError
from app.agent.orchestrator import run_eval_case
from app.eval_cases import EVAL_CASES

router = APIRouter(prefix="/eval", tags=["eval"])


@router.get("/cases")
def list_cases() -> dict:
    """Return the fixed evaluation case definitions."""
    return {"count": len(EVAL_CASES), "cases": EVAL_CASES}


@router.post("/run")
async def run_eval() -> dict:
    """Execute all evaluation cases against the live Ollama + MCP stack."""
    results = []
    try:
        for case in EVAL_CASES:
            results.append(await run_eval_case(case))
    except LLMError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    passed = sum(1 for r in results if r["passed"])
    return {
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "results": results,
    }
