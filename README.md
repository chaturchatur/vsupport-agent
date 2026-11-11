# Vsupport-agent

A production-ready **VoiceAI insurance claims support agent** for "Observe Insurance." Callers dial in, authenticate via phone number and date of birth, and get real-time claim status updates, FAQ answers, and escalation to human representatives — all through natural voice conversation.

![Architecture](diagrams/architecture.png)

## How It Works

```
Caller  ──phone──▶  VAPI  (Deepgram STT → GPT-4o → ElevenLabs TTS)
                      │ tool calls
                      ▼
                   n8n Cloud  (webhook auth + envelope parsing)
                      │ REST API (PostgREST)
                      ▼
                Supabase PostgreSQL
                   ├── customers     (read — account lookup)
                   ├── interactions  (write — call logs + call outcomes)
                   ├── follow_ups    (write — escalations and callbacks for humans)
                   └── faqs          (pgvector — FAQ retrieval)
```

Around the call itself (added on `feature/pre-post-call-workflows`, not yet verified on a live call):

```
Before the call   VAPI assistant-request ─▶ n8n pre-call-context ─▶ caller recognised by caller ID
                                                                   (first-name greeting, DOB still required)
After the call    VAPI end-of-call-report ─▶ n8n end-of-call-report ─▶ outcomes stored on interactions
                                                                     ├─ escalation / negative ─▶ follow_ups + email alert
                                                                     ├─ resolved + authenticated ─▶ claim-status SMS (Twilio)
                                                                     └─ follow-up needed ─▶ follow_ups (callback)
Monitoring        Supabase ─▶ v_call_outcomes_daily ─▶ Grafana dashboard (containment rate, escalations, ...)
```

1. **Caller dials in** — VAPI handles telephony, streams audio through Deepgram (STT), GPT-4o (conversation), and ElevenLabs (TTS)
2. **Authentication** — The agent asks for phone number → confirms name → verifies date of birth
3. **Claim lookup** — GPT-4o triggers `lookup_caller` tool → n8n webhook → Supabase query → result returned to caller
4. **FAQ handling** — General questions route through VAPI's Custom Knowledge Base → Supabase Edge Function (pgvector semantic search with gte-small embeddings)
5. **Call logging** — Interactions logged via `log_interaction` tool + end-of-call report (with dedup)
6. **Call outcomes** — The end-of-call report stores whether the call was resolved without a human, escalated, or needs a follow-up, then opens follow-ups, alerts a human, or texts the caller their claim status
7. **Caller recognition** — Before the agent speaks, a known caller ID is matched to a customer so the greeting uses their first name. Caller ID is not authentication: date of birth is still verified before any claim detail is shared

![Conversation Flow](diagrams/conversation-flow.png)

## Tech Stack

| Layer | Technology | Role |
|-------|-----------|------|
| **Telephony & Orchestration** | [VAPI](https://vapi.ai) | Call handling, STT/LLM/TTS routing |
| **Speech-to-Text** | Deepgram Nova-2 | Real-time transcription |
| **LLM** | GPT-4o (via VAPI) | Conversational AI, tool calling |
| **Text-to-Speech** | ElevenLabs ("Sarah") | Natural voice synthesis |
| **Workflow Engine** | n8n Cloud | Webhook auth, envelope parsing, all DB operations |
| **Database** | Supabase PostgreSQL | Customers, interactions, FAQs (pgvector) |
| **FAQ Search** | Supabase Edge Functions + pgvector | Semantic search with gte-small embeddings |
| **Config** | Python + Pydantic Settings | Environment configuration |

## Project Structure

```
Vsupport-agent/
├── app/
│   └── config.py                 # Pydantic Settings (.env)
├── vapi/
│   ├── assistant_config.json     # Full VAPI assistant config (GPT-4o, tools, analysis)
│   └── system_prompt.md          # Conversational system prompt (version-controlled)
├── n8n/workflows/                # n8n workflow JSON exports
│   ├── lookup-caller.json        # Phone/name/claim lookup → Supabase
│   ├── log-interaction.json      # Call interaction logging → Supabase
│   ├── end-of-call-report.json   # Post-call summary with dedup, outcomes, follow-up actions
│   └── pre-call-context.json     # Caller recognition before the agent speaks (assistant-request)
├── supabase/
│   ├── migrations/               # DDL: customers, interactions (+ outcomes), follow_ups, faqs, pgvector
│   ├── functions/
│   │   ├── generate-embedding/   # Auto-embed FAQ rows (gte-small, 384 dims)
│   │   └── search-faq/           # VAPI Custom KB endpoint (pgvector search)
│   ├── seed.sql                  # 5 sample customers
│   └── seed_faqs.sql             # 18 FAQ entries
├── scripts/
│   ├── deploy-vapi.sh            # Resolve placeholders → deploy assistant
│   ├── deploy-n8n.sh             # Resolve placeholders → create/update n8n workflows
│   ├── resolve_n8n_placeholders.py # Fills __PLACEHOLDER__ values from .env at deploy time
│   ├── configure-vapi-phone.sh   # enable/disable pre-call recognition on the phone number
│   ├── happy-path-script.md      # Demo: approved claim flow
│   └── error-path-script.md      # Demo: re-verification & error flows
├── diagrams/                     # Excalidraw diagrams + rendered PNGs
├── data/faqs.json                # FAQ source data (18 entries)
├── grafana/                      # Dashboard JSON + setup steps (read-only Postgres role)
├── tests/                        # pytest: envelopes, outcome mapping, follow-up routing, pre-call responses
├── docs/
│   └── technical-writeup.md      # Technical write-up (architecture, costs, HIPAA)
└── requirements.txt
```

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 18+ (the tests execute the JavaScript inside the n8n Code nodes)
- Accounts: [VAPI](https://vapi.ai), [n8n Cloud](https://n8n.io), [Supabase](https://supabase.com)

### Setup

```bash
# Clone and install
git clone <repo-url>
cd Vsupport-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Fill in: VAPI_API_KEY, VAPI_SECRET, N8N_API_KEY, N8N_WEBHOOK_BASE_URL,
#          SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
# Optional: ALERT_EMAIL_*, TWILIO_*, N8N_*_CREDENTIAL_ID (post-call alert email and SMS;
#           left empty, those actions are skipped)
```

### Database Setup

Run migrations against your Supabase project (via Dashboard SQL Editor or Supabase CLI):

```sql
-- Run in order:
-- supabase/migrations/001_initial_schema.sql    (customers + interactions)
-- supabase/migrations/002_phone_digits_column.sql
-- supabase/migrations/003_add_date_of_birth.sql
-- supabase/migrations/004_enable_pgvector.sql
-- supabase/migrations/005_faqs_table.sql
-- supabase/migrations/006_faq_embedding_trigger.sql
-- supabase/migrations/007_interaction_outcomes.sql  (outcome columns + v_call_outcomes_daily)
-- supabase/migrations/008_follow_ups.sql            (escalation / callback queue)
```

Then seed sample data:

```bash
# Apply seed data
psql $DATABASE_URL -f supabase/seed.sql
psql $DATABASE_URL -f supabase/seed_faqs.sql
```

### Deploy Edge Functions

```bash
supabase functions deploy generate-embedding
supabase functions deploy search-faq
supabase secrets set VAPI_SECRET=your_secret
```

### Deploy VAPI Assistant

```bash
./scripts/deploy-vapi.sh
```

This resolves `{{N8N_WEBHOOK_BASE_URL}}`, `{{VAPI_SECRET}}`, and `{{VAPI_KB_ID}}` placeholders in the config and creates/updates the assistant via the VAPI REST API.

### Deploy n8n Workflows

```bash
./scripts/deploy-n8n.sh                 # all workflows
./scripts/deploy-n8n.sh pre-call-context
```

Apply migrations 007 and 008 first. `__PLACEHOLDER__` values in the workflow exports are filled in from `.env`.

### Run Tests

```bash
pytest tests/ -p no:playwright
```

The tests cover VAPI envelope shapes and run the real JavaScript from the n8n Code nodes under Node.js. They do not call VAPI, n8n, Supabase, Twilio or Grafana.

## n8n Workflows

Four workflows, all authenticated via `X-Vapi-Secret` header. The first three run on n8n Cloud; `pre-call-context` and the extended `end-of-call-report` are in the repo but have not been deployed yet:

| Workflow | Webhook Path | Purpose |
|----------|-------------|---------|
| **Lookup Caller** | `/webhook/lookup-caller` | Account lookup by phone, last name, or claim number |
| **Log Interaction** | `/webhook/log-interaction` | Log call summary, sentiment, caller info |
| **End-of-Call Report** | `/webhook/vapi-server` | Post-call report with dedup, call outcomes, follow-ups, alert email, claim-status SMS |
| **Pre-Call Context** | `/webhook/pre-call-context` | Answers VAPI's `assistant-request`: recognises the caller and returns greeting variables |

## VAPI Assistant

- **Model**: GPT-4o (temperature 0.3)
- **Voice**: ElevenLabs "Sarah"
- **Transcriber**: Deepgram Nova-2
- **HIPAA**: Enabled (BAA-eligible, no call recording)
- **Knowledge Base**: Custom KB backed by Supabase pgvector (18 FAQs)
- **Max call duration**: 10 minutes
- **Tools**: `lookup_caller`, `log_interaction`, `endCall`

### Conversation Flow

1. **Greeting** → automatic first message
2. **Authentication** → phone lookup → name confirmation → DOB verification
3. **Claim status** → approved / pending / requires documentation
4. **FAQ handling** → semantic search via pgvector Knowledge Base
5. **Escalation** → human callback arranged when needed
6. **Wrap-up** → summary, log interaction, graceful hangup

## Database Schema

**Supabase PostgreSQL**:

- **customers** — `first_name`, `last_name`, `phone_number` (E.164), `phone_digits` (generated), `claim_number` (unique), `claim_status`, `claim_details`, `date_of_birth`
- **interactions** — `caller_name`, `phone_number`, `summary`, `sentiment`, `vapi_call_id` (unique, enables dedup), plus nullable outcome columns: `call_reason`, `authenticated`, `claim_number`, `claim_status`, `resolved_without_human`, `escalation_requested`, `follow_up_needed`, `follow_up_reason`, `duration_seconds`, `ended_reason`, `caller_phone_digits`
- **follow_ups** — `vapi_call_id`, `kind` (`escalation` | `callback`), `reason`, `status` (default `open`), `created_at`
- **v_call_outcomes_daily** (view) — calls, authenticated calls, contained calls, escalations and containment rate per day
- **faqs** — `question`, `answer`, `category`, `embedding` (vector(384) via gte-small)

## Key Design Decisions

- **n8n as primary integration layer** — All VAPI webhooks and DB operations go through n8n Cloud, keeping the architecture simple and the codebase small.
- **Supabase over Airtable** — Migrated from Airtable for pgvector support (FAQ RAG), proper constraints (UNIQUE for dedup), and generated columns (`phone_digits` to avoid PostgREST encoding bugs).
- **`phone_digits` generated column** — Strips `+` from E.164 phone numbers to work around the Supabase n8n node's `encodeURI()` mangling of `+` in PostgREST filter strings.
- **UNIQUE constraint dedup** — End-of-call report uses `INSERT ON CONFLICT DO NOTHING` via `vapi_call_id` uniqueness, replacing a fragile 10-second wait + search approach.
- **FAQ RAG via pgvector** — gte-small embeddings (384 dims) with inner product similarity search, served through Supabase Edge Functions as a VAPI Custom Knowledge Base.

## Cost Estimate

~**$0.24 per call** (based on 3-minute average):

| Component | Cost/call |
|-----------|----------|
| VAPI platform | $0.05 |
| Deepgram STT | $0.04 |
| GPT-4o | $0.08 |
| ElevenLabs TTS | $0.06 |
| Supabase | $0.001 |
| **Total** | **~$0.24** |

See `docs/technical-writeup.md` for volume scaling analysis and production considerations.

## Testing

```bash
pytest tests/ -v
```

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_vapi_envelope.py` | 10 | VAPI tool-call & EOC envelope parsing |
| `test_post_call_outcomes.py` | TBD_OUT | Analysis schema, outcome mapping with missing fields, outcome merge, migration 007 |
| `test_follow_up_routing.py` | TBD_FUP | Escalation / SMS / callback conditions, SMS guard rails, failure isolation |
| `test_pre_call_context.py` | TBD_PRE | `assistant-request` envelope, known / unknown / error responses, prompt variables |
| `test_deploy_and_dashboard.py` | TBD_DEP | Deploy-time placeholder resolution, Grafana dashboard structure |

## Documentation

- `docs/technical-writeup.md` — Full technical write-up (architecture, HIPAA, costs, scaling, war stories)
- `vapi/system_prompt.md` — Complete conversational system prompt
- `n8n/workflows/*.md` — Node-by-node explanation of each workflow
- `grafana/README.md` — Dashboard setup (read-only role, data source, import)
- `.agent/` — Living project documentation (architecture, SOPs, decisions, gotchas)
