# ShelfMate

NovaMart’s internal AI assistant for **store associates** and **Ops**.

ShelfMate answers questions **grounded in company policy documents**, looks up **mock live order status** through **MCP tools**, **refuses** when it does not know, and can **Escalate to Ops** so a human can close the loop.

This repository is the Artefact take-home submission: a working prototype plus evaluation notes and a short production note.

## What this demo covers (brief requirements)

| Requirement | How ShelfMate shows it |
| --- | --- |
| Grounded answers from docs | Policies in `docs/policies/` → chunked → embedded → Weaviate → MCP `search_policies` |
| At least one live tool | MCP `get_order_status` over mock OMS data (`ORD-10042`, …) |
| Refuse when unsure | Deterministic out-of-scope gate + ungrounded-answer rewrite to a canonical “I don’t know” |
| Production thinking | See [`PRODUCTION_NOTE.md`](PRODUCTION_NOTE.md) |
| Creative bet | **Escalate to Ops** (`create_escalation` + workspace ticket panel) |

## Assumptions

- Users are authenticated store associates / admins (demo login only — not SSO).
- Policy corpus is the ten markdown files shipped in-repo (not a live CMS).
- Orders are mocked JSON for the take-home; production would call OMS read-only APIs.
- Default local stack uses **Ollama** for chat + embeddings; Settings also support OpenAI-compatible / Anthropic / Google chat and OpenAI-compatible embeddings (e.g. cloud providers).
- English UI; product name **ShelfMate**.

## Product flows

1. `/` landing → `/login` → `/app` chat workspace  
2. Policy Q&A via MCP `search_policies` (Weaviate near-vector + keyword fallback)  
3. Order lookup via MCP `get_order_status`  
4. Refuse + **Escalate to Ops** (`create_escalation` / `list_escalations`)  
5. `/app/knowledge` — browse chunks and trial retrieval with confidence  
6. `/app/settings` — Chat model / Embedding / Vector store (+ reindex)  
7. Eval harness — [`EVAL_RESULTS.md`](EVAL_RESULTS.md)

## Architecture

```
Browser (React/Vite)
    │  /api/*
FastAPI host
    ├─ Auth (demo JWT)
    ├─ Agent orchestrator (tool loop + refuse rules)
    ├─ MCP host ──► shelfmate-tools (stdio)
    │                  ├ search_policies
    │                  ├ get_order_status
    │                  ├ create_escalation
    │                  └ list_escalations
    ├─ RAG: chunk → embed → Weaviate (BYO vectors)
    └─ LLM adapter (Ollama / OpenAI-compatible / Anthropic / Google)
```

Creative bet kept: **Escalate to Ops** — when the assistant refuses or the associate needs a human, a ticket is written with store id + transcript context.

## Quick start (local)

### Prerequisites

- Docker Desktop (for Weaviate; optional full compose)  
- Node.js 20+ (frontend)  
- Python 3.12+ (backend)  
- [Ollama](https://ollama.com) with models below (default local path)

```powershell
ollama pull qwen3:8b
ollama pull qwen3-embedding
```

### 1) Weaviate

```powershell
cd shelfmate
docker compose up -d weaviate
# HTTP http://127.0.0.1:8088  (gRPC mapped on 50058)
```

### 2) Backend

```powershell
copy backend\.env.example backend\.env
# Edit backend\.env if you use cloud LLM/embedding keys instead of Ollama
powershell -ExecutionPolicy Bypass -File .\start-backend.ps1
# http://127.0.0.1:8000
```

Open **Settings → Vector store → Reindex policies** once embeddings are reachable.

### 3) Frontend

```powershell
powershell -ExecutionPolicy Bypass -File .\start-frontend.ps1
# http://localhost:5173
```

### Demo login

| Username | Password | Role |
| --- | --- | --- |
| `admin` | `admin123` | admin |
| `store` | `store123` | associate |

### Optional: full local Docker stack (app + Weaviate + Ollama)

```powershell
copy .env.docker.example .env
docker compose up -d --build
# App http://localhost:8080
```

First boot may take several minutes while Ollama pulls models; empty collections auto-reindex when `SHELFMATE_AUTO_REINDEX=1`.

### Optional: cloud chat + embedding (no local LLM)

Use OpenAI-compatible endpoints via `backend/.env` (placeholders only in `.env.example`) or the Settings UI:

- Chat: e.g. DeepSeek `deepseek-chat`  
- Embedding: any OpenAI-compatible `/v1/embeddings` model (dimension must match reindex)

Then reindex after changing embedding model/dimensions.

**Never commit real API keys.** Keep them in `backend/.env` (gitignored) or paste once in Settings.

## Try these prompts

| Prompt | Expected behavior |
| --- | --- |
| “What is the return window for opened electronics?” | `search_policies` → cite electronics policy (15 days) |
| “Where is order ORD-10042?” | `get_order_status` → live-ish mock status |
| “What is the CEO’s personal mobile number?” | Refuse (out-of-scope gate) |
| After a refuse: Escalate to Ops | Creates a ticket visible in the workspace panel |

## Evaluation

Latest recorded run: **4/4** on the golden set — see [`EVAL_RESULTS.md`](EVAL_RESULTS.md).

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\run_eval.py
```

Cases cover: policy retrieval, order tool, refuse, price-match grounding.

## Key decisions

1. **MCP as the tool boundary** — retrieval and OMS are not hidden side effects; the model must call tools, and the UI shows tool traces.  
2. **Weaviate + BYO vectors** — controllable RAG with similarity → confidence labels for associates.  
3. **Refuse in code, not only in the prompt** — out-of-scope regex gate + “empty search / ungrounded answer” rewrite so demos stay stable.  
4. **Escalate to Ops** — product-shaped creativity: refuse is not a dead end; associates get a human path with context.  
5. **Settings-first multi-provider LLM/embedding** — prototype stays local-first (Ollama) but can switch to customer cloud endpoints without rewriting the agent.

## With more time

- Streaming answers; stronger chunking + rerank; hybrid search  
- SSO / store-scoped ACLs; audit log per tool call  
- Real OMS + ServiceNow/Jira adapters behind the same MCP contracts  
- Larger eval suite (latency, tool-choice, jailbreaks) in CI  
- Managed vector DB + enterprise model endpoint (see production note)

## Repository map

```
shelfmate/
  README.md
  PRODUCTION_NOTE.md
  EVAL_RESULTS.md
  docker-compose.yml          # Weaviate (+ optional full Ollama stack)
  docs/policies/              # NovaMart policy corpus
  backend/app/agent/          # Orchestrator + LLM + MCP host
  backend/app/rag/            # Chunk / embed / Weaviate
  backend/app/mcp_server/     # MCP tools
  backend/scripts/run_eval.py
  frontend/src/pages/         # Landing, Login, Chat, Knowledge, Settings
```

## Production note

See [`PRODUCTION_NOTE.md`](PRODUCTION_NOTE.md) (≤ 1 page): platform choice, connecting real data, security/governance, evaluation & rollout.
