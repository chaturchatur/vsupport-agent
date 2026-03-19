# Interview Briefing: VoiceAI Insurance Claims Support Agent

## Complete System Walkthrough for Engineering Team Presentation

---

## 1. What We Built (The Big Picture)

**Vsupport-agent** is a fully autonomous voice AI agent that handles inbound insurance claims support calls for "Observe Insurance." A customer calls in, speaks naturally, and the AI agent:

1. Greets them as "Sarah"
2. Authenticates their identity (phone → name confirmation → DOB verification)
3. Looks up their claim status in the database
4. Answers FAQ questions using semantic search (RAG)
5. Logs the interaction and sentiment
6. Gracefully ends the call

**Zero human intervention** for standard calls. Escalates to humans only when it can't verify identity or the caller explicitly requests it.

---

## 2. Architecture & How Everything Links Together

### The 5-Layer Stack

```
Layer 1: TELEPHONY + VOICE (VAPI)
  ├── Deepgram Nova-2 (STT — speech-to-text)
  ├── GPT-4o (LLM — reasoning + conversation)
  ├── ElevenLabs "Sarah" (TTS — text-to-speech)
  └── VAPI orchestrates the full loop: audio in → text → LLM → text → audio out

Layer 2: WORKFLOW ENGINE (n8n Cloud)
  ├── 3 webhook-triggered workflows
  ├── Receives tool calls from VAPI via HTTPS
  ├── All database reads/writes happen here
  └── Auth: x-vapi-secret header validation

Layer 3: DATABASE (Supabase PostgreSQL)
  ├── customers table (read-only for agent)
  ├── interactions table (write — call logs)
  ├── faqs table (pgvector embeddings for RAG)
  └── Edge Functions for FAQ embedding + search

Layer 4: FAQ RAG (Supabase pgvector + Edge Functions)
  ├── 18 FAQ entries with gte-small embeddings (384 dims)
  ├── Semantic similarity search via pgvector
  └── VAPI Custom Knowledge Base integration
```

### Data Flow — A Complete Call

```
1. Customer dials in
2. VAPI picks up → plays firstMessage ("Thank you for calling Observe Insurance...")
3. Customer says their phone number
4. Deepgram transcribes speech → GPT-4o extracts digits
5. GPT-4o triggers lookup_caller tool call →
   → VAPI sends POST to n8n webhook (with x-vapi-secret header)
   → n8n parses VAPI envelope, normalizes phone (JS), builds PostgREST filter
   → n8n queries Supabase customers table via REST API (phone_digits column)
   → n8n formats response → returns to VAPI
6. GPT-4o confirms name → asks for DOB → compares LLM-side (no extra API call)
7. GPT-4o reads claim status from lookup result → speaks it to caller
8. If caller asks FAQ → VAPI auto-queries Knowledge Base →
   → Supabase Edge Function (search-faq) embeds query → pgvector search → returns top 3
9. Caller ready to hang up → GPT-4o triggers log_interaction tool call →
   → n8n inserts into interactions table
10. VAPI fires end-of-call-report webhook →
    → n8n inserts into interactions (dedup via UNIQUE constraint on vapi_call_id)
11. Call ends
```

---

## 3. The Three n8n Workflows (In Detail)

### Workflow 1: Lookup Caller (5 nodes)
**Webhook → Parse Envelope → Query Customers → Format Result → Respond**

- Parses VAPI's tool-call envelope to extract `toolCallId` + arguments
- JS Code node normalizes US phone to E.164 (strip non-digits, prepend +1)
- Builds PostgREST OR filter: `or=(phone_digits.eq.14155551234,last_name.ilike.johnson)`
- Queries `phone_digits` generated column (not `phone_number`) to avoid `+` encoding bug
- Returns single match (with DOB), multi-match list, or "not found"

### Workflow 2: Log Interaction (7 nodes)
**Webhook → Parse Envelope → Insert → Format Success/Error → Respond**

- Strips non-DB fields before Supabase insert (uses `autoMapInputData`)
- Error branch handles insert failures gracefully
- Gets `toolCallId` from original webhook body (not from parsed data)

### Workflow 3: End-of-Call Report (5 nodes)
**Webhook → Parse EOC → Is EOC? (IF) → Strip Meta → Upsert**

- Filters for `end-of-call-report` message type only
- Uses Supabase create with `onError: continueRegularOutput`
- UNIQUE constraint on `vapi_call_id` silently rejects duplicates
- Replaced the old 10-second wait + search hack from Airtable days

---

## 4. Key Architectural Decisions & Why

### Decision 1: n8n Cloud as primary integration layer (not a custom backend)
**Why:** Visual workflow editing, built-in Supabase nodes, zero boilerplate for webhooks. No backend server to deploy or maintain.

### Decision 2: Airtable → Supabase migration
**Why:** Airtable had 5 req/sec rate limit, no indexing, no unique constraints, 50k record cap. The end-of-call dedup was a hacky 10-second sleep + search. Supabase gives us proper indexes, `UNIQUE` constraints, `INSERT ON CONFLICT DO NOTHING` for atomic dedup.

### Decision 3: Supabase REST API (not Postgres wire protocol)
**Why:** n8n Cloud has IPv6 routing issues — can't reach Supabase Postgres on port 5432 or the pooler on 6543 (`ENETUNREACH`). REST API over HTTPS (port 443) works immediately.

### Decision 4: `phone_digits` generated column
**Why:** The Supabase node applies `encodeURI()` to filter strings. `+` in E.164 numbers gets preserved (interpreted as space by PostgREST → 0 results). `phone_digits` strips the `+` at the DB level so the filter value is pure digits. Problem solved at the right layer.

### Decision 5: DOB verification as LLM-side comparison
**Why:** No new tool call or workflow needed. `lookup_caller` already returns the full customer record including DOB. The LLM compares spoken DOB against stored value. Flexible date matching ("March 15th 1985" vs "1985-03-15") is something LLMs excel at.

### Decision 6: FAQ RAG with Supabase pgvector (not OpenAI embeddings)
**Why:** Zero external embedding API costs — `gte-small` runs natively in Supabase Edge Functions. Scales to hundreds of FAQs without touching the system prompt. VAPI's Custom Knowledge Base auto-queries the Edge Function.

### Decision 7: HIPAA enabled
**Why:** Insurance = protected health information. `hipaaEnabled: true` activates BAA-eligible mode in VAPI (no call recording/logging by VAPI).

---

## 5. Security & Compliance (Deep Dive)

### Authentication Layers

| Layer | Mechanism | What It Protects |
|-------|-----------|-----------------|
| **Caller → Agent** | Phone number + name confirmation + DOB verification (2 attempts) | Prevents unauthorized access to claim information |
| **VAPI → n8n** | `x-vapi-secret` header validated by n8n Header Auth credential | Prevents unauthorized webhook calls to n8n |
| **VAPI → Edge Function** | HMAC SHA256 signature (`x-vapi-signature`) verified in `search-faq` | Prevents unauthorized FAQ queries |
| **n8n → Supabase** | Service Role Key (server-side only, stored in n8n credential) | Database access control |
| **Deploy pipeline** | `.env` secrets + placeholder resolution in `deploy-vapi.sh`, resolved config is `.gitignored` | No secrets in version control |

### HIPAA Compliance Details

VAPI's `hipaaEnabled: true` activates **BAA-eligible mode**:
- **No call recording** — VAPI does not store audio
- **No transcript logging** — conversation text is not persisted by VAPI
- **No PII in VAPI analytics** — structured data from `analysisPlan` is the only thing VAPI retains
- **Our responsibility**: Supabase stores `caller_name`, `phone_number`, `summary` in the interactions table. In production, we'd need:
  - Supabase HIPAA add-on (available on Team/Enterprise plans)
  - Encryption at rest (Supabase uses AES-256 by default on all plans)
  - Row-level security policies (currently using service role key — RLS bypassed)
  - Audit logging for who accessed what records
  - Data retention policy (auto-delete interactions after X days)

### Data Flow Security Audit

```
Caller speaks → Deepgram (encrypted audio stream) → text
Text → GPT-4o (OpenAI, HIPAA-eligible with BAA) → response
Tool call → HTTPS + x-vapi-secret → n8n Cloud (EU/US datacenter)
n8n → HTTPS + service role key → Supabase PostgREST (TLS 1.3)
Edge Function → runs in Supabase's Deno runtime (isolated, no external calls except DB)
```

Every hop is HTTPS. No plaintext. No data at rest outside Supabase (which encrypts by default).

### What's NOT Covered Yet (Production Gaps)
1. **No rate limiting** on n8n webhooks (could be DDoS'd)
2. **No IP allowlisting** — n8n webhooks are publicly reachable
3. **No audit trail** — no logging of who looked up which customer record
4. **Service role key bypasses RLS** — fine for a voice agent, but not for multi-tenant
5. **DOB verification is LLM-side** — a jailbreak prompt could theoretically bypass it (mitigated by VAPI's controlled environment, but not impossible)

---

## 6. Cost Per Call Estimate (Deep Dive)

### Assumptions
- **Average call duration:** 3 minutes (~30 conversational turns)
- **Average tokens per call:** ~2,000 input tokens (system prompt + conversation history + tool results), ~800 output tokens (agent responses + tool calls)
- **Average TTS characters:** ~1,200 characters (agent speaks ~200 chars/response x 6 responses)
- **Tool calls per call:** 2-3 (1 lookup + 1 log + optional FAQ search)

### Per-Call Breakdown

| Component | Pricing Model | Calculation | Est. Cost/Call |
|-----------|--------------|-------------|----------------|
| **VAPI platform** | $0.05/min | 3 min x $0.05 | **$0.150** |
| **Deepgram STT** (Nova-2) | $0.0043/min (included in VAPI) | 3 min x $0.0043 | **$0.013** |
| **GPT-4o** (LLM) | $2.50/1M input, $10/1M output | 2K in x $2.50/1M + 800 out x $10/1M | **$0.013** |
| **ElevenLabs TTS** | ~$0.30/1K chars (via VAPI) | 1.2K chars x $0.30/1K | **$0.036** |
| **Supabase Edge Functions** | Free: 500K/mo, then $2/1M | 1 invocation | **~$0.000** |
| **Supabase DB** | Free: 500MB, Pro: $25/mo | Negligible per query | **~$0.000** |
| **n8n Cloud** | $24/mo Starter (2,500 execs) | 3 execs/call | **$0.029** |
| | | | |
| **Total per call** | | | **~$0.24** |

### Monthly Fixed Costs

| Service | Plan | Monthly Cost |
|---------|------|-------------|
| VAPI | Pay-as-you-go | $0 base (usage only) |
| n8n Cloud | Starter | $24/mo |
| Supabase | Free tier | $0/mo |
| **Total fixed** | | **$24/mo** |

### Volume Scaling — Cost at Different Call Volumes

| Monthly Calls | Per-Call Cost | Fixed Cost | Total Monthly | Cost/Call (blended) |
|--------------|-------------|------------|--------------|-------------------|
| **100** | $24 | $24 | **$48** | $0.48 |
| **500** | $120 | $24 | **$144** | $0.29 |
| **1,000** | $240 | $24 | **$264** | $0.26 |
| **5,000** | $1,200 | $49* | **$1,249** | $0.25 |
| **10,000** | $2,400 | $99** | **$2,499** | $0.25 |

*n8n Pro ($49/mo) needed at ~833+ calls/mo (2,500 exec limit / 3 execs/call)
**Supabase Pro ($25/mo) + n8n Pro ($49/mo) + VAPI phone number ($1.50/mo)

### Break-Even vs Human Agents

| Metric | AI Agent | Human Agent |
|--------|----------|-------------|
| Cost per call | ~$0.25 | ~$2.00 (fully loaded: $15/hr, 7.5 calls/hr AHT) |
| Available hours | 24/7/365 | 8hrs/day, 5 days/week |
| Ramp-up time | Instant | 2-4 weeks training |
| Consistency | 100% script adherence | Variable |
| Concurrent calls | 10+ (VAPI plan dependent) | 1 per agent |
| **Break-even** | **Immediate — AI is cheaper from call #1** | |

### Cost Reduction Levers
1. **GPT-4o-mini swap**: ~60% cheaper LLM costs ($0.15/1M input, $0.60/1M output) — saves ~$0.01/call
2. **Deepgram Nova-2 → Whisper**: Potentially cheaper STT, but higher latency
3. **ElevenLabs → PlayHT/LMNT**: Lower per-character TTS costs
4. **VAPI → self-hosted Pipecat/LiveKit**: Eliminates VAPI's $0.05/min platform fee (biggest single cost). Requires more engineering effort but saves 60% of per-call cost at scale
5. **n8n self-hosted**: $0/mo instead of $24-49/mo, but you manage the infra

---

## 7. Scalability Analysis (Deep Dive)

### Current Limits — Where Each Component Breaks

| Component | Hard Limit | Practical Ceiling | What Happens When Hit |
|-----------|-----------|-------------------|----------------------|
| **VAPI** (pay-as-you-go) | ~10 concurrent calls | ~200 calls/hr | Callers get busy signal or queue |
| **n8n Cloud Starter** | 2,500 executions/mo | ~833 calls/mo (3 execs/call) | Workflows stop executing until next billing cycle |
| **Supabase Free** | 500MB DB, 500K Edge Function calls, 2 Edge Functions | ~150K FAQ queries/mo | Edge Functions return 500s; DB still works |
| **GPT-4o** (via VAPI) | Tier-dependent: 10K RPM, 2M TPM at Tier 3 | ~300+ concurrent calls before token rate limits | VAPI queues or retries; caller hears silence/delay |
| **PostgREST** | Supabase manages pool (Free: ~20 connections) | ~100 concurrent queries | 503 errors on n8n side → tool call fails → graceful error message to caller |
| **Deepgram** | 100 concurrent streams (default) | Effectively unlimited for this use case | STT fails → VAPI falls back or errors |

### Latency Budget — Where Time Goes in a Tool Call

```
Caller speaks                        0ms
Deepgram STT transcription      150-300ms
GPT-4o decides to call tool      200-500ms  (first token)
VAPI sends webhook to n8n          50-100ms  (HTTPS)
n8n processes workflow             100-200ms  (parse + normalize + build filter)
Supabase PostgREST query           20-50ms   (indexed lookup)
n8n formats response                10-20ms
VAPI receives tool result           50-100ms
GPT-4o generates spoken response  300-800ms  (depends on token count)
ElevenLabs TTS synthesis          200-400ms
Audio plays to caller                 0ms
─────────────────────────────────────────────
Total perceived delay:          1.1-2.5 seconds per turn
```

**Critical insight:** The LLM (GPT-4o) and TTS (ElevenLabs) dominate latency, NOT the database or workflows. Optimizing n8n or Supabase queries saves 10-50ms — irrelevant compared to 500-1200ms from LLM+TTS.

### Scaling Path — Phase by Phase

**Phase A: 0 → 1,000 calls/month (Current architecture, no changes)**
- Everything works on current free/starter tiers
- Total cost: ~$264/mo
- Only action: provision a real phone number

**Phase B: 1,000 → 5,000 calls/month**
- Upgrade n8n to Pro ($49/mo) — unlimited executions
- Upgrade Supabase to Pro ($25/mo) — 8GB storage, dedicated compute, more Edge Function invocations
- Add connection pooler (Supabase has built-in PgBouncer)
- Consider GPT-4o-mini for cost reduction
- Total cost: ~$1,250-1,350/mo

**Phase C: 5,000 → 25,000 calls/month**
- VAPI Growth plan for higher concurrency
- Add **Redis cache** in front of Supabase for customer lookups (phone→customer mapping, 5-min TTL). Most callers call about the same claim — cache hit rate should be 30-50%
- Move from n8n Cloud to **self-hosted n8n** on AWS ECS/Fargate for unlimited concurrency + lower cost
- Add monitoring: Datadog/Grafana for latency percentiles, error rates, cache hit rates
- Total cost: ~$4,000-5,000/mo

**Phase D: 25,000+ calls/month (Enterprise)**
- Replace n8n with **AWS Lambda** functions (event-driven, auto-scaling, zero cold-start with provisioned concurrency)
- Replace VAPI with **self-hosted Pipecat/LiveKit** — eliminate $0.05/min platform fee (saves ~$3,750/mo at 25K calls)
- Supabase → **AWS RDS PostgreSQL** with read replicas for high-read customer lookups
- Multi-region deployment for latency (US-East + US-West)
- Total cost: ~$3,000-4,000/mo (lower than Phase C due to eliminating VAPI platform fee)

### What Does NOT Need to Change at Any Scale
- **Database schema** — already indexed, constrained, optimized. Postgres handles millions of rows easily
- **System prompt** — conversation logic is scale-independent
- **Edge Functions** — stateless, auto-scale on Supabase (or port to Lambda trivially)
- **VAPI config** — model-agnostic; swap GPT-4o → GPT-4o-mini → Claude Sonnet as needed
- **FAQ RAG pipeline** — pgvector scales to 100K+ vectors without architecture changes

### Horizontal vs Vertical Scaling

| Concern | Scaling Strategy |
|---------|-----------------|
| More concurrent calls | VAPI plan upgrade (vertical) → self-hosted Pipecat (horizontal) |
| More DB queries | Supabase Pro + read replicas (vertical) → RDS multi-AZ (horizontal) |
| More webhook throughput | n8n Pro (vertical) → self-hosted n8n cluster or Lambda (horizontal) |
| More FAQ entries | pgvector handles 100K+ vectors; add HNSW index at ~10K entries |
| More customers | Partition customers table by region at ~1M rows (overkill until then) |

---

## 8. How We Can Make It Better

### Immediate Wins (1-2 days)
1. **Provision a real phone number** (~$1.50/mo) — currently testing via VAPI Dashboard only
2. **Configure DB webhook** for auto-embedding new FAQs on insert
3. **Add more FAQ entries** — just insert rows, embeddings auto-generate
4. **GPT-4o-mini swap** — for cost reduction (~60% cheaper) with minimal quality loss on this structured task

### Medium-Term (1-2 weeks)
5. **Analytics dashboard** — Query interactions table for sentiment trends, call volumes, escalation rates (containment rate KPI)
6. **Callback scheduling** — When escalating to human, actually create a callback task (n8n → CRM integration)
7. **Multi-language support** — Deepgram supports 30+ languages, swap TTS voice per language
8. **Call recording + transcription** (opt-in, non-HIPAA calls) for QA and training
9. **A/B test system prompts** — Different greeting styles, verification flows

### Longer-Term (1+ month)
10. **Fine-tuned model** — Train on actual call transcripts for insurance-specific language
11. **Outbound calls** — Proactive claim status updates ("Your claim has been approved!")
12. **Multi-tenant** — Separate configs per insurance brand, shared infrastructure
13. **Real-time monitoring** — Grafana dashboard for latency, error rates, sentiment distribution
14. **Voiceprint authentication** — Replace DOB verification with voice biometrics

---

## 9. Testing & Quality

- **10 automated tests** (pytest): VAPI envelope parsing (10)
- **Demo scripts**: Happy path (approved claim), error paths (identity denial, re-verification, requires_documentation)
- **Conversation state machine**: 17 states, color-coded diagram (green=happy, red=error, yellow=re-verification, purple=FAQ)
- **Excalidraw diagrams**: Architecture diagram + conversation flow diagram (in `diagrams/`)

---

## 10. Engineering Challenges — War Stories

### Challenge 1: The `+` Encoding Bug (3 iterations to solve)

**The symptom:** Phone lookups by E.164 number (`+17185557777`) returned 0 rows despite the data existing in Supabase.

**Debugging journey:**
1. Confirmed data existed via Supabase dashboard — row was there
2. Tested the PostgREST query directly in browser — worked fine
3. Realized the n8n Supabase node was the culprit

**Root cause:** The n8n Supabase node applies `encodeURI()` to the `filterString` parameter before sending it to PostgREST. `encodeURI()` does NOT encode `+` (it's a "safe" character in URI spec). But PostgREST interprets `+` as a space in query parameters (per `application/x-www-form-urlencoded` rules). So `phone_number.eq.+17185557777` becomes `phone_number.eq. 17185557777` → no match.

**Attempt 1 — Pre-encode `+` as `%2B`:** Failed. `encodeURI()` then double-encodes the `%` to `%25`, producing `%252B` → still no match.

**Attempt 2 — HTTP Request node:** Replaced the Supabase node with a raw HTTP Request node that doesn't apply `encodeURI()`. Built the full URL manually with `encodeURIComponent()` in a Code node. **This worked** — but now Lookup Caller used a different node type than every other workflow. Inconsistent, harder to maintain.

**Attempt 3 (final) — `phone_digits` generated column:** Added a Postgres generated column: `phone_digits TEXT GENERATED ALWAYS AS (replace(phone_number, '+', '')) STORED`. Lookup Caller now filters on `phone_digits.eq.17185557777` — pure digits, no `+`, nothing for `encodeURI()` to break. **Problem solved at the database layer**, all workflows use the same Supabase node type.

**Lesson:** When a middleware has an encoding bug you can't fix, change the data shape so the problematic character never enters the pipeline.

---

### Challenge 2: End-of-Call Dedup (Race Condition)

**The problem:** Every call was getting logged TWICE in the interactions table.

**Why it happened:** VAPI has two logging mechanisms that fire independently:
1. `log_interaction` — a tool call triggered by the LLM at wrap-up (GPT-4o decides to call it)
2. `end-of-call-report` — a lifecycle webhook VAPI sends automatically when the call ends

Both arrive at n8n within seconds of each other, both try to insert into the interactions table.

**Airtable era solution (hacky):**
```
end-of-call-report arrives → Wait 10 seconds → Search Airtable for vapi_call_id →
If found: skip (log_interaction already wrote it)
If not found: create record
```
Problems: 10-second delay is arbitrary (what if log_interaction takes 15s?), Airtable search isn't indexed (O(n) scan), race condition still possible if both arrive within the 10s window.

**Supabase solution (correct):**
```sql
-- interactions table
vapi_call_id TEXT UNIQUE
```
```
-- n8n End-of-Call Report workflow
Supabase create with onError: continueRegularOutput
```
The `UNIQUE` constraint + `continueRegularOutput` is equivalent to `INSERT ON CONFLICT DO NOTHING`. If `log_interaction` already wrote a row with that `vapi_call_id`, the end-of-call insert silently fails. If `log_interaction` never fired (e.g., caller hung up abruptly), the end-of-call report creates the record as a fallback.

**Atomic, zero-latency, zero race conditions.** This single improvement justified the Airtable → Supabase migration.

---

### Challenge 3: n8n Cloud → Supabase Postgres Connection Failure

**The symptom:** n8n's Postgres node returned `ENETUNREACH` when connecting to Supabase.

**Debugging journey:**
1. Tested direct host `db.<ref>.supabase.co:5432` — `ENETUNREACH`
2. Tried the connection pooler `aws-0-us-east-1.pooler.supabase.com:6543` — same error
3. Both resolved to IPv6 addresses. n8n Cloud's infrastructure couldn't route to IPv6.

**Considered solutions:**
- **Supabase IPv4 add-on** (~$4/mo) — adds a dedicated IPv4 address. Would work but adds cost for something that should be free.
- **Custom backend as DB intermediary** — n8n → backend (HTTP) → Supabase. Works but requires deploying a separate server, adding a second service to manage.
- **Supabase REST API** — n8n's built-in Supabase node connects via PostgREST (HTTPS, port 443). HTTPS resolves and routes correctly regardless of IPv4/IPv6.

**Chosen solution:** Supabase node via REST API. Zero additional cost, zero additional infra. Trade-off: no raw SQL (PostgREST filters only), but for our simple CRUD operations this is actually a benefit (no SQL injection surface).

---

### Challenge 4: n8n Supabase Node `defineInNode` Schema Cache Bug

**The symptom:** Supabase inserts created rows with all NULLs/defaults instead of the actual data.

**Root cause:** The Supabase node v1 has a `defineInNode` mode where you map fields via a UI (`fieldsUi`). This mode caches the table schema and has a bug: `"Could not find the '' column"`. The node silently falls back to inserting empty values.

**Solution:** Use `dataToSend: "autoMapInputData"` instead. This mode takes the entire input JSON object and maps keys directly to column names. **Requirement:** Code nodes upstream must output ONLY keys that match actual DB columns — strip metadata like `toolCallId`, `is_eoc`, etc. before the data reaches the Supabase node.

---

### Challenge 5: VAPI API Quirks (Death by 1000 Undocumented Behaviors)

Multiple VAPI API behaviors that aren't in the docs (or contradict them):

1. **Tools must be in `model.tools[]`** — placing them at the assistant top level is silently ignored (no error, just doesn't work)
2. **`server.secret` doesn't work for tool calls** — despite docs mentioning it. Must use `server.headers["x-vapi-secret"]` instead. However, `server.secret` DOES work for Knowledge Base resources (sends HMAC)
3. **`knowledgeBase` is not an assistant field** — returns `400: property knowledgeBase should not exist`. Must create KB as separate resource via `POST /knowledge-base`, then reference via `model.knowledgeBaseId`
4. **`analysisPlan.summaryPlan.prompt` doesn't work** — the correct path is `analysisPlan.summaryPrompt` (flat string, not nested)
5. **VAPI CLI `create` and `update` are interactive-only** — no `--body` flag exists. Had to build `deploy-vapi.sh` using `curl` against the REST API directly

**Lesson:** Voice AI platforms are still immature. Budget extra time for API exploration and always verify behavior empirically, not from docs.

---

### Challenge 6: DOB Verification — Solving It Without Engineering

**The obvious approach:** Build a `verify_dob` tool call → n8n workflow → compare server-side → return match/no-match.

**Why we didn't:** The `lookup_caller` response already contains the full customer record including `date_of_birth`. The LLM sees it. Instead of a round-trip API call, we just instruct the LLM:

> "Compare the caller's spoken date of birth against the `date_of_birth` field. Be flexible — 'March 15th, 1985', '3/15/85', and 'March fifteenth nineteen eighty-five' should all match `1985-03-15`."

The LLM handles natural language date parsing better than any regex or `dateutil.parser` could. Zero latency (no API call), zero engineering effort (no new workflow), and more flexible than code.

**Trade-off:** A sophisticated prompt injection could theoretically make the LLM reveal the DOB or skip verification. Mitigated by VAPI's controlled audio environment (attacker would need to speak the injection aloud on a phone call), but worth noting for a production security review.

---

## 11. File Map (Key Files to Reference)

| File | Purpose |
|------|---------|
| `vapi/assistant_config.json` | Full VAPI assistant config (model, voice, tools, KB) |
| `vapi/system_prompt.md` | The conversation logic (8 sections) |
| `n8n/workflows/*.json` | 3 workflow definitions (lookup, log, EOC) |
| `supabase/migrations/001-005` | Database schema evolution |
| `supabase/functions/search-faq/` | FAQ RAG Edge Function |
| `supabase/functions/generate-embedding/` | Auto-embed FAQ rows |
| `app/config.py` | Pydantic Settings (env vars) |
| `scripts/deploy-vapi.sh` | Deployment script with placeholder resolution |
| `diagrams/*.excalidraw` | Architecture + conversation flow diagrams |
| `.agent/` | Living documentation (System, Decisions, Gotchas, Tasks) |

---

## 12. Talking Points for Q&A

**"Why not just build a custom backend?"**
→ n8n gives us visual debugging, built-in connectors, and zero-boilerplate webhook handling. A custom backend would mean writing and maintaining all the HTTP parsing, auth, DB queries, and error handling manually. n8n lets us iterate on workflows in minutes.

**"Why GPT-4o and not Claude?"**
→ VAPI natively supports both. GPT-4o was chosen for lower latency in real-time voice (critical for natural conversation). Could swap to Claude Sonnet for potentially better instruction following — the config is model-agnostic.

**"Why Supabase over AWS RDS?"**
→ Built-in pgvector (no extensions to manage), Edge Functions for serverless compute, PostgREST for instant API layer, free tier for prototyping. Production migration to RDS would be straightforward — it's just Postgres.

**"What about hallucination?"**
→ Temperature 0.3 (low creativity), max 500 tokens (concise responses), structured system prompt with explicit instructions for every scenario, FAQ RAG grounds answers in real data rather than LLM knowledge.

**"What if Supabase goes down?"**
→ Tool calls return errors → system prompt Section 8 kicks in: "I'm having trouble accessing our records, let me arrange a callback." Graceful degradation, never a hard crash.
