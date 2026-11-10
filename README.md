# ShelfMate

NovaMart’s internal AI assistant for **store associates** and **Ops**.

ShelfMate answers questions **grounded in company policy documents**, looks up **mock live order status** through **MCP tools**, **refuses** when it does not know, and can **Escalate to Ops** so a human can close the loop.

This repository is the Artefact take-home submission: a working prototype plus evaluation notes and a short production note.

## Live demo

| | |
| --- | --- |
| **URL** | [http://124.223.213.17:8080/](http://124.223.213.17:8080/) |
| **Username** | `admin` |
| **Password** | `admin123` |

Stack on the demo host: **DeepSeek `deepseek-chat`** (LLM) + **Tencent TokenHub `kinfra-text-embedding-0.6b`** (embeddings, 1024-d) + **Weaviate** (vector store).

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
- **Default models for this submission:** DeepSeek chat + Tencent TokenHub embeddings (OpenAI-compatible `/v1/embeddings`). Settings still allow switching providers without rewriting the agent.
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
    └─ LLM / embedding adapters
         ├ Chat: DeepSeek deepseek-chat (default)
         └ Embed: Tencent TokenHub kinfra-text-embedding-0.6b (1024-d)
```

Creative bet kept: **Escalate to Ops** — when the assistant refuses or the associate needs a human, a ticket is written with store id + transcript context.

## Models used in this submission

| Role | Provider | Model / endpoint |
| --- | --- | --- |
| Chat LLM | DeepSeek | `deepseek-chat` (`https://api.deepseek.com`) |
| Embedding | Tencent Cloud TokenHub | `kinfra-text-embedding-0.6b` (1024 dimensions) |
| Vector store | Weaviate 1.27 | collection `ShelfMatePolicyChunk` |

Configure keys in `backend/.env` (gitignored). Placeholders only in `backend/.env.example`:

```env
DEEPSEEK_API_KEY=sk-your-deepseek-key
TOKENHUB_API_KEY=sk-your-tokenhub-key
```

**Never commit real API keys.**

## Quick start (local)

### Prerequisites

- Docker Desktop (Weaviate)  
- Node.js 20+  
- Python 3.12+  
- DeepSeek API key + Tencent TokenHub API key  

### 1) Weaviate

```powershell
cd shelfmate
docker compose up -d weaviate
# HTTP http://127.0.0.1:8088  (gRPC mapped on 50058)
```

### 2) Backend

```powershell
copy backend\.env.example backend\.env
# Fill DEEPSEEK_API_KEY and TOKENHUB_API_KEY
powershell -ExecutionPolicy Bypass -File .\start-backend.ps1
# http://127.0.0.1:8000
```

Open **Settings → Vector store → Reindex policies** once (or rely on auto-reindex when configured).

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

### Optional: Docker app stack (Weaviate + backend + frontend, cloud models)

```powershell
copy .env.cloud.example .env
# Fill DEEPSEEK_API_KEY and TOKENHUB_API_KEY in .env
docker compose -f docker-compose.cloud.yml up -d --build
# App http://localhost:8080
```

## Try these prompts

| Prompt | Expected behavior |
| --- | --- |
| “What is the return window for opened electronics?” | `search_policies` → cite electronics policy (15 days) |
| “Can we price match a local competitor flyer?” | `search_policies` → price-match policy |
| “Where is order ORD-10042?” | `get_order_status` → live-ish mock status |
| “What is the CEO’s personal mobile number?” | Refuse (out-of-scope gate) |
| After a refuse: Escalate to Ops | Creates a ticket visible in the workspace panel |

## Evaluation

Latest recorded golden-set run: **4/4** — see [`EVAL_RESULTS.md`](EVAL_RESULTS.md).

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\run_eval.py
```

Cases cover: policy retrieval, order tool, refuse, price-match grounding.

## Key decisions

1. **MCP as the tool boundary** — retrieval and OMS are not hidden side effects; the model must call tools, and the UI shows tool traces.  
2. **Weaviate + BYO vectors** — controllable RAG with similarity → confidence labels for associates.  
3. **Cloud LLM + cloud embeddings for the demo** — DeepSeek for tool-capable chat; TokenHub `kinfra-text-embedding-0.6b` for cheap, fast 1024-d retrieval without hosting a local model.  
4. **Refuse in code, not only in the prompt** — out-of-scope regex gate + “empty search / ungrounded answer” rewrite so demos stay stable.  
5. **Escalate to Ops** — product-shaped creativity: refuse is not a dead end; associates get a human path with context.  
6. **Settings-first multi-provider adapters** — switch chat/embedding endpoints without rewriting the orchestrator.

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
  docker-compose.yml            # Weaviate (local)
  docker-compose.cloud.yml      # App + Weaviate using cloud LLM/embedding
  docs/policies/                # NovaMart policy corpus
  backend/app/agent/            # Orchestrator + LLM + MCP host
  backend/app/rag/              # Chunk / embed / Weaviate
  backend/app/mcp_server/       # MCP tools
  backend/scripts/run_eval.py
  frontend/src/pages/           # Landing, Login, Chat, Knowledge, Settings
```

## Production note

See [`PRODUCTION_NOTE.md`](PRODUCTION_NOTE.md) (≤ 1 page): platform choice, connecting real data, security/governance, evaluation & rollout.
