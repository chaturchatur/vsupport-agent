# VAPI Assistant Config — In-Depth Notes

## File: `vapi/assistant_config.json`

This is a **template** file with `{{placeholder}}` variables resolved at deploy time by `scripts/deploy-vapi.sh`. The deployed assistant ID is `2d8ea99b-1187-4a24-a710-28e1a96af9ee`.

---

## 1. Top-Level Settings

| Field | Value | Purpose |
|-------|-------|---------|
| `name` | "Observe Insurance Claims Assistant" | Display name in VAPI dashboard |
| `firstMessage` | "Thank you for calling Observe Insurance..." | Auto-spoken greeting before LLM takes over |
| `firstMessageMode` | `"assistant-speaks-first"` | Agent speaks first — caller doesn't need to say hello |
| `endCallFunctionEnabled` | `true` | LLM can invoke a built-in `endCall` function to hang up gracefully |
| `endCallMessage` | "Thank you for calling Observe Insurance. Goodbye!" | Fallback message if call ends without LLM-driven goodbye |
| `silenceTimeoutSeconds` | `30` | Call auto-ends after 30s of silence |
| `maxDurationSeconds` | `600` | Hard cap: 10-minute max call duration |
| `responseDelaySeconds` | `1.0` | 1-second pause before the agent responds — makes it sound more natural, reduces interruption |
| `backgroundDenoisingEnabled` | `true` | Filters background noise for cleaner STT |
| `hipaaEnabled` | `true` | BAA-eligible mode — VAPI won't record or log call audio/transcripts on their side |

---

## 2. Model Configuration (`model`)

| Field | Value | Notes |
|-------|-------|-------|
| `provider` | `"openai"` | Uses OpenAI's API via VAPI |
| `model` | `"gpt-4o"` | GPT-4o for high-quality reasoning + voice latency balance |
| `temperature` | `0.3` | Low temperature — deterministic, consistent responses (important for scripted insurance flows) |
| `maxTokens` | `500` | Keeps responses concise — crucial for voice (long responses = bad UX) |
| `messages[0]` | System prompt (role: "system") | The full conversation logic is embedded here |
| `knowledgeBaseId` | `{{VAPI_KB_ID}}` | Links to a Custom Knowledge Base (Supabase Edge Function `search-faq` for FAQ RAG) |

**Key insight:** The system prompt is inlined into `model.messages[0].content` as a single string. The human-readable version is version-controlled separately at `vapi/system_prompt.md`. When deploying, the JSON-escaped version in `assistant_config.json` is what gets pushed.

---

## 3. Tools (`model.tools[]`)

Two function-calling tools, both routed to **n8n Cloud webhooks**:

### `lookup_caller`
- **Webhook:** `{{N8N_WEBHOOK_BASE_URL}}/webhook/lookup-caller`
- **Parameters:** `phone_number`, `last_name`, `claim_number` (all optional — use one at a time)
- **Timeout:** 10 seconds
- **Async:** `false` (blocking — LLM waits for result)
- **Key detail in description:** Explicitly tells the LLM to wait for a complete 10-digit number before calling. This is reinforced in both the tool description AND the system prompt to prevent premature lookups on partial STT transcriptions.

### `log_interaction`
- **Webhook:** `{{N8N_WEBHOOK_BASE_URL}}/webhook/log-interaction`
- **Parameters:** `caller_name`, `phone_number`, `summary` (required), `sentiment` (required, enum: positive/neutral/negative)
- **Timeout:** 10 seconds
- **Async:** `false`

**Architecture note:** Tools are defined inside `model.tools[]`, NOT at the assistant top level. This is a VAPI API requirement — top-level `tools` would be ignored.

**Auth:** Each tool has `server.headers["x-vapi-secret"]` set to `{{VAPI_SECRET}}`. This is how n8n validates incoming requests (Header Auth credential). VAPI does NOT support `server.secret` — only custom headers work.

---

## 4. Voice (`voice`)

| Field | Value | Notes |
|-------|-------|-------|
| `provider` | `"11labs"` | ElevenLabs |
| `voiceId` | `"sarah"` | Pre-built ElevenLabs voice — warm, professional female voice that matches the persona name |

---

## 5. Transcriber (`transcriber`)

| Field | Value | Notes |
|-------|-------|-------|
| `provider` | `"deepgram"` | Deepgram for STT |
| `model` | `"nova-2"` | Deepgram's Nova-2 model — fast, accurate |
| `language` | `"en"` | English |
| `endpointing` | `300` | 300ms of silence = end of utterance. Important tuning: too low = cuts off callers mid-sentence, too high = slow response time. 300ms is a balanced default. |

---

## 6. Server URL (top-level `server`)

```json
"server": {
  "url": "{{N8N_WEBHOOK_BASE_URL}}/webhook/vapi-server",
  "headers": { "x-vapi-secret": "{{VAPI_SECRET}}" }
}
```

This is the **assistant-level serverUrl** — receives VAPI lifecycle events, most importantly `end-of-call-report`. The n8n workflow `end-of-call-report.json` listens here and logs the final interaction to Supabase.

This is distinct from per-tool `server` URLs which handle tool-call webhooks.

---

## 7. Analysis Plan (`analysisPlan`)

Post-call analytics that VAPI runs automatically after each call:

### `summaryPrompt`
Custom prompt: "Summarize this insurance claims support call, including: caller identity, claim status discussed, actions taken, and call outcome."

### `structuredDataPlan`
Extracts structured JSON from each call:

| Field | Type | Description |
|-------|------|-------------|
| `callReason` | string | Primary call reason (claim status check, new claim, general inquiry) |
| `authenticated` | boolean | Whether the caller was verified |
| `claimNumber` | string | Claim number discussed, if any |
| `claimStatus` | enum | `approved`, `pending`, `requires_documentation`, `not_found`, or `""` |
| `escalated` | boolean | Whether escalated to human |
| `callerName` | string | Full name if identified, else `""` |

This structured data is available in the VAPI dashboard and via the API for analytics.

---

## 8. System Prompt — Conversation State Machine

The system prompt (`vapi/system_prompt.md`) defines an 8-section conversation flow:

1. **Greeting** — Auto-delivered via `firstMessage`, LLM told NOT to repeat it
2. **Authentication** — Phone lookup → name confirmation → fallback chain (last_name → claim_number → escalate). Critical guardrail: wait for complete 10-digit phone.
3. **DOB Verification (2b)** — Security gate before revealing claim info. 2 attempts allowed. Stored DOB never revealed.
4. **Claim Status** — Three branches: approved (good news), pending (under review), requires_documentation (ask about missing docs)
5. **FAQ** — Handled by Knowledge Base (RAG via pgvector). Fallback: arrange callback.
6. **Escalation & Safety** — Human handoff, 911 for emergencies, off-topic deflection
7. **Wrap-up & Logging** — Summarize call, cite claim number, call `log_interaction`, say goodbye, then `endCall`
8. **Error Handling** — Graceful degradation on tool failures, no technical details exposed

---

## 9. Deployment (`scripts/deploy-vapi.sh`)

- Reads `.env` for `N8N_WEBHOOK_BASE_URL`, `VAPI_SECRET`, `VAPI_API_KEY`, `VAPI_KB_ID`
- `sed` replaces `{{placeholders}}` → writes `assistant_config.resolved.json`
- If `VAPI_ASSISTANT_ID` is set: `PATCH /assistant/:id` (update)
- If not: `POST /assistant` (create new)
- Uses VAPI REST API directly because the VAPI CLI `create` command is interactive-only

---

## 10. Key Design Decisions & Gotchas

- **Partial phone number problem:** Both the tool description and system prompt hammer the "wait for 10 digits" rule because STT transcribes in real-time and GPT-4o was triggering `lookup_caller` on partial numbers (e.g., just the area code).
- **`server.headers` not `server.secret`:** VAPI API doesn't support `server.secret` — auth must go through custom headers. This was a gotcha discovered during development.
- **Tools inside `model.tools`:** VAPI requires tools to be nested under the model object, not at assistant top level.
- **`knowledgeBaseId` in `model`:** The KB reference goes inside `model`, not at the top level of the assistant.
- **`summaryPrompt` not `summaryPlan.prompt`:** VAPI's analysis config uses `analysisPlan.summaryPrompt` directly, not nested under a `summaryPlan` object.
- **`responseDelaySeconds: 1.0`:** Intentional 1s delay to make the agent feel less robotic and reduce cutting off callers.
- **`endpointing: 300`:** Deepgram's end-of-utterance detection tuned to 300ms — balances responsiveness vs. not interrupting.
