# Observe.AI Round 3 — Presentation Outline

> **Date:** Thursday, 2026-03-20, 3:00 PM PST (1 hour)
> **Format:** Live conversational panel — ~15 min structured, ~45 min Q&A
> **Panel:** CP (PM), Anna (Conversation Designer), Christian (Peer Engineer), Ira (Methodology), NV (Hiring Manager)

---

## Slide 1: Live Demo (~6 min)

**Open with the demo, not slides — show the product first.**

### Happy Path (~3 min) — Sarah Johnson

| Step | What Happens | What to Say |
|------|-------------|-------------|
| 1 | Agent greets: *"Thank you for calling Observe Insurance. My name is Sarah..."* | "This is a live call — real STT, real LLM, real TTS." |
| 2 | Give phone: 415-555-1234 | "Phone lookup hits n8n → Supabase in real time." |
| 3 | Agent confirms: *"Am I speaking with Sarah Johnson?"* | "Single match — moves straight to identity confirmation." |
| 4 | Confirm, then give DOB: March 15th, 1985 | **Callout:** "DOB gate — the agent never reveals the stored DOB. GPT-4o compares it internally, no extra API call." |
| 5 | Agent delivers approved status for CLM-2024-001 | "Claim info only surfaces after full auth." |
| 6 | Ask an FAQ: "What are your office hours?" | **Callout:** "This triggers pgvector RAG — Supabase Edge Function embeds the query, returns top-3 matches." |
| 7 | Agent logs interaction, says goodbye, hangs up | **Callout:** "Interaction logged via tool call, then deduped against end-of-call-report using a UNIQUE constraint." |

### Error Path (~3 min) — Michael Johnson

| Step | What Happens | What to Say |
|------|-------------|-------------|
| 1 | Give phone: 415-555-5678, agent asks *"Am I speaking with Michael Johnson?"* | — |
| 2 | Say "No, that's not me." | **Callout:** "Identity denial — watch the re-verification ladder kick in." |
| 3 | Agent asks for last name → "Johnson" → 2 matches | **Callout:** "Multi-match. Agent asks for first name to disambiguate — doesn't guess." |
| 4 | Say "Michael" → DOB verification → July 22nd, 1990 | "Same DOB gate, different path to get here." |
| 5 | Agent delivers pending status for CLM-2024-002 | **Callout:** "Pending — different status, different response template." |
| 6 | Agent logs, hangs up | "Same logging, same dedup." |

### Narrator Callouts Summary
- **DOB gate:** LLM-side comparison, never reads stored DOB back
- **Re-verification recovery:** phone fails → last name → disambiguate → DOB
- **Latency:** end-to-end response time (STT + LLM + tool call + TTS)
- **Escalation design:** 3 failed attempts, explicit request, emergency, or aggressive caller → human handoff

### Panelist Hooks
- **Anna:** Error handling feels natural? Voice tone during re-verification?
- **Christian:** Notice the latency? What's your read on the round-trip?
- **NV:** It works. It's shipped. Live, not a mockup.
- **CP:** Scope — this is claim status + FAQ, not the whole insurance workflow.

---

## Slide 2: Architecture & System Parts (~2 min)

**Show `diagrams/architecture.png`**

### The 5-Layer Stack

```
VAPI (telephony + voice orchestration)
  → Deepgram Nova-2 (STT)
  → GPT-4o at temp 0.3 (LLM)
  → ElevenLabs "Sarah" (TTS)
      ↓ tool calls
n8n Cloud (3 webhooks, all DB operations)
  → lookup-caller, log-interaction, end-of-call-report
      ↓ Supabase node (REST API / PostgREST)
Supabase PostgreSQL
  → customers (read), interactions (write + dedup), faqs (pgvector)
      ↑
Supabase Edge Functions
  → search-faq (VAPI Custom KB), generate-embedding (gte-small, 384 dims)
```

### One-Pass Data Flow
> "A call comes in → Deepgram transcribes → GPT-4o decides what to do → tool call fires to n8n → n8n queries Supabase → response comes back → GPT-4o forms the answer → ElevenLabs speaks it → caller hears the answer. The whole round-trip."

### Key Point
> "n8n is the integration brain — it handles all webhooks and all database operations."

### Panelist Hooks
- **Christian:** Technical depth — why PostgREST over wire protocol? (Answer: IPv6 connectivity issues with n8n Cloud → Supabase Postgres; REST API works reliably)
- **Ira:** Clear structure, separation of concerns
- **CP:** Why these components? (Answer: best-in-class for each layer, avoid vendor lock-in on any single piece)

---

## Slide 3: Conversation Design & Flow (~2 min)

**Show `diagrams/conversation-flow.png` — 17-state machine, color-coded**

### State Categories
| Color | Category | States |
|-------|----------|--------|
| Green | Happy path | Greeting → Phone Lookup → Name Confirm → DOB Verify → Claim Status → FAQ → Wrap-Up |
| Yellow | Re-verification | Phone Not Found → Last Name Lookup → Multi-Match → Claim # Lookup |
| Red | Escalation | Max Attempts → Explicit Request → Emergency → Aggressive Caller |
| Purple | Terminal | Call End → Escalation Handoff |

### Key Conversation Design Choices

1. **Multi-step auth:** phone → name confirm → DOB (never reveal stored DOB)
2. **Re-verification ladder:** phone fails → try last name → multi-match disambiguate → try claim number → escalate
3. **Escalation triggers:** 3 failed attempts, explicit request, emergency keywords, aggressive caller
4. **Voice style:** 1–3 sentences max, contractions, no bullet points or URLs read aloud
5. **System prompt structure:** 10 sections — greeting, auth, claim status, FAQ handling, escalation, wrap-up, sentiment tracking, error handling, security rules, conversation style

### Panelist Hooks
- **Anna:** This is her domain — edge cases, error recovery, how natural the language feels. Invite her to probe: "What happens if the caller gives a nickname?" "What if they refuse DOB?"
- **CP:** User journey decisions — why this auth order? (Answer: phone is lowest friction, DOB is highest security, so escalate friction gradually)

---

## Slide 4: Choices & Tradeoffs (~1.5 min)

| Decision | Why | Tradeoff |
|----------|-----|----------|
| **n8n over custom backend** | Visual workflow editor, built-in Supabase/HTTP nodes, non-engineers can inspect flows | Less control than pure code, but faster to ship and easier to hand off |
| **Supabase over Airtable** | Started with Airtable — hit 5 req/sec rate limit, no unique constraints, no vector search, 50k record cap. Migrated for pgvector, UNIQUE dedup, generated columns, PostgREST | Migration cost, but eliminated every Airtable limitation |
| **LLM-side DOB comparison** | No extra API call — GPT-4o compares spoken DOB vs stored value in-context | Relies on LLM accuracy, but avoids latency of another round-trip |
| **pgvector over external vector DB** | Keeps FAQ search inside Supabase — no Pinecone/Weaviate cost, gte-small is fast and free | Less sophisticated at massive scale, perfect for 18 FAQs |
| **GPT-4o at temp 0.3** | Low temperature for consistency in auth/claim flows | Higher would sound more natural but risks hallucinating claim details |

### Open-Source / Code-Heavy Alternative

> "I chose managed services to ship fast. Here's what the open-source route looks like and why I'd switch at scale."

| Layer | Current (Managed) | Open-Source Alternative | Tradeoff |
|-------|-------------------|----------------------|----------|
| **Voice orchestration** | VAPI ($0.05/min platform fee) | Self-hosted Pipecat or LiveKit | Eliminates the biggest per-call cost (60% of variable cost), full control over audio pipeline. But: you own the infra — WebSocket management, media streaming, failover, all on you |
| **Workflow engine** | n8n Cloud ($24–49/mo) | Self-hosted n8n on AWS ECS/Fargate, or replace with Python workers + Celery | $0/mo hosting cost, unlimited executions, no vendor cap. But: you manage uptime, scaling, and lose the visual debugging UI for non-engineers |
| **LLM** | GPT-4o via VAPI ($0.08/call) | GPT-4o-mini (~60% cheaper) or self-hosted Llama 3 on vLLM | Mini saves ~$0.05/call with minimal quality loss on structured tasks. Self-hosted Llama eliminates per-token cost entirely. But: mini may struggle on edge-case conversations, self-hosted needs GPU infra |
| **TTS** | ElevenLabs via VAPI ($0.06/call) | Coqui TTS (open-source) or XTTS v2 | Zero TTS cost. But: voice quality gap is real — ElevenLabs sounds human, open-source still sounds synthetic. For insurance, trust matters |
| **STT** | Deepgram Nova-2 via VAPI ($0.04/call) | Whisper (self-hosted) or Whisper.cpp | Zero STT cost. But: higher latency (Whisper is batch-oriented), needs GPU, and Deepgram's streaming is purpose-built for real-time voice |
| **Database** | Supabase (free tier → $25/mo Pro) | Self-hosted PostgreSQL + pgvector on RDS | More control, potentially cheaper at scale. But: you lose Supabase's Edge Functions, dashboard, and auto-managed PostgREST — more ops burden |

> **Why I didn't go this route now:** Managed services let me ship a working product end-to-end in days, not weeks. The open-source path is the right move at scale (25K+ calls/month) when the platform fees start to dominate — and I know exactly which pieces to swap and in what order.

### Panelist Hooks
- **CP:** Product tradeoffs — how did you decide what to build vs buy?
- **Christian:** Technical depth — pgvector vs dedicated vector DB, embedding model choice, Pipecat architecture
- **NV:** Pragmatic shipping — Airtable → Supabase migration shows willingness to change course. Knows when to use managed vs DIY
- **Anna:** Voice naturalness vs accuracy tradeoff at temp 0.3. Open-source TTS quality gap

---

## Slide 5: Performance & Metrics (~1.5 min)

### Cost Per Call: ~$0.24 (3-min average)

| Component | Cost/Call |
|-----------|----------|
| VAPI (telephony) | $0.05 |
| Deepgram (STT) | $0.04 |
| GPT-4o (LLM) | $0.08 |
| ElevenLabs (TTS) | $0.06 |
| Supabase (DB + Edge Functions) | $0.001 |
| **Total** | **~$0.24** |

**At scale:** 1,000 calls/month ≈ $240

### Open-Source Route: Cost Comparison

| Component | Current (Managed) | Open-Source | Savings |
|-----------|-------------------|-------------|---------|
| VAPI (telephony) | $0.05 | $0.00 (Pipecat self-hosted) | -$0.05 |
| Deepgram (STT) | $0.04 | $0.00 (Whisper self-hosted) | -$0.04 |
| GPT-4o (LLM) | $0.08 | $0.03 (GPT-4o-mini) or $0.00 (Llama 3) | -$0.05 to -$0.08 |
| ElevenLabs (TTS) | $0.06 | $0.00 (Coqui/XTTS v2) | -$0.06 |
| Supabase (DB) | $0.001 | $0.001 (RDS) | ~$0.00 |
| **Total/call** | **~$0.24** | **~$0.03–0.001** | **85–99% cheaper** |
| GPU infra (amortized) | $0.00 | ~$0.02–0.05/call | New cost |
| **Net total/call** | **~$0.24** | **~$0.05–0.08** | **~67–79% cheaper** |

> "At 1,000 calls/month the managed route costs $240 — not worth optimizing. At 25,000 calls/month it's $6,000 — that's when the open-source swap to Pipecat + Whisper + Coqui pays for itself, even after GPU costs. The tradeoff is engineering time: weeks of infra work and you own the uptime."

### Latency Budget: 1.1–2.5s Per Turn

| Stage | Latency |
|-------|---------|
| Deepgram STT (transcription) | 100–300ms |
| GPT-4o (first token / tool decision) | 200–500ms |
| n8n → Supabase round-trip (tool call) | 20–50ms |
| GPT-4o (spoken response generation) | 300–800ms |
| ElevenLabs TTS (streaming) | 200–400ms |
| **Total perceived delay** | **1.1–2.5s** |

> "Under 2.5 seconds is the threshold where callers start feeling the delay. The LLM and TTS dominate latency — the database layer is already at 20–50ms with indexed lookups. The biggest production optimization lever would be replacing VAPI's platform layer with self-hosted Pipecat to fine-tune the audio pipeline."

### Compliance & Testing
- **HIPAA-eligible mode:** `hipaaEnabled: true` — no call recording, BAA-ready
- **Test coverage:** 10 tests passing (VAPI envelope parsing)
- **Dedup:** UNIQUE constraint on `vapi_call_id` — atomic, no race conditions (replaced a 10-second wait hack from Airtable era)
- **FAQ search:** pgvector with gte-small embeddings (384 dims), top-3 retrieval, 0.8 similarity threshold

### Panelist Hooks
- **NV:** Real metrics, cost-conscious thinking — $0.24/call is concrete
- **Ira:** Testing strategy, validation approach
- **Christian:** Dedup strategy (UNIQUE constraint vs application-level), embedding model choice (gte-small vs alternatives)

---

## Slide 6: Scalability & Production Readiness (~1.5 min)

### What's Production-Ready Now
- Auth flow (phone → name → DOB, re-verification ladder)
- Claim status lookup (approved / pending / requires_documentation)
- FAQ RAG (18 entries, pgvector semantic search)
- Interaction logging with atomic dedup
- Error handling (not found, multi-match, max attempts)
- HIPAA mode enabled

### What I'd Add for Production Scale
1. **Phone number provisioning** — currently using VAPI Dashboard "Talk" button, would provision a real number (~$1.50/mo)
2. **Monitoring & alerting** — n8n execution logs exist but need dashboards (Grafana/Datadog)
3. **Multi-language support** — Deepgram + ElevenLabs both support it, GPT-4o handles multilingual
4. **Fine-tuned STT** — insurance terminology (claim numbers, medical terms)
5. **Rate limiting** — on webhook endpoints
6. **Horizontal scaling** — n8n Cloud handles it natively, Supabase connection pooling via Supavisor

### Phased Rollout (NV's Philosophy)
> "Start narrow — claim status only. Measure containment rate. Expand to more use cases. This is exactly that approach: one vertical slice, fully working, before going wide."

### Connect to Observe.AI
> "This is a smaller version of what your agents do at scale — same architecture pattern, same observe-then-automate philosophy. I built the agent that handles the call; Observe.AI builds the platform that makes thousands of those agents better."

### Panelist Hooks
- **NV:** Phased rollout, pragmatism — does this match how they think about deploying?
- **CP:** Roadmap thinking — what would the next 3 features be?
- **Christian:** Scaling considerations — connection pooling, worker concurrency, embedding throughput

---

## Q&A Reference (not slides — notes to have ready)

### Files to Pull Up on Demand
| File | When to Show |
|------|-------------|
| `vapi/system_prompt.md` | Anna asks about prompt structure, conversation rules |
| `n8n/workflows/*.json` | Christian asks about workflow internals |
| `supabase/migrations/*.sql` | Christian asks about schema design |
| `supabase/functions/search-faq/index.ts` | Questions about RAG implementation |
| `supabase/functions/generate-embedding/index.ts` | Questions about embedding pipeline |
| `diagrams/conversation-flow.png` | Anna asks about edge cases or state transitions |

### Per-Panelist Likely Questions

**NV (Hiring Manager):**
- "How would you scale this to 10k calls/day?" → Connection pooling, queue-based processing, multi-region VAPI
- "What's your approach to monitoring in production?" → n8n execution logs + Supabase dashboard, would add alerting layer
- "Tell me about a time you changed direction mid-project" → Airtable → Supabase migration (rate limits, no vector search, no unique constraints)

**CP (PM):**
- "How did you prioritize what to build?" → Claim status is highest-volume call type, FAQ is second — covers 60–70% of inbound
- "What metrics would you track?" → Containment rate, AHT, CSAT, cost per call, escalation rate
- "How would you involve non-technical stakeholders?" → n8n visual workflows, Supabase dashboard — no code needed to inspect

**Anna (Conversation Designer):**
- "What happens when the caller interrupts?" → VAPI handles barge-in natively, Deepgram detects speech overlap
- "How do you handle silence?" → 30-second silence timeout, agent prompts before disconnecting
- "What about caller frustration?" → Sentiment tracking in system prompt, escalation on aggressive tone

**Christian (Peer Engineer):**
- "Why not a direct Postgres connection?" → n8n Cloud IPv6 issues with Supabase Postgres, REST API is reliable and sufficient
- "How does dedup work?" → UNIQUE constraint on vapi_call_id, INSERT ON CONFLICT DO NOTHING via Supabase node error handling
- "What's the embedding strategy?" → gte-small (384 dims), Supabase Edge Function auto-embeds on insert, match_faqs RPC for search

**Ira (Methodology):**
- "How do you test this?" → 10 automated tests (VAPI envelope parsing), manual demo scripts for e2e
- "What's your deployment process?" → deploy-vapi.sh resolves config → VAPI API, n8n workflows managed in cloud, Supabase migrations versioned

### Gap Framing (from interview briefing)
- **Experience density:** "I built this end-to-end in [X days] — every layer, every integration, every edge case."
- **SIP/PSTN understanding:** "VAPI abstracts telephony, but I understand the call flow — SIP INVITE → media stream → webhook events."
- **iPaaS comfort:** "n8n is my integration layer by choice, not by limitation. I could have written it all in code — I chose visual workflows for inspectability."

---

## Timing Summary

| Section | Duration | Running Total |
|---------|----------|---------------|
| 1. Live Demo | 6 min | 6 min |
| 2. Architecture | 2 min | 8 min |
| 3. Conversation Design | 2 min | 10 min |
| 4. Tradeoffs | 1.5 min | 11.5 min |
| 5. Performance | 1.5 min | 13 min |
| 6. Scalability | 1.5 min | 14.5 min |
| **Q&A / Conversation** | **45.5 min** | **60 min** |

**Total structured: ~15 min. The remaining 45 min is the real evaluation — conversational depth, technical fluency, and how you engage each panelist.**
