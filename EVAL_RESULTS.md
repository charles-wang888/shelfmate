# ShelfMate evaluation results

- **When:** 2026-11-10T00:37:35.688821+00:00
- **Model:** `qwen3:8b`
- **Score:** **4/4 passed** (0 failed)

## Summary

| Case | Result | Failed checks | Notes |
| --- | --- | --- | --- |
| `policy-electronics-return` | **PASS** | — | tools: search_policies |
| `order-status` | **PASS** | — | tools: get_order_status |
| `unknown-refuse` | **PASS** | — | out_of_scope_gate |
| `price-match` | **PASS** | — | tools: search_policies |

## How we judge quality

- **policy-electronics-return**: must call `search_policies`, cite a source, mention `15`.
- **order-status**: must call `get_order_status`, mention delivery/out_for_delivery.
- **unknown-refuse**: must refuse (`I don't know`), and must **not** call policy/order tools.
- **price-match**: must call `search_policies` with sources; must not refuse.

## Refusal hardening

Out-of-scope asks (CEO personal mobile, etc.) hit a **deterministic gate** before the LLM,
so refuse demos stay stable. Ungrounded model answers are replaced with a canonical refuse.

## Re-run

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\run_eval.py
```
