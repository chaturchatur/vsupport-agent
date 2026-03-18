# Decision Log

> Last verified: 2026-03-18 (Added callerName to structuredDataPlan)

A chronological record of architectural and design decisions — and any reversals — with rationale.

## How to Use This File

Each decision entry follows this format:

```
### [YYYY-MM-DD] Decision Title
**Status:** accepted | superseded | reversed
**Context:** What prompted this decision.
**Decision:** What we decided.
**Why:** The reasoning behind it.
**Alternatives considered:** What else we looked at (if any).
**Superseded by:** (only if status is superseded/reversed) Link to the newer decision.
```

---

## Decisions

### [2025-XX-XX] n8n Cloud as primary integration layer (not FastAPI)
**Status:** accepted
**Context:** Needed to connect VAPI tool calls to Airtable for caller lookup and interaction logging.
**Decision:** Use n8n Cloud for all webhook handling and Airtable CRUD. FastAPI stays as a thin utility layer (phone normalization only).
**Why:** n8n provides visual workflow editing, built-in Airtable nodes, and webhook handling with zero boilerplate. Keeps FastAPI lightweight and avoids duplicating integration logic.
**Alternatives considered:** Building all integrations in FastAPI; using Zapier instead of n8n.

### [2025-XX-XX] VAPI tool definitions inside `model.tools[]`, not top-level
**Status:** accepted
**Context:** VAPI API rejected tool definitions placed at the assistant's top level.
**Decision:** Define all tools inside `model.tools[]` in the assistant config.
**Why:** VAPI API requirement — tools must be nested under the model object.
**Alternatives considered:** None; this is an API constraint.

### [2025-XX-XX] Webhook auth via `server.headers` instead of `server.secret`
**Status:** accepted
**Context:** `server.secret` field is not supported by the VAPI API despite appearing in some docs.
**Decision:** Pass the webhook secret via `server.headers["x-vapi-secret"]` with Header Auth credential in n8n.
**Why:** Only working auth mechanism for VAPI → n8n webhook calls.
**Alternatives considered:** `server.secret` (doesn't work).

### [2025-XX-XX] CLI-wrapping skills over MCP servers
**Status:** accepted
**Context:** Needed tooling for VAPI and Airtable management within Claude Code.
**Decision:** Wrap existing CLIs (`vapi`, `pyairtable`) as custom Claude Code skills instead of building MCP servers.
**Why:** Simpler, leverages existing battle-tested CLIs, avoids maintaining separate server processes.
**Alternatives considered:** Building custom MCP servers for each service.

### [2025-XX-XX] Deploy via REST API script, not VAPI CLI `create`
**Status:** accepted
**Context:** VAPI CLI `create` command is interactive-only, can't be scripted.
**Decision:** Use `scripts/deploy-vapi.sh` which calls the VAPI REST API directly (`POST /assistant` or `PATCH /assistant/:id`).
**Why:** Enables repeatable, non-interactive deployments with placeholder resolution.
**Alternatives considered:** VAPI CLI (interactive-only, not scriptable).

### [2026-03-17] Replace Airtable with Supabase PostgreSQL
**Status:** accepted
**Context:** Airtable has hard scalability limits: 5 req/sec rate limit, no indexing, no unique constraints, 50k record cap. The end-of-call-report dedup required a hacky 10-second wait + search approach.
**Decision:** Migrate data store from Airtable to Supabase PostgreSQL.
**Why:** Proper database features — indexes, unique constraints (`vapi_call_id UNIQUE`), `INSERT ON CONFLICT DO NOTHING` for atomic dedup. Eliminates 10s wait hack entirely.
**Alternatives considered:** Keeping Airtable and working around limits.

### [2026-03-17] n8n Postgres node → Supabase (not FastAPI as DB intermediary)
**Status:** superseded
**Context:** Initial Supabase migration routed n8n → FastAPI (HTTP Request) → Supabase (supabase-py). This required deploying FastAPI to a cloud host reachable from n8n Cloud, meaning two separate cloud services to manage.
**Decision:** Use n8n's built-in Postgres node to connect directly to Supabase. FastAPI reverts to utility-only (`/health`, `/normalize-phone`).
**Why:** Eliminates the need to host FastAPI on a separate cloud. Single-cloud deployment (n8n Cloud) with Supabase as managed database. Simpler operational overhead.
**Alternatives considered:** FastAPI as DB intermediary (more testable Python code, but requires managing a second cloud deployment).
**Supersedes:** Initial Supabase migration approach (FastAPI as DB layer).
**Superseded by:** Supabase node via REST API (below).

### [2026-03-17] Supabase node (REST API) instead of Postgres node (wire protocol)
**Status:** accepted
**Context:** n8n Cloud could not connect to Supabase's Postgres wire protocol (ports 5432/6543) due to IPv6 connectivity issues (`ENETUNREACH` on IPv6 addresses). Both the direct host (`db.<ref>.supabase.co`) and the connection pooler (`aws-0-*.pooler.supabase.com`) failed.
**Decision:** Use n8n's built-in Supabase node (`n8n-nodes-base.supabase`) which connects via the REST API (PostgREST over HTTPS, port 443) instead of the Postgres wire protocol.
**Why:** HTTPS connections resolve correctly and bypass IPv6 routing issues. The Supabase credential (host URL + service role key) works immediately. No SQL injection concerns since PostgREST filters replace raw SQL. Dedup still works via unique constraint + `onError: continueRegularOutput`.
**Alternatives considered:** Supabase IPv4 add-on (~$4/mo) to fix the Postgres connection; keeping the Postgres node approach.
**Supersedes:** n8n Postgres node → Supabase (direct wire protocol).

### [2026-03-18] HTTP Request node for Lookup Caller reads (bypass Supabase node `encodeURI` bug)
**Status:** superseded
**Context:** Phone lookups by E.164 number (e.g., `+17185557777`) returned 0 rows despite correct data. Root cause: the n8n Supabase node applies `encodeURI()` to the `filterString` parameter. `encodeURI` preserves `+` (interpreted as space by PostgREST → no match). Using `encodeURIComponent` to pre-encode `+` as `%2B` also fails because `encodeURI` double-encodes `%` to `%25`, producing `%252B`.
**Decision:** Replace the Supabase node in the Lookup Caller workflow with an HTTP Request node (`n8n-nodes-base.httpRequest`). The Parse Envelope Code node builds the full Supabase REST URL with `encodeURIComponent()` for filter values, and the HTTP Request node passes it through without re-encoding. Auth via predefined `supabaseApi` credential.
**Why:** The HTTP Request node does not apply `encodeURI()` to the URL, so `%2B` reaches PostgREST correctly. Log Interaction and End-of-Call Report workflows still use the Supabase node (writes don't involve `+` in filter strings).
**Alternatives considered:** Storing phone numbers without `+` prefix (data model change, affects all workflows); creating a Postgres RPC function (more infrastructure); using Supabase node's manual filter mode (doesn't support dynamic OR conditions).
**Superseded by:** `phone_digits` generated column (below).

### [2026-03-18] `phone_digits` generated column to fix `+` encoding (keep Supabase node for all workflows)
**Status:** accepted
**Context:** The HTTP Request node workaround (above) solved the `+` encoding issue but introduced inconsistency — Lookup Caller used a different node type than all other workflows. Prefer a uniform Supabase node approach across all workflows.
**Decision:** Add a `phone_digits` generated column to the `customers` table (`replace(phone_number, '+', '')` — STORED). Lookup Caller queries `phone_digits.eq.14155551234` instead of `phone_number.eq.+14155551234`, so `+` never appears in the PostgREST filter string. All workflows use the Supabase node.
**Why:** Solves the encoding issue at the database level. No `+` in filter values → no `encodeURI()` problem. Keeps all n8n workflows on the same node type (Supabase node). The generated column is indexed (`idx_customers_phone_digits`) and automatically maintained by Postgres — zero application-level overhead.
**Alternatives considered:** HTTP Request node workaround (worked but inconsistent node types); storing phones without `+` (breaks E.164 standard in the canonical column, affects all workflows).

### [2026-03-18] DOB verification as LLM-side comparison (no new tool or workflow)
**Status:** accepted
**Context:** Needed a date-of-birth authentication layer after phone/name verification to add security before revealing claim information.
**Decision:** Add `date_of_birth` column to customers table, return it in the `lookup_caller` single-match response, and instruct the LLM via system prompt (Section 2b) to ask for and compare DOB before proceeding to claim status. Two attempts allowed; stored DOB must never be revealed to the caller.
**Why:** No new n8n workflow or tool call needed — the LLM already receives the customer record from `lookup_caller` and can compare the spoken DOB against the stored value. Keeps architecture simple. DOB matching is flexible (handles spoken dates like "March 15th, 1985" vs stored `1985-03-15`).
**Alternatives considered:** A dedicated `verify_dob` tool call to n8n (unnecessary complexity — the LLM already has the data); server-side DOB comparison in n8n (would require a new workflow and tool definition for minimal benefit).

### [2026-03-18] FAQ RAG with Supabase pgvector + VAPI Custom Knowledge Base
**Status:** accepted
**Context:** 4 FAQ Q&A pairs were hardcoded in Section 4 of the system prompt, wasting LLM context and not scalable.
**Decision:** Use Supabase's built-in RAG stack — pgvector + Edge Functions with `gte-small` embedding model (384 dims) — to store and retrieve FAQ entries. VAPI's Custom Knowledge Base feature auto-queries the Edge Function.
**Why:** Zero external embedding API costs (gte-small runs natively in Supabase Edge Functions), fewer moving parts than routing through n8n + OpenAI. Scales to hundreds of FAQs without touching the system prompt.
**Alternatives considered:** OpenAI embeddings via n8n workflow (API costs, more hops); hardcoded FAQ expansion (context waste); Pinecone/Weaviate (over-engineered for FAQ scale).

### [2026-03-18] VAPI Knowledge Base as separate resource (not top-level assistant field)
**Status:** accepted
**Context:** Initial attempt placed `knowledgeBase` config at the assistant's top level — VAPI API rejected it with "property knowledgeBase should not exist".
**Decision:** Create KB as a separate resource via `POST /knowledge-base`, then reference via `model.knowledgeBaseId` in the assistant config.
**Why:** VAPI API requirement — knowledge bases are standalone resources with their own IDs. The `server.secret` field on the KB resource handles auth (sends `x-vapi-signature` HMAC to the endpoint).
**Alternatives considered:** None; this is an API constraint discovered during deployment.

### [2026-03-17] JS-based phone normalization in n8n Code nodes
**Status:** accepted
**Context:** With FastAPI out of the DB path, phone normalization for customer lookups can no longer use the Python `phonenumbers` library in-line. Need an alternative in n8n.
**Decision:** Normalize US phone numbers to E.164 in n8n Code nodes using basic JS (strip non-digits, prepend +1 for 10-digit numbers).
**Why:** Sufficient for US numbers (the only region this demo handles). Avoids re-introducing FastAPI into the data path just for normalization. The FastAPI `/normalize-phone` endpoint still exists for other use cases.
**Alternatives considered:** Calling FastAPI `/normalize-phone` from n8n (adds latency and re-introduces the FastAPI dependency).

### [2026-03-18] Add `callerName` to VAPI structuredDataPlan schema
**Status:** accepted
**Context:** The EOC workflow extracts `callerName` from `message.analysis.structuredData.callerName`, but the field was never declared in the `structuredDataPlan` schema. VAPI only extracts fields defined in the schema, so `callerName` was always `undefined` → `"Unknown"` in the interactions table.
**Decision:** Add `callerName` (string) to `analysisPlan.structuredDataPlan.schema.properties` in `vapi/assistant_config.json`.
**Why:** One-line fix that closes the gap between the schema and the extraction logic. The EOC workflow's fallback (`|| 'Unknown'`) already handles the empty case correctly.
**Alternatives considered:** None — the field was simply missing from the schema.
