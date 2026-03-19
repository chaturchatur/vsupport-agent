# Technical Write-Up: VoiceAI Claims Support Agent

## A. Tools, Frameworks, and APIs

### Architecture Overview

The system is a 5-layer stack where each layer handles a single concern:

| Layer | Component | Role |
|-------|-----------|------|
| **Telephony + Voice** | VAPI | Orchestrates the full audio loop: caller speech in → STT → LLM → TTS → audio out |
| **Speech-to-Text** | Deepgram Nova-2 | Real-time transcription with 300ms endpointing |
| **LLM** | GPT-4o (temp 0.3, 500 max tokens) | Conversation reasoning, tool calling, DOB verification |
| **Text-to-Speech** | ElevenLabs "Sarah" | Natural-sounding female voice matching the persona |
| **Workflow Engine** | n8n Cloud | 3 webhook-triggered workflows for all database I/O |
| **Database** | Supabase PostgreSQL | Customers (read), Interactions (write), FAQs (pgvector RAG) |
| **Edge Functions** | Supabase Deno Runtime | FAQ embedding generation (gte-small) + semantic search |
| **Config** | Python + Pydantic Settings | Environment configuration |

### Why These Specific Tools

**VAPI over Retell/LiveKit/Pipecat:**
VAPI was chosen because it provides a fully managed telephony layer with native integrations to Deepgram, OpenAI, and ElevenLabs — eliminating the need to manage WebSocket audio streams, SIP trunking, or turn-taking logic ourselves. Its `assistant-speaks-first` mode, built-in `endCall` function, and `analysisPlan` for post-call structured data extraction meant we could focus on conversation logic rather than telephony plumbing. The trade-off is the $0.05/min platform fee, but for a prototype this buys significant development speed.

**Deepgram Nova-2 for STT:**
Nova-2 is optimized for real-time streaming with low word error rates on phone-quality audio. The 300ms endpointing setting balances responsiveness (caller doesn't wait too long for a response) against not cutting speakers off mid-utterance. Deepgram's built-in noise handling pairs well with VAPI's `backgroundDenoisingEnabled: true`.

**GPT-4o for LLM:**
GPT-4o provides the best latency-to-quality ratio for real-time voice. Temperature 0.3 keeps responses deterministic (critical for scripted insurance flows where hallucinating a claim status would be a compliance issue). Max tokens at 500 prevents the agent from monologuing — long responses are terrible UX in voice. Claude Sonnet would be a viable swap for potentially better instruction following; the config is model-agnostic.

**ElevenLabs for TTS:**
The pre-built "Sarah" voice is warm and professional without sounding robotic. ElevenLabs' streaming latency (200-400ms) keeps the total turn latency under 2.5 seconds, which is the threshold where callers start feeling the delay.

**n8n Cloud as the integration layer (not a custom backend):**
This was a deliberate architectural choice. n8n gives us visual workflow debugging, built-in Supabase/HTTP nodes, and webhook endpoints with zero boilerplate. Building the same 3 workflows in a custom backend would mean writing HTTP parsing, auth middleware, database queries, error branching, and response formatting manually — all of which n8n handles declaratively. The visual representation also makes the system auditable by non-engineers (product, compliance).

**Supabase over Airtable/Google Sheets:**
The original prototype used Airtable, but we migrated to Supabase to solve three critical problems:
1. **Rate limits** — Airtable caps at 5 req/sec; Supabase PostgreSQL handles thousands
2. **Atomic dedup** — `UNIQUE` constraint on `vapi_call_id` enables `INSERT ON CONFLICT DO NOTHING`, replacing a hacky 10-second wait + search approach in Airtable
3. **pgvector** — Built-in vector extension for FAQ semantic search, eliminating external embedding API costs

**Supabase Edge Functions + gte-small for FAQ RAG:**
Instead of calling OpenAI's embedding API, we use `Supabase.ai.Session("gte-small")` which runs the embedding model directly on Supabase infrastructure. Zero external API costs, zero additional latency (function and database are co-located), and the 384-dimensional vectors are small enough for fast similarity search. The `match_faqs` RPC uses pgvector's inner product operator (`<#>`) which is equivalent to cosine similarity for L2-normalized vectors but computationally faster.

### How It Scales for Production

**Current capacity:** ~833 calls/month on starter tiers ($24/mo fixed cost, ~$0.24/call variable).

**Scaling path:**

| Phase | Volume | Key Changes | Monthly Cost |
|-------|--------|-------------|-------------|
| **A** (current) | 0–1,000 calls | No changes needed | ~$264 |
| **B** | 1,000–5,000 | Upgrade n8n Pro ($49), Supabase Pro ($25), consider GPT-4o-mini | ~$1,300 |
| **C** | 5,000–25,000 | Self-hosted n8n, Redis cache for customer lookups, monitoring | ~$4,500 |
| **D** | 25,000+ | Replace VAPI with self-hosted Pipecat/LiveKit, AWS Lambda instead of n8n, RDS with read replicas | ~$3,500 |

**What doesn't change at any scale:** The database schema (already indexed and constrained), system prompt (conversation logic is scale-independent), Edge Functions (stateless, auto-scale), and the FAQ RAG pipeline (pgvector handles 100K+ vectors; add HNSW index at ~10K entries).

**Latency budget analysis:**

```
Deepgram STT:          150-300ms
GPT-4o (first token):  200-500ms
n8n + Supabase:        130-270ms  ← NOT the bottleneck
GPT-4o (response):     300-800ms
ElevenLabs TTS:        200-400ms
────────────────────────────────
Total per turn:        1.1-2.5 seconds
```

The LLM and TTS dominate latency. Optimizing the database layer (already at 20-50ms with indexed lookups) yields minimal improvement. The biggest production optimization lever is replacing VAPI's platform layer with self-hosted Pipecat, which eliminates the $0.05/min fee (60% of per-call cost) and allows fine-tuning the audio pipeline.

---

## B. Problem Solving & Debugging

### The `+` Encoding Bug (3 iterations to solve)

**The symptom:** Phone lookups by E.164 number (`+14155551234`) returned 0 rows despite the data existing in Supabase.

**Debugging journey:**

1. Confirmed the row existed via the Supabase dashboard — data was there
2. Tested the PostgREST query directly in the browser — worked fine
3. Isolated the issue to the n8n Supabase node

**Root cause:** The n8n Supabase node applies `encodeURI()` internally to filter strings before sending them to PostgREST. `encodeURI()` does NOT encode `+` (it's a "safe" character in URI spec). But PostgREST interprets `+` as a space in query parameters (per `application/x-www-form-urlencoded` rules). So `phone_number.eq.+14155551234` becomes `phone_number.eq. 14155551234` — no match.

**Attempt 1 — Pre-encode `+` as `%2B`:** Failed. `encodeURI()` then double-encodes the `%` to `%25`, producing `%252B` — still broken.

**Attempt 2 — Raw HTTP Request node:** Replaced the Supabase node with a manual HTTP Request node that doesn't apply `encodeURI()`. Built the URL manually with proper encoding in a Code node. This worked, but introduced inconsistency — Lookup Caller would use a different node type than every other workflow.

**Attempt 3 (final) — `phone_digits` generated column:** Added a Postgres generated column:

```sql
ALTER TABLE customers
ADD COLUMN phone_digits TEXT GENERATED ALWAYS AS (replace(phone_number, '+', '')) STORED;
```

Now Lookup Caller filters on `phone_digits.eq.14155551234` — pure digits, no `+`, nothing for `encodeURI()` to break. The canonical E.164 `phone_number` column is preserved untouched for display and other uses.

**The lesson:** When a middleware has an encoding bug you can't fix (it's in n8n's node internals), change the data shape so the problematic character never enters the pipeline. Solving the problem at the database layer means every consumer benefits, not just the one workflow.

### What I'd Optimize With More Time

1. **Persist VAPI's `analysisPlan` structured data.** The end-of-call-report payload contains `callReason`, `authenticated`, `claimNumber`, `claimStatus`, and `escalated` — rich metadata the current `interactions` table doesn't capture. Adding these columns would enable analytics like "what % of calls require escalation?" or "which claim statuses generate the most calls?"

2. **Add a Redis cache for customer lookups.** Most callers call about the same claim repeatedly. A 5-minute TTL cache on `phone_digits → customer` would cut Supabase queries by 30-50% and shave 20-50ms off tool call latency.

3. **Build an analytics dashboard.** The `interactions` table has sentiment, summary, and timestamps for every call. A simple dashboard showing call volume trends, sentiment distribution, escalation rates, and average call duration would give the business immediate visibility into agent performance.

4. **Replace VAPI's platform fee with self-hosted Pipecat.** At $0.05/min, VAPI's platform fee is the single largest per-call cost (62% of variable cost). Self-hosted Pipecat on AWS would eliminate this while giving us finer control over the audio pipeline, at the cost of more engineering effort.

5. **Add outbound call capability.** Proactively calling customers when their claim status changes ("Your claim CLM-2024-001 has been approved!") would reduce inbound call volume and improve customer satisfaction.

---

## C. Data & Metrics Evaluation

### Metrics I Would Track

| Metric | Definition | Source | Why It Matters |
|--------|-----------|--------|----------------|
| **Containment Rate** | % of calls resolved without human escalation | `interactions.summary` (NLP classification) or `analysisPlan.escalated` | Primary success KPI — measures whether the agent is actually deflecting human work |
| **Average Handle Time (AHT)** | Mean call duration in seconds | VAPI call metadata (`maxDurationSeconds` consumed vs. available) | Efficiency indicator — shorter AHT = better UX and lower cost |
| **Authentication Success Rate** | % of calls where caller identity is verified | `analysisPlan.authenticated` | Measures friction — low rate = callers struggling with phone/DOB verification |
| **First-Call Resolution (FCR)** | % of callers who don't call back within 48 hours | Join `interactions` on `phone_number` with time window | Measures whether the agent actually resolves the caller's issue |
| **Sentiment Distribution** | Ratio of positive/neutral/negative | `interactions.sentiment` | Proxy for customer satisfaction — negative trend = something broke |
| **Tool Call Failure Rate** | % of `lookup_caller` / `log_interaction` calls that return errors | n8n execution logs | Infrastructure health indicator |
| **FAQ Hit Rate** | % of FAQ queries with similarity > 0.8 | Edge Function logs (match count) | Knowledge base coverage — low rate = missing FAQ entries |
| **Cost Per Call** | Total cost / total calls | Billing data (VAPI + n8n + Supabase) | ROI tracking against human agent baseline (~$2.00/call) |

### How I Would Use This Data to Improve Agent Logic

**Prompt tuning loop:**
1. Pull calls where `sentiment = 'negative'` OR `escalated = true` from the interactions table
2. Review the VAPI transcripts (available via API) for those calls
3. Identify patterns — e.g., "caller said DOB but agent didn't recognize the format" or "agent gave wrong claim status interpretation"
4. Update the system prompt to address the pattern (e.g., add explicit handling for "I was born on the fifteenth" without a month)
5. Track whether the change improves the metric in the next 7 days

**Knowledge base improvement loop:**
1. Identify FAQ queries where `match_faqs` returned 0 results (similarity below 0.8 threshold)
2. Review what callers actually asked
3. Add new FAQ entries for uncovered topics — the `generate-embedding` webhook automatically creates the vector embedding on INSERT
4. Monitor whether FAQ hit rate increases

**Authentication friction reduction:**
1. Track cases where `authenticated = false` — segment by failure point (phone not found, name denied, DOB mismatch)
2. If DOB mismatch is the leading cause, consider relaxing the date matching in the system prompt (e.g., accepting year-only matches for elderly callers) or adding alternative verification methods
3. If "phone not found" dominates, investigate whether the `customers` table is missing records or whether STT is consistently garbling specific digit sequences

### Example: Identifying and Fixing a Drop in Containment Rate

**Scenario:** Containment rate drops from 85% to 70% over a 2-week period.

**Step 1 — Detect the drop.**
Query the `interactions` table for recent calls where `summary` mentions "escalation," "representative," or "callback," grouped by day:

```sql
SELECT DATE(timestamp),
       COUNT(*) AS total_calls,
       COUNT(*) FILTER (WHERE summary ILIKE '%representative%' OR summary ILIKE '%callback%') AS escalated,
       ROUND(1.0 - COUNT(*) FILTER (WHERE summary ILIKE '%representative%' OR summary ILIKE '%callback%')::numeric / COUNT(*)::numeric, 2) AS containment_rate
FROM interactions
WHERE timestamp > NOW() - INTERVAL '14 days'
GROUP BY DATE(timestamp)
ORDER BY DATE(timestamp);
```

**Step 2 — Segment the escalations.**
Pull VAPI's `analysisPlan` structured data (via the VAPI API) for escalated calls. Group by `callReason`:

- If most escalations have `callReason = 'claim status check'` and `claimStatus = 'requires_documentation'` → the agent isn't effectively explaining what documents are needed. The caller gives up and asks for a human.
- If most escalations have `authenticated = false` → verification flow is broken (maybe a data issue in the customers table, or STT accuracy degraded after a Deepgram model update).

**Step 3 — Hypothesize and fix.**
Suppose the root cause is `requires_documentation` calls escalating because the `claim_details` field is empty for new claims — the agent says "you need additional documentation" but can't specify *what* documentation.

Fix: Update the system prompt's `requires_documentation` branch:

```
- **Requires documentation (with details):** Read the `claim_details` field.
- **Requires documentation (no details):** "Your claim requires additional documentation.
  The most commonly needed items are proof of loss, photos of the damage, and repair
  estimates. You can upload these at our portal or email support@observeinsurance.com.
  Would you like me to go over the process?"
```

**Step 4 — Validate.**
Monitor containment rate for `requires_documentation` calls over the next 7 days. If it returns to baseline, the fix worked. If not, pull transcripts again to identify the new failure mode.

This iterative loop — **measure → segment → hypothesize → fix → validate** — is how the agent continuously improves without requiring a complete redesign. The key is having the right data in the right tables: `interactions` for aggregate metrics, VAPI's `analysisPlan` for per-call structured data, and transcripts for root-cause analysis.
