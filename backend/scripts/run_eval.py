"""Run ShelfMate eval cases in-process and write a conclusion report.

Usage (from backend/, with venv):
  .\\.venv\\Scripts\\python.exe scripts\\run_eval.py

Writes:
  ../EVAL_RESULTS.md          human-readable summary for the interview
  ../docs/eval_results.json   machine-readable dump
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.agent.orchestrator import run_eval_case  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.eval_cases import EVAL_CASES  # noqa: E402


def _failed_checks(case_result: dict) -> str:
    bad = [c["name"] for c in case_result.get("checks", []) if not c.get("ok")]
    return ", ".join(bad) if bad else "—"


def _markdown(payload: dict) -> str:
    lines = [
        "# ShelfMate evaluation results",
        "",
        f"- **When:** {payload['ran_at']}",
        f"- **Model:** `{payload['model']}`",
        f"- **Score:** **{payload['passed']}/{payload['total']} passed**"
        f" ({payload['failed']} failed)",
        "",
        "## Summary",
        "",
        "| Case | Result | Failed checks | Notes |",
        "| --- | --- | --- | --- |",
    ]
    for row in payload["results"]:
        status = "PASS" if row["passed"] else "FAIL"
        note = (row["result"].get("refuse_reason") or "") if row["result"].get("refused") else ""
        if not note:
            tools = ", ".join(t["name"] for t in row["result"].get("tool_calls", [])) or "—"
            note = f"tools: {tools}"
        lines.append(
            f"| `{row['id']}` | **{status}** | {_failed_checks(row)} | {note} |"
        )

    lines.extend(
        [
            "",
            "## How we judge quality",
            "",
            "- **policy-electronics-return**: must call `search_policies`, cite a source, mention `15`.",
            "- **order-status**: must call `get_order_status`, mention delivery/out_for_delivery.",
            "- **unknown-refuse**: must refuse (`I don't know`), and must **not** call policy/order tools.",
            "- **price-match**: must call `search_policies` with sources; must not refuse.",
            "",
            "## Refusal hardening",
            "",
            "Out-of-scope asks (CEO personal mobile, etc.) hit a **deterministic gate** before the LLM,",
            "so refuse demos stay stable. Ungrounded model answers are replaced with a canonical refuse.",
            "",
            "## Re-run",
            "",
            "```powershell",
            "cd backend",
            ".\\.venv\\Scripts\\python.exe scripts\\run_eval.py",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


async def _run() -> dict:
    results = []
    for case in EVAL_CASES:
        print(f"→ running {case['id']} ...", flush=True)
        results.append(await run_eval_case(case))
        status = "PASS" if results[-1]["passed"] else "FAIL"
        print(f"  {status}", flush=True)

    passed = sum(1 for r in results if r["passed"])
    return {
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "model": settings.ollama_model,
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "results": results,
    }


def main() -> int:
    payload = asyncio.run(_run())
    md_path = REPO_ROOT / "EVAL_RESULTS.md"
    json_path = REPO_ROOT / "docs" / "eval_results.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_markdown(payload), encoding="utf-8")
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {md_path}")
    print(f"Wrote {json_path}")
    print(f"passed={payload['passed']}/{payload['total']}")
    return 0 if payload["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
