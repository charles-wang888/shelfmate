# ShelfMate — Production Note (NovaMart)

## Platform choice

This prototype runs on **local Ollama + Weaviate + a custom FastAPI host + MCP tools** so we can demonstrate chunked RAG with confidence scores, tool use, refusal, and Ops escalation with full control. Settings already allow switching the chat model to OpenAI / Anthropic / Google for customer-aligned demos. For NovaMart production, I would **not** standardize on laptop Ollama. I would pick a managed enterprise stack — most likely **Claude Managed Agents** or **ChatGPT Enterprise / Azure OpenAI** if NovaMart already has that agreement; **Gemini Enterprise** if Google Workspace is the corporate backbone. Decision criteria: SSO, VPC/private networking, data retention controls, eval hooks, and total cost for ~N store associates.

Managed agents win for speed-to-hardening (guardrails, logging, admin). A custom build (this repo’s shape) wins when NovaMart needs first-class MCP tool governance across OMS, IAM, and ticketing. Hybrid is realistic: managed model endpoint + first-party MCP tool servers.

## Connecting real data

- **Policies**: sync from the official policy CMS into a versioned corpus; replace keyword search with embeddings + ACL filters by role/region.  
- **Orders**: replace the mock MCP `get_order_status` with an OMS adapter (read-only service account, timeout + cache).  
- **Escalations**: map `create_escalation` to ServiceNow / Jira / NovaMart Ops inbox; include store id, associate id, and transcript.

## Security & governance

- SSO (OIDC) and store-scoped authorization; never expose PII tools to the open internet.  
- Prompt/tool allowlists; block free-form SQL/shell.  
- Audit every tool call; redact payment data in logs.  
- DLP on transcripts; retention aligned with retail compliance.  
- Separate prod MCP servers from prototype mocks with signed configs.

## Quality evaluation & monitoring

- Golden-set evals (policy, order, refuse, escalate) in CI before model/prompt changes.  
- Online monitors: refusal rate, tool error rate, escalation reopen rate, associate thumbs-down.  
- Sample weekly human review of refused and escalated chats; feed misses back into docs and tools.  
- Alert when groundedness checks fail (answer without retrieval/tool evidence).

## Rollout sketch

Pilot 3 stores → measure deflection vs Ops tickets → expand. Keep a human “Escalate to Ops” path forever; the product promise is reliable help, not zero humans.
