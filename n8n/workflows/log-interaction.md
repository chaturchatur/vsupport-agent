# Workflow 2: Log Interaction

**Workflow ID:** `fS60qOqtDuWyIReD` | **Webhook:** `POST /webhook/log-interaction` | **7 nodes, branching pipeline**

```
Webhook → Parse Envelope → Insert Interaction ─┬─ (success) → Format Success → Respond Success
                                                └─ (error)   → Format Error   → Respond Error
```

---

## Node 1: Webhook (trigger)

- Listens for `POST /webhook/log-interaction`
- **Auth:** Header Auth — validates `x-vapi-secret` header against the stored credential (`PQXagW16N8ErYDM7`)
- Uses `responseNode` mode — the response is sent explicitly by one of the two Respond nodes (not auto-returned)

**Who calls it:** VAPI's GPT-4o LLM issues a `log_interaction` tool call at the end of every conversation, just before saying goodbye. The system prompt (Section 6: Wrap-up & Logging) instructs GPT-4o to call this tool with `caller_name`, `phone_number`, `summary`, and `sentiment`.

---

## Node 2: Parse Envelope (Code node — JS)

This node does two things:

### a) Unwrap the VAPI envelope

```
body.message.toolCallList[0] → extracts function arguments
body.message.call.id          → extracts vapi_call_id
```

Arguments expected: `caller_name`, `phone_number`, `summary`, `sentiment` (all from GPT-4o's tool call)

**Key detail:** The `toolCallId` is **not** extracted here. Unlike Lookup Caller (which passes `toolCallId` through the pipeline), this workflow only extracts the DB columns at this stage. The `toolCallId` is retrieved later by Format Success/Error directly from the Webhook node's original body via `$('Webhook').first().json.body`. This avoids threading the ID through the Supabase node.

### b) Sanitize and default the fields

| Field | Logic |
|-------|-------|
| `caller_name` | Trims whitespace, defaults to `"Unknown"` if missing |
| `phone_number` | Trims whitespace, defaults to empty string |
| `summary` | Trims whitespace, defaults to empty string |
| `sentiment` | Validates against `['positive', 'neutral', 'negative']` — defaults to `'neutral'` if the LLM sends anything unexpected |
| `timestamp` | Server-generated `new Date().toISOString()` — not from the LLM |
| `vapi_call_id` | Extracted from `message.call.id` (the VAPI call object, not the tool call) |

**Output:** A single JSON object with exactly these 6 fields — maps 1:1 to the `interactions` table columns.

---

## Node 3: Insert Interaction (Supabase node)

- **Operation:** `create` on `interactions` table
- **Data mapping:** `autoMapInputData` — the 6 fields from Parse Envelope are auto-mapped to table columns by name (no manual field mapping needed)
- **`onError: continueErrorOutput`** — this is the critical setting. Instead of halting the workflow on failure, the node routes to its **second output** (error branch). Success goes to the first output. This creates the branching pipeline.
- Connects via REST API (PostgREST over HTTPS), not the Postgres wire protocol
- Uses the Supabase credential `Zhs4bVeCvuPXCQkF`

**What can cause an error?** The `interactions` table has a UNIQUE constraint on `vapi_call_id`. If `log_interaction` fires twice for the same call (e.g., GPT-4o retries the tool call), the second INSERT will violate the constraint and route to the error branch. This is one of two dedup mechanisms — the End-of-Call Report workflow is the other.

---

## Node 4a: Format Success (Code node — JS)

Runs when the Supabase INSERT succeeds (first output of Insert Interaction).

Retrieves `toolCallId` by reaching back to the original Webhook body:

```js
const toolCallId = body.message?.toolCallList?.[0]?.id
                || body.message?.toolCalls?.[0]?.id || '';
```

**Why two paths?** VAPI has sent both `toolCallList` and `toolCalls` in different API versions. Checking both provides forward/backward compatibility.

Reads the inserted record's `id` from the Supabase node's output and returns:

```json
{
  "results": [{
    "toolCallId": "call_abc123",
    "result": "{\"success\":true,\"record_id\":\"42\"}"
  }]
}
```

---

## Node 4b: Format Error (Code node — JS)

Runs when the Supabase INSERT fails (second output of Insert Interaction).

Same `toolCallId` retrieval logic as Format Success. Returns a generic error:

```json
{
  "results": [{
    "toolCallId": "call_abc123",
    "result": "{\"success\":false,\"error\":\"Failed to save interaction record\"}"
  }]
}
```

**Design choice:** The error message is intentionally generic. The actual Supabase error (e.g., unique constraint violation) is not surfaced to VAPI/GPT-4o — the LLM doesn't need to know why it failed, only that it failed. GPT-4o's error handling (Section 8 of the system prompt) will say "I'm having a little trouble accessing our records right now" regardless.

---

## Node 5a: Respond Success (Respond to Webhook)

Sends the Format Success JSON back to VAPI as the HTTP response body. GPT-4o receives confirmation that the log was saved and proceeds with the goodbye message.

---

## Node 5b: Respond Error (Respond to Webhook)

Sends the Format Error JSON back to VAPI. GPT-4o sees `success: false` and triggers its error handling script.

---

## How this differs from Lookup Caller

| Aspect | Lookup Caller | Log Interaction |
|--------|---------------|-----------------|
| **Direction** | Read (getAll) | Write (create) |
| **Pipeline shape** | Linear (5 nodes) | Branching (7 nodes — success/error split) |
| **toolCallId routing** | Threaded through the pipeline | Retrieved from Webhook node at format time via `$('Webhook')` |
| **Error handling** | No branching — errors surfaced in Format Result | `onError: continueErrorOutput` creates a dedicated error branch |
| **Phone normalization** | JS E.164 normalization + PostgREST filter building | None — phone is stored as-is from GPT-4o |
| **Dedup concern** | N/A (read-only) | UNIQUE constraint on `vapi_call_id` prevents duplicate logs |

---

## FAQ

### Why do we have both Log Interaction and End-of-Call Report if they both write to `interactions`?

They serve different purposes, fire at different times, and catch different scenarios.

**Log Interaction** is an LLM-initiated tool call. GPT-4o explicitly calls `log_interaction` during the conversation (right before goodbye), passing a conversation-aware summary and sentiment. It depends on the LLM choosing to call the tool — if the caller hangs up abruptly, the call drops, or GPT-4o hits max tokens / times out, the tool call never happens and no log gets written.

**End-of-Call Report** is a VAPI platform event. VAPI sends it automatically for *every* call after hangup, regardless of how the call ended. It includes VAPI's own `analysisPlan` output (structured data like `callReason`, `authenticated`, `claimNumber`, `escalated`) — metadata the LLM-generated log doesn't have.

Think of it as:
- **Log Interaction** = the agent's own notes ("here's what I think happened")
- **End-of-Call Report** = the platform's safety net ("here's what actually happened, with structured metadata")

Both write to `interactions` with a UNIQUE constraint on `vapi_call_id`. Whichever fires first wins; the second is silently deduplicated. In the happy path, `log_interaction` fires first (during the call) and the end-of-call report's INSERT gets rejected by the constraint. In the drop/crash path, only the end-of-call report writes.

They're **belt and suspenders** — the LLM path gives a richer summary while the call is live, the platform path guarantees every call is logged even when the LLM path fails.

### Why is `toolCallId` fetched from the Webhook node instead of passed through Parse Envelope?

Parse Envelope's job is to produce a clean object that maps 1:1 to the `interactions` table columns. If `toolCallId` were included, the Supabase node (with `autoMapInputData`) would try to insert it as a column — which doesn't exist in the table, causing an error.

Rather than adding manual field exclusion, the workflow uses n8n's `$('Webhook')` expression to reach back to the original request body. This keeps Parse Envelope's output clean and the Supabase node's auto-mapping simple.

### What happens if `log_interaction` is called twice for the same call?

The `interactions` table has a UNIQUE constraint on `vapi_call_id`. The first INSERT succeeds (→ Format Success → Respond Success). The second INSERT violates the constraint (→ Format Error → Respond Error). GPT-4o gets `success: false` but handles it gracefully — the caller never knows.

This is the same dedup strategy used by the End-of-Call Report workflow, just with different error routing (`continueErrorOutput` here vs. `continueRegularOutput` there).

### Why does Parse Envelope default sentiment to `'neutral'`?

GPT-4o's tool call includes a `sentiment` enum (`positive`/`neutral`/`negative`), but LLMs can occasionally hallucinate values outside the enum. The `interactions` table has a CHECK constraint on sentiment — inserting an invalid value would cause a Supabase error. The validation in Parse Envelope acts as a guardrail, ensuring the INSERT never fails due to bad sentiment values.

### Why is `timestamp` server-generated instead of coming from the LLM?

Trust boundary. The n8n server's clock is authoritative — it reflects when the interaction was actually logged, not when GPT-4o decided to call the tool (which could be delayed by retries or latency). This also prevents the LLM from hallucinating a timestamp.

---

## End-to-end example

1. Caller says: "That's all I needed, thanks!"
2. GPT-4o summarizes the conversation and issues:
   ```
   log_interaction({
     caller_name: "Sarah Johnson",
     phone_number: "415-555-1234",
     summary: "Caller checked status of claim CLM-2024-001, confirmed approved. No further action needed.",
     sentiment: "positive"
   })
   ```
3. VAPI POSTs the tool-call envelope to n8n (includes `message.call.id` = the VAPI call UUID)
4. Parse Envelope extracts the 4 args + generates `timestamp` + pulls `vapi_call_id` from `message.call.id`
5. Insert Interaction writes to Supabase: `{ caller_name: "Sarah Johnson", phone_number: "415-555-1234", summary: "...", sentiment: "positive", timestamp: "2026-03-18T...", vapi_call_id: "abc-123-..." }`
6. Supabase returns the created row with `id: 42`
7. Format Success returns `{ results: [{ toolCallId: "call_xyz", result: '{"success":true,"record_id":"42"}' }] }`
8. GPT-4o receives confirmation, says "Thank you for calling Observe Insurance. Have a wonderful day!"
9. After the caller confirms goodbye, GPT-4o calls `endCall` to hang up
