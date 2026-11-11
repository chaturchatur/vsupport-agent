# Decision Log

> Last verified: 2026-11-11 (pre-call / post-call workflows)

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

### [2025-XX-XX] n8n Cloud as primary integration layer (not a custom backend)
**Status:** accepted
**Context:** Needed to connect VAPI tool calls to Airtable for caller lookup and interaction logging.
**Decision:** Use n8n Cloud for all webhook handling and DB CRUD. No custom backend needed.
**Why:** n8n provides visual workflow editing, built-in Supabase nodes, and webhook handling with zero boilerplate. Eliminates the need for a separate backend server.
**Alternatives considered:** Building all integrations in a custom backend; using Zapier instead of n8n.

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

### [2026-03-17] n8n Postgres node → Supabase (not a custom backend as DB intermediary)
**Status:** superseded
**Context:** Initial Supabase migration considered routing n8n → custom backend (HTTP Request) → Supabase. This would require deploying a backend server reachable from n8n Cloud, meaning two separate cloud services to manage.
**Decision:** Use n8n's built-in Postgres node to connect directly to Supabase.
**Why:** Single-cloud deployment (n8n Cloud) with Supabase as managed database. Simpler operational overhead.
**Alternatives considered:** Custom backend as DB intermediary (more testable Python code, but requires managing a second cloud deployment).
**Supersedes:** Initial Supabase migration approach.
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
**Context:** Phone normalization for customer lookups needed an in-workflow solution.
**Decision:** Normalize US phone numbers to E.164 in n8n Code nodes using basic JS (strip non-digits, prepend +1 for 10-digit numbers).
**Why:** Sufficient for US numbers (the only region this demo handles). No external dependency needed.
**Alternatives considered:** Python-based normalization via a separate service (adds latency and operational overhead).

### [2026-03-18] Add `callerName` to VAPI structuredDataPlan schema
**Status:** accepted
**Context:** The EOC workflow extracts `callerName` from `message.analysis.structuredData.callerName`, but the field was never declared in the `structuredDataPlan` schema. VAPI only extracts fields defined in the schema, so `callerName` was always `undefined` → `"Unknown"` in the interactions table.
**Decision:** Add `callerName` (string) to `analysisPlan.structuredDataPlan.schema.properties` in `vapi/assistant_config.json`.
**Why:** One-line fix that closes the gap between the schema and the extraction logic. The EOC workflow's fallback (`|| 'Unknown'`) already handles the empty case correctly.
**Alternatives considered:** None — the field was simply missing from the schema.

### [2026-11-11] Outcome columns are merged onto the interaction row (insert, then update)
**Status:** accepted (unit-tested; not yet run on n8n Cloud)
**Context:** Call outcomes (resolved without a human, escalation, follow-up) come only from the end-of-call report. But on the happy path `log_interaction` has already written the row, so the report's `create` is rejected by the UNIQUE constraint and its data is thrown away. Storing outcomes only through that insert would have recorded them only for calls where the LLM failed to log, which is the wrong sample for a containment rate.
**Decision:** Keep the existing insert-with-swallowed-conflict, then always run a Supabase `update` filtered on `vapi_call_id` that writes only the outcome columns. Summary, sentiment and caller name written by the LLM are left alone.
**Why:** Stays on the Supabase node (no upsert operation exists on it), keeps the UNIQUE-constraint dedup untouched, and the update is idempotent.
**Alternatives considered:** PostgREST upsert (`Prefer: resolution=merge-duplicates`) through an HTTP Request node (one call instead of two, but would overwrite the LLM's summary unless the column list is managed by hand); having `log_interaction` write outcomes (the LLM does not know the outcome until the call is over).

### [2026-11-11] Missing outcome values are stored as NULL, and containment is divided by scored calls
**Status:** accepted
**Context:** VAPI omits structured-data fields when analysis fails or the call is too short. Legacy rows have no outcome data at all.
**Decision:** Every outcome column is nullable and a missing boolean is stored as NULL, never FALSE. `v_call_outcomes_daily.containment_rate` is `contained_calls / scored_calls`, where a scored call has a non-NULL `resolved_without_human`.
**Why:** Defaulting to FALSE would silently count every unanalysed call as "not contained".
**Alternatives considered:** Dividing by all calls (simpler, but the rate would drop whenever analysis fails).

### [2026-11-11] Post-call routing is computed in one Code node; the Switch only reads booleans
**Status:** accepted
**Context:** The Switch after the upsert has three conditions with shared inputs (stored row vs. parsed report, configuration present or not).
**Decision:** A `Decide Actions` Code node outputs `do_escalation`, `do_sms`, `do_callback`, `send_alert`. The Switch has one boolean rule per output and `allMatchingOutputs` on.
**Why:** Code nodes can be executed by the test suite; Switch expressions cannot. One call can legitimately need an escalation and a callback.
**Alternatives considered:** Putting the conditions in Switch expressions (untestable outside n8n).

### [2026-11-11] End-of-call webhook answers on receipt
**Status:** accepted
**Context:** The workflow now sends email and SMS and makes several database writes. With `responseMode: lastNode` any of them could delay or fail the HTTP response.
**Decision:** `responseMode: onReceived`, and `onError: continueRegularOutput` on every node after the data is stored.
**Why:** VAPI does not use the response body of an end-of-call report. Answering first makes it structurally impossible for a branch to affect the response.
**Alternatives considered:** Respond to Webhook node placed after the upsert (works, but more moving parts for no benefit).

### [2026-11-11] Deploy-time placeholders for environment-specific workflow values
**Status:** accepted
**Context:** The alert recipient, sender address, Twilio sender number, optional credential ids, the assistant id and the Supabase URL must not be hard-coded in a public repo. n8n custom variables (`$vars`) need Cloud Pro or Enterprise.
**Decision:** Workflow exports contain `__NAME__` placeholders; `scripts/deploy-n8n.sh` resolves them from `.env` through `scripts/resolve_n8n_placeholders.py`. Optional values resolve to empty and the workflow skips that action; required ones fail the deploy.
**Why:** Same idea as the `{{PLACEHOLDER}}` substitution `deploy-vapi.sh` already does, works on any n8n plan, and is testable offline.
**Alternatives considered:** `$vars` (plan-gated); `$env` (not confirmed to be readable on n8n Cloud); a config table in Supabase (an extra read on every call).

### [2026-11-11] SMS goes only to the number on the customers row, with status read from the database
**Status:** accepted (Twilio delivery not tested)
**Context:** After a resolved, authenticated call the caller gets a text confirming claim status.
**Decision:** Look the customer up by the (strictly validated) claim number, require exactly one row with a matching claim number and a valid E.164 number, send to that row's `phone_number`, and take the status text from that row. Skip silently if Twilio is not configured.
**Why:** The caller ID and anything said on the call are unverified. The LLM's idea of the status may be wrong; the database is the source of truth.
**Alternatives considered:** Texting the caller ID (could send claim details to a borrowed phone).

### [2026-11-11] Alert email carries the call id only
**Status:** accepted
**Context:** Escalations and negative calls alert a human by email.
**Decision:** The email contains the trigger and the VAPI call id. No name, number, claim or summary.
**Why:** The assistant runs with `hipaaEnabled`; email is the least protected hop. The human looks the call up in `follow_ups` / `interactions`.
**Alternatives considered:** Including the summary (more convenient, leaks caller details into mailboxes).

### [2026-11-11] Pre-call recognition uses a separate webhook on the phone number, not /webhook/vapi-server
**Status:** accepted (from VAPI documentation; not yet verified on a live call)
**Context:** The plan was to add `assistant-request` to the assistant's `serverMessages` and possibly route on `message.type` in the existing server-URL workflow.
**Decision:** New workflow `pre-call-context` at `/webhook/pre-call-context`, set as the **phone number's** server URL with the assistant un-assigned from the number (`scripts/configure-vapi-phone.sh`). `serverMessages` is unchanged.
**Why:** VAPI sends `assistant-request` only when the phone number has no assistant, i.e. before any assistant (and its server URL) is selected. `assistant-request` is not in the `serverMessages` enum.
**Trade-off:** Inbound calls now depend on this webhook answering within a fixed 7.5 s; VAPI documents no fallback. Mitigations: 2.5 s timeouts on both lookups, every failure falls through to the default assistant, one-command rollback.
**Alternatives considered:** Extending `/webhook/vapi-server` (cannot receive the event); keeping the assistant on the number and having the agent call `lookup_caller` silently at the start of the call (no call-setup dependency, but the greeting is spoken before the lookup returns, so no first-name greeting).

### [2026-11-11] pre-call-context reads Supabase through HTTP Request nodes with a timeout
**Status:** accepted
**Context:** The 2026-03-18 decision standardised on the Supabase node. That node has no per-request timeout, and here a hung request means a failed phone call.
**Decision:** The two reads in `pre-call-context` use HTTP Request nodes (`supabaseApi` predefined credential, `timeout: 2500`, `onError: continueRegularOutput`). All other workflows stay on the Supabase node.
**Why:** A hard cap per lookup is the only way to guarantee a default response inside VAPI's budget. The `+`-encoding issue that motivated the Supabase-node standard does not arise: only digits are filtered on.
**Alternatives considered:** Supabase node plus a workflow-level timeout (a timed-out execution returns nothing, so the call would fail).

### [2026-11-11] Known-caller greeting is sent as assistantOverrides.firstMessage
**Status:** accepted (not yet verified on a live call)
**Context:** A recognised caller should hear their first name and be asked only for date of birth; an unknown caller should hear today's greeting unchanged.
**Decision:** The assistant's own `firstMessage` stays as it was. `pre-call-context` adds `assistantOverrides.firstMessage` only for recognised callers. Variables are sent as strings.
**Why:** VAPI documents `{{variable}}` substitution but not conditionals inside `firstMessage`. This way the unknown-caller path and the rollback path (assistant assigned directly to the number) use exactly the old greeting with no template logic.
**Alternatives considered:** `{% if %}` in `firstMessage` (undocumented); a `{{greeting}}` variable (renders empty if the variable is ever missing).

### [2026-11-11] Caller ID is context, not authentication
**Status:** accepted
**Context:** Recognising the caller by number makes the claim number, status and last-call summary available to the prompt before the caller has proved anything.
**Decision:** The stored date of birth is never fetched by `pre-call-context`; the agent still gets it via `lookup_caller` and verifies it. The prompt allows only the first name to be spoken before verification passes. A negative previous call is acted on after verification, or pre-verification only as a generic offer of a human with no reference to the earlier call.
**Why:** Phone numbers are shared, borrowed and spoofable.
**Alternatives considered:** Not passing claim data pre-verification at all (safer still; the variables were kept because they were requested and the agent re-fetches the record anyway. Worth revisiting if the prompt guard proves leaky in testing).

### [2026-11-11] Add `sentiment` to structuredDataPlan
**Status:** accepted
**Context:** The EOC workflow has always read `structuredData.sentiment`, but the field was never declared, so the report-side sentiment was always `neutral` (same class of bug as the earlier `callerName` fix). The new negative-sentiment branch would never fire for calls the LLM did not log.
**Decision:** Declare `sentiment` (enum) in the schema alongside the four new outcome fields. Existing field names are unchanged.
**Alternatives considered:** Leaving it (the escalation branch would silently miss dropped, angry calls).
