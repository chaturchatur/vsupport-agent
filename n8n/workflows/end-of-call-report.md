# Workflow 3: End-of-Call Report

**Workflow ID:** `oRACRgI5oTF5TSGk` | **Webhook:** `POST /webhook/vapi-server` | **19 nodes: gated pipeline + three action branches**

```
Webhook → Parse EOC Envelope → Is EOC? ─┬─ (true) → Strip Meta → Upsert Interaction → Build Outcome Patch → Merge Outcomes → Decide Actions → Route Actions
                                         └─ (false) → dropped

Route Actions (Switch, every matching output fires)
  ├─ escalation → Build Escalation Row → Insert Escalation Follow-up → Alert Configured? → Send Alert Email
  ├─ sms        → Find Customer → Build SMS → Send Claim SMS
  └─ callback   → Build Callback Row → Insert Callback Follow-up
```

It does three jobs:

1. **Safety-net logging** (unchanged): every call gets an `interactions` row even if the LLM never called `log_interaction`.
2. **Outcome persistence** (new): stores what happened on the call, so containment can be computed from data.
3. **Acting on the outcome** (new): opens follow-ups, alerts a human, texts the caller.

> **Status:** the code-node logic is unit-tested (`tests/test_post_call_outcomes.py`, `tests/test_follow_up_routing.py`). The workflow has **not** been deployed or run against a real call, a real Supabase project, SMTP or Twilio. See "Not verified" at the bottom.

---

## Node 1: Webhook (trigger)

- Listens for `POST /webhook/vapi-server`
- **Auth:** Header Auth on `x-vapi-secret` (credential `PQXagW16N8ErYDM7`)
- **`responseMode: onReceived`** (changed from `lastNode`): n8n answers `200` as soon as the request is authenticated, before any node runs.

**Why the response mode changed:** with `lastNode` the HTTP response waited for the last node. Now that Twilio, SMTP and extra database writes hang off this workflow, a slow or failing action would have delayed or failed the response. VAPI ignores the body of an end-of-call-report response, so answering immediately costs nothing and guarantees no branch can affect the webhook response.

**Who calls it:** the assistant-level `server.url` in `assistant_config.json`. VAPI sends the server messages listed in `serverMessages` here; this workflow only acts on `end-of-call-report`.

---

## Node 2: Parse EOC Envelope (Code node, JS)

### a) Check the message type

Anything that is not `end-of-call-report` returns `{ is_eoc: false }` and is dropped by the IF node.

### b) Existing fields (behaviour unchanged)

| Field | Source | Notes |
|-------|--------|-------|
| `caller_name` | `analysis.structuredData.callerName` | Falls back to `'Unknown'` |
| `phone_number` | `call.customer.number` | Caller ID from VAPI |
| `summary` | `analysis.summary` | Fallback: concatenated `artifact.messages` (500 chars), then `'No summary available'` |
| `sentiment` | `analysis.structuredData.sentiment` | Validated, defaults to `'neutral'` |
| `timestamp` | Server-generated | |
| `vapi_call_id` | `call.id` | The dedup key |

`sentiment` was read here before but was never declared in `structuredDataPlan`, so VAPI never produced it and this node always wrote `neutral`. It is now declared in the schema.

### c) Outcome fields (new)

| Column | Source | When VAPI omits it |
|--------|--------|--------------------|
| `call_reason` | `structuredData.callReason` (max 200 chars) | `null` |
| `authenticated` | `structuredData.authenticated` | `null` |
| `claim_number` | `structuredData.claimNumber`, upper-cased, must match `[A-Za-z0-9-]{3,40}` | `null` |
| `claim_status` | `structuredData.claimStatus`, must be `approved` / `pending` / `requires_documentation` / `not_found` | `null` |
| `resolved_without_human` | `structuredData.resolvedWithoutHuman` | `null` |
| `escalation_requested` | `structuredData.escalationRequested`, else the older `escalated` | `null` |
| `follow_up_needed` | `structuredData.followUpNeeded`, else the older `callbackPromised` | `null` |
| `follow_up_reason` | `structuredData.followUpReason` (max 300 chars) | `null` |
| `duration_seconds` | `message.durationSeconds`, else `endedAt - startedAt`, rounded | `null` |
| `ended_reason` | `message.endedReason`, else `call.endedReason` | `null` |
| `caller_phone_digits` | Caller ID, digits only, 10-digit numbers get a leading `1` | `null` |

**Missing booleans become `null`, never `false`.** `null` means "this call was not scored". Defaulting to `false` would count every un-analysed call as "not contained" and silently wreck the containment rate. The daily view only divides by scored calls.

`claim_number` is restricted to a strict character set because it is later placed in a PostgREST filter (Find Customer). Text extracted by an LLM from a phone call is untrusted input.

`caller_phone_digits` is not an outcome; it is what lets the Pre-Call Context workflow find "this caller's last call".

---

## Node 3: Is EOC? (IF node)

`$json.is_eoc === true` → Strip Meta. Otherwise the event is dropped.

---

## Node 4: Strip Meta (Code node, JS)

Removes `is_eoc`. The next node uses `autoMapInputData`, which sends every key as a column, so only real columns may remain. A test checks every key this workflow writes exists in migrations 001 + 007.

---

## Node 5: Upsert Interaction (Supabase node, `create`)

Unchanged: `create` on `interactions`, `autoMapInputData`, `onError: continueRegularOutput`. The UNIQUE constraint on `vapi_call_id` is still the dedup mechanism.

| Scenario | What happens here |
|----------|-------------------|
| `log_interaction` did **not** fire (dropped call) | INSERT succeeds with all columns, including outcomes |
| `log_interaction` already fired (happy path) | INSERT is rejected by the UNIQUE constraint, error swallowed |

**The second row is why nodes 6 and 7 exist.** On the happy path, which is most calls, the row was written by the LLM tool and has no outcome columns. If the workflow stopped here, outcomes would be stored only for calls that went *badly enough* for the LLM not to log them, and the containment rate would be computed on exactly the wrong sample.

---

## Node 6: Build Outcome Patch (Code node, JS)

Builds `{ vapi_call_id, <outcome columns>, caller_phone_digits }` from Strip Meta's output. It leaves out `summary`, `sentiment`, `caller_name`, `phone_number` and `timestamp`, so whatever the LLM logged during the call is kept.

Returns nothing when there is no `vapi_call_id`: without the key there is nothing safe to match on, and the rest of the workflow does not run.

---

## Node 7: Merge Outcomes (Supabase node, `update`)

- `update` on `interactions`, filter string `vapi_call_id=eq.<id>`, `autoMapInputData`
- `onError: continueRegularOutput`, `alwaysOutputData: true`
- Returns the stored row (the node always asks PostgREST for the representation)

Together, nodes 5 and 7 are an upsert: insert if new, otherwise patch the outcome columns onto the existing row. When node 5 inserted the row, this update rewrites the same values (harmless).

---

## Node 8: Decide Actions (Code node, JS)

All routing decisions are made here, in one testable place. The Switch after it only reads three booleans.

Values come from the stored row returned by Merge Outcomes, falling back to what was parsed if the update failed.

| Output | Condition |
|--------|-----------|
| `do_escalation` | `escalation_requested` is true **or** sentiment is `negative` (in the stored row or in this report) |
| `do_sms` | `resolved_without_human` **and** `authenticated` **and** a valid `claim_number` **and** Twilio is configured |
| `do_callback` | `follow_up_needed` is true |
| `send_alert` | `do_escalation` and the alert email is configured |

Sentiment is checked in both places because on the happy path the stored row carries the sentiment the LLM logged during the call, which is usually better than the post-call analysis.

**Deploy-time settings.** The top of this node holds placeholders that `scripts/deploy-n8n.sh` fills in from `.env`:

| Placeholder | `.env` key | If empty |
|-------------|-----------|----------|
| `__ALERT_EMAIL_TO__` | `ALERT_EMAIL_TO` | No alert email (follow-up row is still written) |
| `__ALERT_EMAIL_FROM__` | `ALERT_EMAIL_FROM` | Same |
| `__N8N_SMTP_CREDENTIAL_ID__` | `N8N_SMTP_CREDENTIAL_ID` | Same |
| `__TWILIO_FROM_NUMBER__` | `TWILIO_FROM_NUMBER` | No SMS, silently |
| `__N8N_TWILIO_CREDENTIAL_ID__` | `N8N_TWILIO_CREDENTIAL_ID` | Same |

Nothing environment-specific is committed: no recipient address, no sender number, no credential id. Placeholders are used instead of n8n `$vars` because custom variables are only available on n8n Cloud Pro and Enterprise.

---

## Node 9: Route Actions (Switch node)

Three rules on `do_escalation`, `do_sms`, `do_callback`, with **`allMatchingOutputs: true`**: one call can need an escalation *and* a callback. A call matching nothing ends here.

---

## Escalation branch

**Build Escalation Row** → `{ vapi_call_id, kind: 'escalation', reason }`. `reason` is `follow_up_reason` if the analysis gave one, otherwise the trigger (`caller asked for a human`, `negative sentiment`, or both).

**Insert Escalation Follow-up** → Supabase `create` on `follow_ups`. `UNIQUE (vapi_call_id, kind)` means a re-delivered report cannot open the same follow-up twice; the rejected insert is swallowed.

**Alert Configured?** → IF on `send_alert`.

**Send Alert Email** → SMTP. Recipient and sender come from Decide Actions (i.e. from `.env`), never from the workflow file. The body contains the trigger and the VAPI call id **only**: no caller name, number, claim or summary. Email is the least protected hop in the system, so the human looks the call up in the database.

The alert is sent even if the follow-up insert failed. For a human alert, sending twice is better than not sending.

---

## SMS branch

**Find Customer** → Supabase `getAll` on `customers`, `claim_number=ilike.<claim>`, limit 2.

**Build SMS** emits a message only if **all** of these hold:

- exactly one customer row came back
- its `claim_number` equals the one from the call
- its `phone_number` is valid E.164
- its `claim_status` is one of the three known statuses

The message goes **to `customers.phone_number`**: never to the caller ID and never to a number spoken on the call. The status text is taken from the database row, not from what the LLM believes it said.

**Send Claim SMS** → n8n Twilio node, `to`/`from`/`message` taken only from Build SMS.

If Twilio is not configured, `do_sms` is false and this branch never starts.

Before using this with real customers: texting someone their claim status needs their consent to be texted, and the message is not encrypted. The demo data has no opt-in column.

---

## Callback branch

**Build Callback Row** → `{ vapi_call_id, kind: 'callback', reason }` → **Insert Callback Follow-up** (same dedup as escalations).

---

## Failure isolation

| Requirement | How it is met |
|-------------|---------------|
| A branch failure must not fail the webhook response | The webhook answers on receipt, before any node runs |
| A branch failure must not fail the upsert | Every branch starts after Upsert Interaction and Merge Outcomes have finished |
| A branch failure must not stop the other branches | Every node from Decide Actions onward has `onError: continueRegularOutput` (asserted by a test) |

---

## What the data supports

```sql
SELECT * FROM v_call_outcomes_daily ORDER BY day DESC;
```

`containment_rate = contained_calls / scored_calls`, where contained means `resolved_without_human AND NOT escalation_requested`. See `supabase/migrations/007_interaction_outcomes.sql` and `grafana/`.

Caveat: these numbers are an LLM's reading of each call (VAPI's post-call analysis). They are an estimate of containment, not ground truth. Spot-check them against real calls before quoting them.

---

## Deployment order matters

Apply migrations `007` and `008` **before** deploying this workflow. Without `007`, Upsert Interaction sends columns that do not exist, the insert fails, the error is swallowed, and the safety-net row for dropped calls is lost.

---

## Not verified (needs live accounts)

- That a real end-of-call report carries `analysis.structuredData`, `durationSeconds` and `endedReason` where this node reads them. VAPI's docs show `endedReason`, `call` and `artifact` in the example payload; `analysis` and the duration are not shown there. The existing workflow already read `analysis.*`, and duration has a timestamp fallback.
- Supabase node `update` with `filterType: string` and `autoMapInputData` on the current n8n Cloud version (parameter names taken from the node's source).
- Switch node `allMatchingOutputs` routing in a real execution.
- SMTP and Twilio delivery, and how n8n behaves when a node's credential is absent.
- Whether GPT-4o fills the four new analysis fields sensibly.
