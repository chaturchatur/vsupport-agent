# Tasks & Plans

> Last verified: 2026-03-17

## Context

Build a voice-enabled AI agent that handles inbound insurance claim support calls for "Observe Insurance." Deliverables: working VAPI voice agent, n8n workflows, FastAPI utility layer, Airtable integrations (read + write), demo recordings (happy + error paths), conversation flow + architecture diagrams, and a technical write-up.

## Tech Stack

- **Voice Platform**: VAPI (telephony + STT/TTS/LLM orchestration)
- **STT**: Deepgram Nova-2 (via VAPI)
- **LLM**: GPT-4o (via VAPI)
- **TTS**: ElevenLabs (via VAPI)
- **Workflow Engine**: n8n Cloud — primary integration layer (all VAPI webhooks + Airtable CRUD)
- **Backend**: Python + FastAPI — utility layer (phone normalization, health endpoint)
- **Data Store**: Airtable (Customers table + Interactions table)
- **CLI Tools**: VAPI CLI, pyairtable CLI (with custom Claude Code skills `/vapi` and `/airtable`)
- **Diagrams**: Excalidraw (via excalidraw-diagram skill)
- **Hosting**: n8n Cloud (Starter plan); FastAPI local + ngrok or AWS Lambda

---

## Phase 0: Tooling & Skills Setup

- [x] **0a: Install CLIs** — `pyairtable` CLI installed, VAPI CLI pending
- [x] **0b: Create custom Claude Code skills** — `/vapi` and `/airtable` skills created via `/skill-creator`
- [x] **0c: Install Excalidraw diagram skill** — installed at `.claude/skills/excalidraw-diagram`
- [x] **0d: Account setup (user action)** — VAPI, Airtable, n8n Cloud sign-ups + API keys
  - VAPI: Sign up at dashboard.vapi.ai → get API key → `vapi auth`
  - Airtable: Sign up → create Personal Access Token → set `AIRTABLE_API_KEY` env var
  - n8n Cloud: Sign up at app.n8n.cloud (Starter plan)
- [x] **0e: Local dev tunneling** — `ngrok` installed

**Status:** Phase 0 complete.

---

## Phase 1: Project Foundation

- [x] **Step 1: File structure** — Create project scaffolding:
  ```
  app/
  ├── __init__.py
  ├── main.py              # FastAPI app: /health, /normalize-phone, CORS
  ├── config.py            # Pydantic Settings (env vars)
  ├── schemas.py           # Request/response Pydantic models
  └── services/
      ├── __init__.py
      └── phone.py         # Phone normalization utility (phonenumbers lib)
  vapi/
  ├── assistant_config.json  # VAPI assistant definition
  └── system_prompt.md       # GPT-4o system prompt (version-controlled)
  n8n/
  └── workflows/
      ├── lookup-caller.json
      ├── log-interaction.json
      └── end-of-call-report.json
  scripts/
  ├── happy-path-script.md
  └── error-path-script.md
  tests/
  ├── conftest.py
  ├── test_phone_normalize.py
  └── test_vapi_envelope.py
  diagrams/
  ├── conversation-flow.excalidraw
  └── architecture.excalidraw
  ```
- [x] **Step 2: Dependencies** — `requirements.txt`: fastapi, uvicorn, phonenumbers, pydantic-settings, httpx, pytest. `.env.example` with all required env vars.

**Status:** Phase 1 complete.

---

## Phase 2: Airtable Setup

- [x] **Step 3: Create Airtable base** — Customers table + Interactions table
  - **Customers**: first_name, last_name, phone_number (E.164), claim_number, claim_status (approved/pending/requires_documentation), claim_details
  - **Interactions**: caller_name, phone_number, summary, sentiment (positive/neutral/negative), timestamp, vapi_call_id
  - Populate 3-5 sample rows (one per claim_status, two with same last_name, requires_documentation row must have claim_details populated)
  - Verify with `/airtable` skill

**Status:** Phase 2 complete.

---

## Phase 3: n8n Workflows

All n8n workflows created programmatically via the **n8n REST API** (`N8N_API_KEY`).

- [x] **Step 4: Workflow — Lookup Caller** — Webhook trigger → auth (X-Vapi-Secret) → extract call.id + toolCallId → parse arguments → normalize phone → Airtable search → format response (single/multiple/not-found/error)
  - Supports three search modes: phone_number, last_name, claim_number
  - Workflow ID: `MbxKTCGUszqbCafS`, webhook path: `/webhook/lookup-caller`
- [x] **Step 5: Workflow — Log Interaction** — Webhook trigger → auth → extract call.id + toolCallId → parse arguments → set timestamp → Airtable create record → error branch
  - Workflow ID: `fS60qOqtDuWyIReD`, webhook path: `/webhook/log-interaction`
- [x] **Step 5b: Workflow — End-of-Call Report** — Webhook trigger → auth → filter end-of-call-report → 10s wait (race condition prevention) → extract call data → check dedup → create if missing
  - Race condition note: 10s Wait node ensures log_interaction completes before dedup check
  - Workflow ID: `oRACRgI5oTF5TSGk`, webhook path: `/webhook/vapi-server`
- [x] Export all three workflows as JSON to `n8n/workflows/`

---

## Phase 4: FastAPI Utility Layer

- [x] **Step 6: Phone normalization service** (`app/services/phone.py`) — `normalize_phone(raw, default_region="US")` using `phonenumbers` lib, E.164 output
- [x] **Step 7: Schemas** (`app/schemas.py`) — `NormalizePhoneRequest` / `NormalizePhoneResponse`
- [x] **Step 8: App** (`app/main.py`) — `GET /health`, `POST /normalize-phone`, CORS middleware

**Status:** Phase 4 complete.

---

## Phase 5: VAPI Agent Configuration

- [x] **Step 9: System prompt** (`vapi/system_prompt.md`) — Full conversational flow: greeting, authentication, re-verification (last_name → claim_number), claim status handling, FAQ knowledge base, escalation, wrap-up + logging, sentiment rules, error handling
- [x] **Step 10: Assistant config** (`vapi/assistant_config.json`) — GPT-4o, ElevenLabs voice (sarah), Deepgram Nova-2, tools (lookup_caller, log_interaction) with per-tool server URLs, endCallFunctionEnabled, hipaaEnabled, analysisPlan (summary + structured data), server object for end-of-call-report webhook
  - Placeholder URLs use `{{N8N_WEBHOOK_BASE_URL}}` and `{{VAPI_SECRET}}` — replace before deploying via VAPI CLI or `/vapi` skill

**Status:** Phase 5 complete.

---

## Phase 6: Diagrams

- [x] **Step 11: Conversation state machine diagram** — `diagrams/conversation-flow.excalidraw` (states, transitions, color-coded: green=happy, red=error, yellow=re-verification)
- [x] **Step 12: System architecture diagram** — `diagrams/architecture.excalidraw` (VAPI, n8n, FastAPI, Airtable, monitoring touchpoints)

**Status:** Phase 6 complete.

---

## Phase 7: Tests, Deployment & Demos

- [x] **Step 13: Tests** — 20 tests passing: 6 phone normalization unit tests, 4 FastAPI endpoint tests, 6 VAPI tool-call envelope tests, 4 end-of-call-report envelope tests. `pytest tests/ -p no:playwright`
- [x] **Step 14: Deployment** — n8n Cloud (already deployed), deploy script (`scripts/deploy-vapi.sh`) resolves placeholders and creates/updates VAPI assistant via REST API. Assistant ID: `2d8ea99b-1187-4a24-a710-28e1a96af9ee`. FastAPI runs locally (`uvicorn app.main:app --reload`). Phone number not yet provisioned.
- [x] **Step 15: Demo scripts** — 3 demo scenarios documented: happy path (approved claim), error paths (identity denial + re-verification with multi-match, phone not found + abrupt hangup, requires documentation flow)

**Status:** Phase 7 complete.

---

## Phase 8b: FAQ RAG with Supabase pgvector + VAPI Custom KB

- [x] **Enable pgvector** — Migration `004_enable_pgvector.sql`
- [x] **Create faqs table + match_faqs RPC** — Migration `005_faqs_table.sql` (vector(384), inner product distance)
- [x] **Create generate-embedding Edge Function** — Auto-embeds FAQ rows using gte-small on insert/update
- [x] **Create search-faq Edge Function** — VAPI Custom KB endpoint: embed query → pgvector search → return docs
- [x] **Seed 18 FAQ entries** — `data/faqs.json` + `supabase/seed_faqs.sql`, covering office hours, claims, billing, coverage, appeals, etc.
- [x] **Generate embeddings** — All 18 rows embedded via generate-embedding function
- [x] **Create VAPI Knowledge Base resource** — ID: `5e53959b-b870-4cd5-aba6-d79c0d219635`
- [x] **Update assistant config** — `model.knowledgeBaseId` + system prompt Section 4 replaced with KB instructions
- [x] **Update deploy script** — `VAPI_KB_ID` placeholder resolution
- [x] **Test semantic search** — Exact match ("office hours") and paraphrased ("how can I appeal") both return correct results
- [x] **Regression tests** — 20/20 passing
- [x] **Configure DB webhook** — PostgreSQL trigger via migration `006_faq_embedding_trigger.sql` (pg_net → Edge Function)
- [ ] **Live voice test** — VAPI Dashboard "Talk" button → ask FAQ questions → verify KB retrieval

**Status:** Implementation complete. DB webhook requires manual Dashboard config. Live voice test pending.

---

## Phase 9: Technical Write-Up

- [x] Architecture choices (why VAPI, n8n, GPT-4o, Supabase, FastAPI) — `docs/interview-briefing.md` Section 4
- [x] Production scaling considerations (component limits, latency budget, scaling phases A-D) — Section 7
- [x] Per-call cost estimate (~$0.24/call, volume scaling table, break-even analysis) — Section 6
- [x] HIPAA considerations (BAA-eligible mode, production gaps, data flow audit) — Section 5
- [x] Problem solving & debugging (6 war stories: `+` encoding, dedup race, IPv6, schema cache, VAPI quirks, DOB) — Section 10
- [x] What I'd optimize (immediate wins, medium-term, longer-term roadmap) — Section 8
- [x] Data & metrics evaluation (testing suite, demo scripts, quality assurance) — Section 9

**Status:** Phase 9 complete. Full briefing at `docs/interview-briefing.md`.

---

## Verification Checklist

- [ ] `/airtable` — verify base schema, sample data
- [ ] `/vapi` — verify assistant config (tools, endCall, hipaa, analysisPlan)
- [ ] n8n webhook auth — test 401 rejection without X-Vapi-Secret
- [ ] n8n Workflow 1 — phone, last_name (single + multi), claim_number lookups
- [ ] n8n Workflow 2 — log-interaction with vapi_call_id
- [ ] n8n Workflow 3 — end-of-call-report dedup (skip if already logged)
- [ ] n8n error branches — simulate Airtable timeout
- [ ] FastAPI — health check 200, /normalize-phone with default_region=US
- [ ] `pytest tests/` — all pass
- [ ] Call test — happy path (verify Airtable log + claim_number in response)
- [ ] Call test — identity denial (re-verification + multi-match + log)
- [ ] Call test — not found (end-of-call-report fallback logging)
- [ ] Call test — endCall graceful hangup
- [ ] Excalidraw diagrams render correctly

---

## Reference

Full plan details: [plan.md](../plan.md) (architecture diagrams, system prompt content, assistant config JSON, demo scripts, write-up outline)

> **Usage:** Update task checkboxes as work progresses. Run `/update-docs` after completing each phase.
