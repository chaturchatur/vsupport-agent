# VoiceAI Claims Support Assistant — Implementation Plan

## Context
Build a voice-enabled AI agent that handles inbound insurance claim support calls for "Observe Insurance." This is a take-home challenge requiring: a working VAPI voice agent, n8n workflows, a FastAPI utility layer, Airtable integrations (read + write), demo recordings (happy + error paths), conversation flow + architecture diagrams, and a technical write-up.

## Tech Stack
- **Voice Platform**: VAPI (telephony + STT/TTS/LLM orchestration)
- **STT**: Deepgram Nova-2 (via VAPI)
- **LLM**: GPT-4o (via VAPI)
- **TTS**: ElevenLabs (via VAPI)
- **Workflow Engine**: n8n Cloud — primary integration layer (all VAPI webhooks + Airtable CRUD)
- **Backend**: Python + FastAPI — utility layer (phone normalization, health endpoint, local testing)
- **Data Store**: Airtable (Customers table + Interactions table)
- **CLI Tools**: VAPI CLI, pyairtable CLI (with custom Claude Code skills via `/skill-creator`)
- **Diagrams**: Excalidraw (via excalidraw-diagram skill)
- **Hosting**: n8n Cloud (Starter plan); FastAPI local + ngrok or AWS Lambda. AWS recommended for production in write-up.

## Architecture

### Diagram A: Conversation State Machine

```
[Greeting] → [Ask Phone Number] → [lookup_caller tool]
    → [Found] → "Am I speaking with {first_name} {last_name}?"
        → [Confirmed] → [Claim Status] → [FAQ / Questions] → [Wrap-up + endCall] → [End]
        → [Denied] → [Re-verify: ask last name]
            → [Single match] → Re-confirm identity → [Claim Status] → ...
            → [Multiple matches] → Ask first name to disambiguate → [Claim Status] → ...
            → [No Match] → [Re-verify: ask claim number]
                → [Match] → [Claim Status] → ...
                → [No Match] → [Escalate: "scheduling callback"] → [End]
    → [Not Found] → ["No record found, scheduling callback"] → [End]
    → [Airtable Error] → ["Having trouble, will schedule a callback"] → [End]

Post-call (always): [VAPI end-of-call-report webhook] → [Check dedup] → [Log if missing]
```

### Diagram B: System Architecture

```
[Caller] → PSTN → [VAPI] → Deepgram STT → GPT-4o → ElevenLabs TTS → [Caller]
                     │
                     ├── tool calls via per-tool server.url → [n8n tool webhooks]
                     │     (lookup-caller, log-interaction)
                     │
                     └── serverUrl (all other webhook types) → [n8n server webhook]
                           (end-of-call-report, status-update, etc.)
                     ▼
              [n8n Cloud] ─── PRIMARY INTEGRATION LAYER
                ├── Workflow 1: lookup-caller (per-tool URL)
                │     └── (calls FastAPI /normalize-phone if needed)
                ├── Workflow 2: log-interaction (per-tool URL, LLM-triggered)
                └── Workflow 3: end-of-call-report (serverUrl, VAPI auto-fires)
                   │
                   ▼
              [Airtable Base]
                ├── Customers (read)
                └── Interactions (write)

[FastAPI] ─── UTILITY LAYER (local + ngrok / Lambda)
  ├── GET  /health
  └── POST /normalize-phone (called by n8n internally)
```

**Webhook routing note**: VAPI uses per-tool `server.url` for tool calls (lookup-caller, log-interaction) and `serverUrl` for all other webhook types (end-of-call-report, status-update, etc.). Both are set intentionally — per-tool URLs route tool calls to dedicated n8n workflows, while `serverUrl` catches everything else.

**Monitoring touchpoints** (marked on diagram):
- 📊 VAPI Dashboard: call duration, latency, cost, completion rate
- 📋 n8n Execution Logs: workflow success/failure rates, execution time
- 📝 Airtable: write success/failure tracked via n8n error branches

**n8n handles**: ALL VAPI webhook reception, ALL Airtable CRUD, end-of-call-report processing, response formatting
**FastAPI handles**: Phone number normalization helper (called by n8n), health endpoint, local testing

---

## Phase 0: Tooling & Skills Setup

### Step 0a: Install CLIs
- **VAPI CLI**: `curl -sSL https://vapi.ai/install.sh | bash`
- **pyairtable CLI**: `pip install 'pyairtable[cli]'`
- Verify: `vapi --help`, `pyairtable --help`

### Step 0b: Create Custom Claude Code Skills (via `/skill-creator`)

Use the `/skill-creator` skill to generate both skills:

**Skill: `/vapi`** — wraps VAPI CLI for assistant management
- Operations: create/list/update assistants, list phone numbers, create calls, listen for webhooks
- Example usage: `/vapi list assistants`, `/vapi create-assistant --from-config`

**Skill: `/airtable`** — wraps pyairtable CLI for data operations
- Operations:
  - `whoami` — verify auth
  - `bases` — list all bases
  - `schema {base_id}` — show base/table schema
  - `records {base_id} {table_name}` — query records with formula filter
- Example usage: `/airtable bases`, `/airtable records appXXX Customers --filter "phone_number=+15551234567"`

### Step 0c: Install Excalidraw Diagram Skill
- Clone: `git clone https://github.com/coleam00/excalidraw-diagram-skill.git`
- Copy: `cp -r excalidraw-diagram-skill .claude/skills/excalidraw-diagram`
- Setup renderer: follow SKILL.md instructions (`uv sync && uv run playwright install chromium`)

### Step 0d: Account Setup (User Action Required)
- **VAPI**: Sign up at dashboard.vapi.ai → get API key → `vapi auth`
- **Airtable**: Sign up → create Personal Access Token at airtable.com/create/tokens → set `AIRTABLE_API_KEY` env var
- **n8n Cloud**: Sign up at app.n8n.cloud (Starter plan — unlimited executions, 5+ active workflows). Provides public HTTPS webhook URLs out of the box.

### Step 0e: Local Dev Tunneling
- Install: `brew install ngrok` (or `brew install cloudflared`)
- Run: `ngrok http 8000` to expose FastAPI locally during development
- Use the HTTPS URL for any local testing with VAPI or n8n HTTP Request nodes
- Note: Not strictly needed if n8n Cloud handles all VAPI webhooks — only required if FastAPI needs to be reachable from external services

---

## Phase 1: Project Foundation

### Step 1: File Structure
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
    ├── lookup-caller.json           # Exported n8n workflow
    ├── log-interaction.json         # Exported n8n workflow
    └── end-of-call-report.json      # Post-call reliable logging workflow
scripts/
├── happy-path-script.md     # Exact caller script for demo recording
└── error-path-script.md     # Exact caller script for demo recording
.claude/
├── commands/
│   ├── vapi.md            # Custom VAPI CLI skill
│   ├── airtable.md        # Custom Airtable CLI skill
│   ├── init-docs.md       # (existing)
│   └── update-docs.md     # (existing)
└── skills/
    └── excalidraw-diagram/  # Excalidraw rendering skill
tests/
├── conftest.py
├── test_phone_normalize.py  # Phone normalization tests
└── test_vapi_envelope.py    # Tests VAPI envelope → extracted fields parsing logic (standalone Python, replicates n8n Code node logic)
diagrams/
├── conversation-flow.excalidraw   # Conversation state machine diagram
└── architecture.excalidraw        # System architecture diagram
.env.example
.gitignore                           # .env, __pycache__/, .venv/, node_modules/, *.pyc
requirements.txt
```

### Step 2: Dependencies
- `requirements.txt`: fastapi, uvicorn, phonenumbers, pydantic-settings, httpx, pytest
- `.env.example`: `AIRTABLE_API_KEY`, `AIRTABLE_BASE_ID`, `AIRTABLE_CUSTOMERS_TABLE`, `AIRTABLE_INTERACTIONS_TABLE`, `VAPI_API_KEY`, `VAPI_SECRET` (shared secret for webhook authentication)

---

## Phase 2: Airtable Setup

### Step 3: Create Airtable Base
**Customers table**:
| Field | Type | Notes |
|-------|------|-------|
| first_name | Single line text | |
| last_name | Single line text | |
| phone_number | Single line text | E.164 format (+15551234567). Use "Single line text" not "Phone" — Airtable's Phone type is cosmetic and may format inconsistently. Exact string match is needed for lookup formulas (e.g., `{phone_number} = '+15551234567'`), so consistent E.164 storage is critical. |
| claim_number | Single line text | Unique claim ID (e.g., CLM-001) — used for re-verification |
| claim_status | Single select | approved / pending / requires_documentation |
| claim_details | Long text | |

**Interactions table**:
| Field | Type | Notes |
|-------|------|-------|
| caller_name | Single line text | |
| phone_number | Single line text | E.164 format |
| summary | Long text | |
| sentiment | Single select | positive / neutral / negative |
| timestamp | Date (w/ time) | ISO 8601 |
| vapi_call_id | Single line text | Source: extracted from `call.id` in VAPI webhook envelope |

Populate Customers with 3-5 sample rows. Requirements:
- At least one row per `claim_status` (approved, pending, requires_documentation)
- All phone numbers in E.164 format (e.g., +15551234567)
- Each row must have a unique `claim_number` (e.g., CLM-001, CLM-002)
- The `requires_documentation` row **must** have `claim_details` populated with specific document requirements (e.g., "Please provide a copy of the police report and two photos of the damage") — the agent references this field when telling the caller what's needed
- Include at least two rows with the same `last_name` to test multi-match disambiguation

Verify with `/airtable` skill.

---

## Phase 3: n8n Workflows

Per-tool `server.url` handles tool call webhooks (lookup-caller, log-interaction). The top-level `serverUrl` handles all other webhook types (end-of-call-report). See Architecture Diagram B for routing details.

**VAPI envelope handling** (critical): n8n webhook receives the full VAPI payload. Use a Code node or Set node to extract `message.toolCallList[0].function.arguments` and format the response as `{"results": [{"toolCallId": "...", "result": "..."}]}`.

**Webhook authentication**: Every n8n workflow must validate the `X-Vapi-Secret` header (sent by VAPI with each request, configured via VAPI's `server.secret` field). Two options:
- **Option A (simpler)**: Use n8n's built-in "Header Auth" credential type on the Webhook node — set header name to `x-vapi-secret` and expected value to the shared secret. n8n rejects unauthorized requests automatically (no Code node needed).
- **Option B**: Add a Code node after the Webhook trigger that checks `$input.first().json.headers['x-vapi-secret']` against the secret and throws if invalid.
Prefer Option A for simplicity.

### Step 4: Workflow — Lookup Caller
```
[Webhook Trigger: /lookup-caller]
    → [Auth: validate X-Vapi-Secret header]
    → [Extract call.id as vapi_call_id]
    → [Extract toolCallId from message.toolCallList[0].id] ← must echo back in response
    → [Parse toolCallList arguments (phone_number, last_name, claim_number)]
    → [Validate: at least one param is non-empty — if all empty, return error response]
    → [Code node: normalize phone via regex or HTTP Request to FastAPI /normalize-phone]
    → [Airtable: Search Records (Customers)]
        Filter by: phone_number (primary) OR last_name OR claim_number
    → [IF single match]: Format result with first_name, last_name, claim_number, claim_status, claim_details
    → [IF multiple matches (e.g., last_name search)]:
        Format result: {"found": true, "multiple": true, "matches": [{first_name, last_name}, ...]}
        (LLM will ask caller to confirm first name to disambiguate)
    → [IF not found]: Format result: {"found": false, "message": "No matching record"}
    → [Error branch ⚠️]: On Airtable failure →
        Format result: {"found": false, "error": true, "message": "System temporarily unavailable"}
    → [Respond to Webhook: {"results": [{"toolCallId": "<extracted>", "result": "<formatted result>"}]}]
```

The lookup supports three search modes for re-verification:
1. `phone_number` — primary lookup (initial caller identification)
2. `last_name` — fallback verification (may return multiple matches — LLM asks for first name to disambiguate)
3. `claim_number` — second fallback verification (unique, always returns 0 or 1 match)

### Step 5: Workflow — Log Interaction
```
[Webhook Trigger: /log-interaction]
    → [Auth: validate X-Vapi-Secret header]
    → [Extract call.id as vapi_call_id]
    → [Extract toolCallId from message.toolCallList[0].id] ← must echo back in response
    → [Parse toolCallList arguments (caller_name, phone_number, summary, sentiment)]
    → [Set timestamp (ISO 8601, UTC)]
    → [Airtable: Create Record (Interactions)]
        Fields: caller_name, phone_number, summary, sentiment, timestamp, vapi_call_id
    → [Error branch ⚠️]: On Airtable failure →
        Format result: {"success": false, "error": "Failed to save interaction record"}
    → [Respond to Webhook: {"results": [{"toolCallId": "<extracted>", "result": "{\"success\": true, \"record_id\": \"...\"}"}]}]
```

### Step 5b: Workflow — End-of-Call Report (Reliable Logging Fallback)
```
[Webhook Trigger: /end-of-call-report (receives all serverUrl webhooks)]
    → [Auth: validate X-Vapi-Secret header]
    → [Filter: message.type === "end-of-call-report"]
    → [Wait node: 10 seconds] ← prevents race condition with log-interaction (see note below)
    → [Extract: call.id, message.analysis.summary, caller phone from message.call]
    → [Derive sentiment from message.analysis or default to "neutral"]
    → [Airtable: Search Interactions WHERE vapi_call_id = call.id]
    → [IF record exists]: Skip (LLM tool call already logged it) → [End]
    → [IF no record]: Create Interaction record from available call data
    → [Error branch ⚠️]: Log error silently (no response needed — VAPI doesn't wait)
```

**Race condition note**: When a call ends, both `log_interaction` (LLM tool call) and `end-of-call-report` (VAPI webhook) can fire near-simultaneously. Without the delay, both check Airtable, both see "no record," and both create a row — producing a duplicate. The 10-second Wait node ensures `log_interaction` completes first. Production fix: use a database with a unique constraint on `vapi_call_id` so the second write is rejected automatically.

**Why this workflow matters**: If the caller hangs up abruptly before the LLM calls `log_interaction`, this webhook still fires. It guarantees every call is logged regardless of how it ends.

Export all three workflows as JSON to `n8n/workflows/` for version control.

---

## Phase 4: FastAPI Utility Layer

### Step 6: Phone Normalization Service (`app/services/phone.py`)
- `normalize_phone(raw: str, default_region: str = "US") -> str` — parse with `phonenumbers.parse(raw, default_region)`, return E.164 format
- Default region `"US"` is critical: callers will say "555-123-4567" without country code, and `phonenumbers.parse()` requires either E.164 input or a default region to succeed
- Handle: various input formats (555-123-4567, (555) 123-4567, +1 555 123 4567, five five five..., etc.)
- Raise `ValueError` for unparseable numbers

### Step 7: Schemas (`app/schemas.py`)
- `NormalizePhoneRequest(raw_phone: str)` / `NormalizePhoneResponse(e164: str, valid: bool)`

### Step 8: App (`app/main.py`)
- `GET /health` — returns `{"status": "ok"}`
- `POST /normalize-phone` — accepts raw phone string, returns E.164 via phonenumbers lib
- CORS middleware enabled
- No VAPI webhook endpoints (n8n handles all webhooks)
- No `X-Vapi-Secret` validation needed (FastAPI is not exposed to VAPI directly)

---

## Phase 5: VAPI Agent Configuration

### Step 9: System Prompt (`vapi/system_prompt.md`)

Full conversational flow for GPT-4o:

**1. Greeting**
- The greeting ("Thank you for calling Observe Insurance. My name is Sarah. How can I help you today?") is delivered automatically via VAPI's `firstMessage` config. Do NOT repeat it. Wait for the caller to respond, then ask for the phone number associated with their account if they haven't already stated their reason for calling.

**2. Authentication & Identity Verification**
- The caller will speak their phone number aloud. Extract the digits regardless of how they're transcribed by STT (spoken words like "five five five", digits, dashes, or any mix). Pass whatever you receive to the `lookup_caller` tool — the system will normalize it.
- Call `lookup_caller` tool with the provided phone number
- **If found (single match)**: "Am I speaking with {first_name} {last_name}?"
  - **If confirmed**: Proceed to claim status
  - **If denied** (re-verification flow):
    - "I apologize for the confusion. Could you please provide your last name so I can look up your account?"
    - Call `lookup_caller` with `last_name` parameter
    - If single match found, re-confirm identity: "Am I speaking with {first_name} {last_name}?"
    - If multiple matches returned: "I found a few accounts under that name. Could you confirm your first name?" Use the first name to match against the returned list.
    - If no match: "Could you provide your claim number instead? It usually starts with CLM."
    - Call `lookup_caller` with `claim_number` parameter
    - If still no match: "I'm unable to verify your identity at this time. I'll arrange for a human representative to call you back within 24 hours. They'll be able to assist you further."
- **If not found**: "I wasn't able to find an account associated with that phone number. Let me arrange for a representative to follow up with you. You should receive a callback within 24 hours."

**3. Claim Status Handling**
- **Approved**: "Great news — your claim has been approved! [claim_details]. Is there anything else you'd like to know about your claim?"
- **Pending**: "Your claim is currently under review. Our team is working on it and you should receive an update soon. [claim_details if available]."
- **Requires documentation**: "Your claim requires some additional documentation before we can proceed. You can upload the documents through our online portal, or email them directly to support@observeinsurance.com. Would you like me to go over what's needed?"

**4. FAQ Knowledge Base**
```
=== FAQ KNOWLEDGE BASE ===
Q: What are your office hours?
A: Our office hours are Monday through Friday, 9 AM to 5 PM Eastern Time.

Q: What is your mailing address?
A: Our mailing address is 123 Insurance Way, Suite 400, Hartford, CT 06103.

Q: How do I start a new claim?
A: You can start a new claim by calling us during business hours, visiting our website at observeinsurance.com/claims, or emailing claims@observeinsurance.com.

Q: What is the general claims process?
A: After you submit a claim, our team reviews the documentation within 3-5 business days. You'll receive updates via email and can check status anytime by calling us. If additional documentation is needed, we'll reach out with specific instructions.
=== END FAQ ===
```
Production note: In a production system, this would be replaced with a vector knowledge base retrieval tool for scalable FAQ management.

**5. Escalation & Safety Behavior**
- **Representative request**: "Absolutely, I'll arrange for a representative to call you back. Can I confirm the best number to reach you? You should hear from someone within 24 hours."
  - Production enhancement: Use VAPI's `forwardingPhoneNumber` to do a live warm transfer instead of scheduling a callback
- **Emergency**: "If this is an emergency, please hang up and dial 911 immediately. Your safety is our top priority."
- **Off-topic**: "I appreciate your question, but I'm best equipped to help with insurance claims and account inquiries. Is there anything related to your claim I can assist with?"

**6. Wrap-up & Logging**
- Summarize what was discussed
- If the caller referenced their claim, mention their claim number (e.g., "For your records, your claim number is CLM-001") so they can use it for future calls
- Call `log_interaction` with: caller_name (if authenticated, otherwise "Unknown"), phone_number (if the caller provided one — omit if they never gave a number), summary of conversation, sentiment
- "Thank you for calling Observe Insurance. Have a wonderful day!"
- After the caller confirms they have no more questions and you've said goodbye, use the `endCall` function to gracefully end the call. Do NOT end the call while the caller is still speaking or asking questions.
- Note: The `log_interaction` tool call is best-effort. The `end-of-call-report` webhook provides reliable fallback logging.

**7. Sentiment Classification Rules**
```
When classifying call sentiment for the log_interaction tool:
- POSITIVE: Caller expressed thanks, satisfaction, relief, or positive feedback
- NEGATIVE: Caller expressed frustration, anger, dissatisfaction, or requested escalation due to unhappiness
- NEUTRAL: Informational queries, standard claim checks, no strong emotion either way
```

**8. Error Handling**
- If any tool call returns an error or times out: "I'm having a little trouble accessing our records right now. Let me arrange for someone to call you back with that information. Is there anything else I can help with in the meantime?"

### Step 10: Assistant Config (`vapi/assistant_config.json`)
```json
{
  "name": "Observe Insurance Claims Assistant",
  "model": {
    "provider": "openai",
    "model": "gpt-4o",
    "temperature": 0.3,
    "systemPrompt": "<contents of system_prompt.md>"
  },
  "voice": {
    "provider": "11labs",
    "voiceId": "<chosen-voice-id>"
  },
  "transcriber": {
    "provider": "deepgram",
    "model": "nova-2"
  },
  "firstMessage": "Thank you for calling Observe Insurance. My name is Sarah. How can I help you today?",
  "endCallFunctionEnabled": true,
  "silenceTimeoutSeconds": 30,
  "maxDurationSeconds": 600,
  "responseDelaySeconds": 0.5,
  "backgroundDenoisingEnabled": true,
  "hipaaEnabled": true,
  "endCallMessage": "Thank you for calling Observe Insurance. Goodbye!",
  "serverUrl": "<n8n-cloud-base-webhook-url>",
  "analysisPlan": {
    "summaryPlan": {
      "enabled": true
    },
    "structuredDataPlan": {
      "enabled": true,
      "schema": {
        "type": "object",
        "properties": {
          "callReason": { "type": "string" },
          "authenticated": { "type": "boolean" },
          "claimStatus": { "type": "string" },
          "escalated": { "type": "boolean" }
        }
      }
    }
  },
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "lookup_caller",
        "description": "Look up a caller's account by phone number, last name, or claim number. Use phone_number for initial lookup. Use last_name or claim_number for re-verification if the caller denies their identity.",
        "parameters": {
          "type": "object",
          "properties": {
            "phone_number": {
              "type": "string",
              "description": "Caller's phone number (any format — will be normalized)"
            },
            "last_name": {
              "type": "string",
              "description": "Caller's last name (for re-verification)"
            },
            "claim_number": {
              "type": "string",
              "description": "Caller's claim number (for re-verification)"
            }
          }
        }
      },
      "server": { "url": "<n8n-lookup-webhook-url>", "secret": "<VAPI_SECRET>", "timeoutSeconds": 10 },
      "async": false
    },
    {
      "type": "function",
      "function": {
        "name": "log_interaction",
        "description": "Log a summary of the call interaction at the end of the conversation",
        "parameters": {
          "type": "object",
          "properties": {
            "caller_name": {
              "type": "string",
              "description": "Caller's full name if authenticated, otherwise 'Unknown'"
            },
            "phone_number": {
              "type": "string",
              "description": "Caller's phone number"
            },
            "summary": {
              "type": "string",
              "description": "Brief summary of the conversation and outcome"
            },
            "sentiment": {
              "type": "string",
              "enum": ["positive", "neutral", "negative"],
              "description": "Overall caller sentiment"
            }
          },
          "required": ["summary", "sentiment"]
        }
      },
      "server": { "url": "<n8n-log-webhook-url>", "secret": "<VAPI_SECRET>", "timeoutSeconds": 10 },
      "async": false
    }
  ]
}
```

**Implementation notes for assistant config:**
- **`systemPrompt` field**: VAPI may use `messages: [{role: 'system', content: '...'}]` instead of `systemPrompt` depending on API version. Verify against VAPI docs during implementation.
- **`lookup_caller` has no `required` array**: All three params are optional because the tool serves three search modes (phone, last_name, claim_number). The n8n Code node must validate that at least one parameter is provided and return an error if all three are empty.
- **`async: false`**: Ensures the LLM waits for the tool result before continuing to speak. Without this, the agent would keep talking while the Airtable lookup is still in progress.
- **`server.timeoutSeconds: 10`**: Explicit timeout so VAPI doesn't hang indefinitely on a slow n8n/Airtable response. The system prompt's error handling (Section 8) covers the timeout case.

Create via VAPI CLI: `vapi assistants create` or `/vapi` skill.

---

## Phase 6: Diagrams

### Step 11: Conversation State Machine Diagram
Use the Excalidraw skill to create `diagrams/conversation-flow.excalidraw` showing:
- **States**: Greeting → Ask Phone → Lookup → Identity Confirmation → Re-verification (last name) → Re-verification (claim number) → Claim Status → FAQ → Escalation → Wrap-up → End
- **Transitions**: labeled with conditions (confirmed/denied/not-found/error/timeout)
- **Color coding**: Happy path in green, error/escalation path in red, re-verification in yellow
- This is the **conversational flow chart** the problem statement explicitly asks for

### Step 12: System Architecture Diagram
Use the Excalidraw skill to create `diagrams/architecture.excalidraw` showing:
- Components: VAPI (STT/LLM/TTS), n8n Cloud, FastAPI, Airtable
- Integration arrows with protocol labels (HTTPS webhooks, REST API)
- All three n8n workflows visible
- **Monitoring touchpoints** annotated with icons:
  - 📊 VAPI Dashboard (call metrics)
  - 📋 n8n Execution Logs (workflow health)
  - 📝 Airtable write tracking (via n8n error branches)

---

## Phase 7: Tests, Deployment & Demos

### Step 13: Tests (Phase 7 continues)
- **Phone normalization**: various formats (+1, parens, dashes, spaces), international numbers, invalid input
- **VAPI envelope parsing**: standalone Python tests that replicate the n8n Code node logic — mock VAPI webhook payloads → verify correct extraction of `call.id`, `toolCallList` arguments, and VAPI results response formatting
- `pytest tests/` with fixtures in `conftest.py`

### Step 14: Deployment
- **n8n**: Use n8n Cloud Starter plan — already deployed with public HTTPS URLs, unlimited executions. No infra management needed.
- **FastAPI**: Run locally with ngrok for demo. Optionally deploy to AWS Lambda via Mangum adapter.
- **VAPI**: Provision phone number via CLI (`vapi phone-numbers create`), attach assistant.
- Production recommendation (for write-up only): n8n on ECS Fargate with Postgres, FastAPI on Lambda, Airtable replaced with a production database.

### Step 15: Demo Recordings

**Happy Path Script:**
```
1. Agent: "Thank you for calling Observe Insurance. My name is Sarah. How can I help you today?"
2. Caller: "Hi, I'd like to check on my insurance claim."
3. Agent: "Of course, I'd be happy to help. Could you provide the phone number associated with your account?"
4. Caller: "Sure, it's 555-123-4567."
   (Airtable sample row: phone_number=+15551234567, first_name=John, last_name=Smith, claim_number=CLM-001, claim_status=approved)
5. Agent: [calls lookup_caller] "Am I speaking with John Smith?"
6. Caller: "Yes, that's me."
7. Agent: "Great, thank you for confirming, John. Your claim CLM-001 has been approved! [details]. Is there anything else?"
8. Caller: "Yes — what are your office hours?"
9. Agent: "Our office hours are Monday through Friday, 9 AM to 5 PM Eastern Time."
10. Caller: "Thanks, that's all I needed."
11. Agent: [calls log_interaction] "You're welcome, John. Thank you for calling Observe Insurance. Have a wonderful day!"
[Verify: Interactions table has new record with positive sentiment, vapi_call_id populated]
```

**Error Path Script (Identity Denial + Re-verification):**
```
1. Agent: "Thank you for calling Observe Insurance. My name is Sarah. How can I help you today?"
2. Caller: "I want to check my claim status."
3. Agent: "Could you provide the phone number associated with your account?"
4. Caller: "555-123-4567."
5. Agent: [calls lookup_caller] "Am I speaking with John Smith?"
6. Caller: "No, that's not me."
7. Agent: "I apologize for the confusion. Could you provide your last name?"
8. Caller: "It's Johnson."
9. Agent: [calls lookup_caller with last_name] "I wasn't able to find a match. Could you provide your claim number?"
10. Caller: "I don't have it handy."
11. Agent: "No problem. I'll arrange for a representative to call you back within 24 hours to assist you. Is there anything else?"
12. Caller: "No, thanks."
13. Agent: [calls log_interaction] "Thank you for calling. Have a great day."
[Verify: Interactions table has record with neutral sentiment, summary mentions failed verification]
```

**Error Path Script (Number Not Found + Abrupt Hangup):**
```
1. Agent: "Thank you for calling Observe Insurance. My name is Sarah. How can I help you today?"
2. Caller: "Yeah, I need to check on a claim."
3. Agent: "Of course. Could you provide the phone number associated with your account?"
4. Caller: "It's 555-999-0000."
   (This number does NOT exist in the Customers table)
5. Agent: [calls lookup_caller — returns not found] "I wasn't able to find an account associated with that phone number. Let me arrange for a representative to follow up with you. You should receive a callback within 24 hours."
6. Caller: *hangs up abruptly without responding*
   (Agent never gets to call log_interaction)
[Verify: After ~15 seconds, end-of-call-report webhook fires → n8n Workflow 3 creates Interaction record with caller_name="Unknown", sentiment="neutral", summary from VAPI's analysisPlan]
```

---

## Phase 8: Technical Write-Up

### Architecture Choices
- Why VAPI (managed telephony + STT/TTS/LLM orchestration, no WebSocket infra needed)
- Why n8n Cloud (visual workflows, built-in Airtable nodes, Starter plan with unlimited executions)
- Why GPT-4o (best balance of reasoning + speed for conversational agent)
- Why Airtable (quick setup, API-friendly, schema visible to evaluators)
- Why FastAPI as utility only (separation of concerns — n8n for integration, Python for logic)

### Production Scaling Considerations
What breaks first at scale and how to address it:
- **Airtable API rate limits** (5 requests/second per base): Replace with PostgreSQL on AWS RDS. Add Redis cache layer for customer lookups (most callers are repeat — cache hit rate will be high).
- **n8n single-threaded workflow execution**: n8n Cloud handles concurrency via queue mode, but for 100+ concurrent calls, migrate to self-hosted n8n on ECS Fargate with multiple workers behind a load balancer and Postgres-backed queue.
- **VAPI concurrent call limits**: Varies by plan (Growth plan supports 100+ concurrent). Monitor via VAPI dashboard and upgrade proactively.
- **LLM latency under load**: GPT-4o has variable latency. Add a timeout + fallback: if lookup_caller doesn't respond within 3 seconds, apologize and offer to call back. Consider GPT-4o-mini as a lower-latency alternative if conversation quality permits.

### Per-Call Cost Estimate
Break down for a typical 3-minute call (research exact pricing during implementation — these are ballpark):
| Component | Rate | Est. Cost (3 min) |
|-----------|------|--------------------|
| VAPI platform fee | ~$0.05/min | ~$0.15 |
| Deepgram Nova-2 STT | ~$0.0059/min | ~$0.02 |
| ElevenLabs TTS | ~$0.30/1K chars | ~$0.15 |
| GPT-4o tokens (input + output) | ~$2.50/$10 per 1M tokens | ~$0.03 |
| **Total per call** | | **~$0.35** |

Fixed costs (not per-call):
- n8n Cloud Starter plan: ~$24/month
- Airtable: Free tier (1,000 records, 5 API calls/sec)

Note: Verify these rates against current pricing pages during the write-up phase. VAPI may bundle STT/TTS costs depending on plan.

### HIPAA Considerations
- `hipaaEnabled: true` in VAPI config — enables BAA-eligible mode
- Airtable is NOT HIPAA-compliant for production — would need to migrate to a compliant database (e.g., AWS RDS with encryption at rest)
- Note: For this demo, no real PII/PHI is used

### Problem Solving & Debugging
- One technical challenge encountered and how it was solved

### What I'd Optimize With One More Week
- Knowledge base RAG instead of hardcoded FAQ
- Redis caching for Airtable lookups (reduce latency)
- Live call transfer via VAPI's `forwardingPhoneNumber` instead of callback scheduling
- Voice biometrics for caller authentication
- Multi-language support (VAPI + Deepgram support this)
- Automated testing with VAPI's test call API
- CI/CD pipeline for system prompt version management

### Data & Metrics Evaluation
**Metrics to track:**
- Containment rate (% of calls resolved without escalation)
- Average handle time (AHT)
- CSAT (post-call survey integration)
- Escalation rate
- Authentication success rate (first attempt vs. re-verification)
- Tool call latency (lookup_caller, log_interaction)

**Using data to improve:**
- Analyze calls where re-verification fails → improve prompt instructions or add more verification methods
- Track AHT trends → identify system prompt sections that cause unnecessary verbosity
- Monitor escalation reasons → add FAQ entries for common escalation triggers

**Example — diagnosing a containment drop:**
1. Pull weekly containment rate from VAPI dashboard
2. Filter escalated calls by reason (via Interactions table summary)
3. Identify pattern (e.g., 40% of escalations are "caller asked about claim payment date" — not in FAQ)
4. Add claim payment timeline to FAQ knowledge base
5. Monitor containment rate over next week to verify improvement

---

## Verification
1. `/airtable` skill — verify base schema, sample data (claim_number, claim_details populated, two rows with same last_name)
2. `/vapi` skill — verify assistant created with correct tools, `endCallFunctionEnabled`, `silenceTimeoutSeconds`, `hipaaEnabled`, `analysisPlan`
3. n8n webhook auth — send request without `X-Vapi-Secret` header → verify 401 rejection
4. n8n Workflow 1 (lookup-caller) — test: phone lookup, last_name lookup (single + multi-match), claim_number lookup
5. n8n Workflow 2 (log-interaction) — test with sample payload, verify Airtable write with vapi_call_id
6. n8n Workflow 3 (end-of-call-report) — test deduplication: send report for call already logged → should skip
7. n8n error branches — simulate Airtable timeout → verify error response format
8. `uvicorn app.main:app` — health check returns 200, `/normalize-phone` handles "5551234567" with default_region=US
9. `pytest tests/` — all tests pass (phone normalization + VAPI envelope parsing)
10. Call VAPI phone number — happy path (follow script) → verify Airtable log + claim_number in response
11. Call VAPI phone number — identity denial path (follow script) → verify re-verification + multi-match + log
12. Call VAPI phone number — number not found path → verify end-of-call-report logs it (with analysis.summary populated)
13. Call VAPI phone number — test endCall: verify agent hangs up gracefully after goodbye
14. Both Excalidraw diagrams render correctly (conversation flow + architecture)
