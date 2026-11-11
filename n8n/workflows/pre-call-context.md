# Workflow 4: Pre-Call Context

**Workflow ID:** not created yet (the first `./scripts/deploy-n8n.sh pre-call-context` creates it and prints the id to put in the `.json`) | **Webhook:** `POST /webhook/pre-call-context` | **7 nodes, linear pipeline**

```
Webhook → Parse Assistant Request → Query Customer → Pick Customer → Query Last Interaction → Build Response → Respond
```

Recognises the caller from their caller ID **before the agent says anything**, so a known caller is greeted by first name and asked only for their date of birth.

> **Status:** written and unit-tested against VAPI's documented payloads. It has **not** been deployed or exercised by a real call. See "Not verified" at the bottom.

---

## Why a separate webhook path (and not `/webhook/vapi-server`)

This was decided by VAPI's documentation, checked on 2026-11-11:

- `assistant-request` is sent only *"if a PhoneNumber doesn't have an `assistantId`"*. At that moment no assistant has been chosen, so the assistant-level `server.url` (`/webhook/vapi-server`) is not in play. The request goes to the **phone number's** server URL (falling back to the org-level one).
- `assistant-request` is **not** a member of the assistant `serverMessages` enum. Adding it to `serverMessages` in `assistant_config.json` would not enable anything and risks the assistant PATCH being rejected. `serverMessages` is therefore unchanged.

So the phone number gets its own server URL pointing here, and `/webhook/vapi-server` keeps doing one job (end-of-call reports). `scripts/configure-vapi-phone.sh enable` makes that change; `disable` puts the assistant back on the number.

**The cost of this design:** once enabled, every inbound call depends on this webhook answering within **7.5 seconds** (fixed by VAPI, not configurable). VAPI documents no fallback: if n8n is down or slow, the call fails. Everything below is built to always answer, and answer fast, but an n8n Cloud outage would take inbound calls down until `configure-vapi-phone.sh disable` is run.

---

## Node 1: Webhook (trigger)

- Listens for `POST /webhook/pre-call-context`
- **Auth:** Header Auth, same `x-vapi-secret` credential as the other workflows (`PQXagW16N8ErYDM7`)
- `responseNode` mode: the Respond node at the end sends the body

**Who calls it:** VAPI, once per inbound call, before the call is connected to an assistant.

**What VAPI sends** (documented shape):

```json
{ "message": { "type": "assistant-request", "call": { /* Call object */ } } }
```

---

## Node 2: Parse Assistant Request (Code node, JS)

1. Sets `is_assistant_request` (`message.type === 'assistant-request'`).
2. Finds the caller's number. VAPI's docs are not consistent about the path, so three candidates are tried in order: `message.call.customer.number`, `message.customer.number`, `message.call.from.phoneNumber`.
3. Normalises it to E.164 with **the same rules as Lookup Caller's Parse Envelope** (10 digits → `+1…`, 11 digits starting with 1 → `+…`, already-`+` numbers kept). A test asserts the two nodes agree.
4. Outputs `phone_digits` (E.164 without `+`), matching the `customers.phone_digits` generated column.

| Situation | `error` | `phone_digits` |
|-----------|---------|----------------|
| Valid number | `''` | `14155551234` |
| Caller ID withheld | `no_phone` | `0` |
| Not a phone number | `invalid_phone` | `0` |

`0` can never match a row. That matters: an empty filter would return *every* customer.

---

## Node 3: Query Customer (HTTP Request → Supabase REST)

```
GET {SUPABASE_URL}/rest/v1/customers?phone_digits=eq.<digits>&select=id,first_name,claim_number,claim_status&limit=2
```

- Auth: the existing `Supabase account` credential, used as a predefined credential type
- **`timeout: 2500` ms**, `onError: continueRegularOutput`, `alwaysOutputData: true`
- `date_of_birth` is deliberately **not** selected. The DOB never enters the prompt; the agent still gets it through `lookup_caller` when it needs to verify.

**Why HTTP Request and not the Supabase node** (which every other workflow uses): the Supabase node has no per-request timeout. Here a hung lookup means a failed phone call, so each lookup needs a hard cap that falls through to the default response. The `+`-encoding problem that pushed the project back to the Supabase node does not apply, because only digits are filtered on.

---

## Node 4: Pick Customer (Code node, JS)

- Keeps only items with an `id` (a failed/timed-out request arrives as an error item with no `id`)
- **Exactly one** match → `caller_known: true`
- Zero matches, a lookup error, or two customers sharing one number → `caller_known: false`. The workflow never guesses between people.
- For unknown callers it sets `phone_digits` to `0` so the next node finds nothing.

---

## Node 5: Query Last Interaction (HTTP Request → Supabase REST)

```
GET {SUPABASE_URL}/rest/v1/interactions?caller_phone_digits=eq.<digits>&select=summary,sentiment,timestamp&order=timestamp.desc&limit=1
```

Same timeout and error settings as Node 3. `caller_phone_digits` is the caller ID stored by the End-of-Call Report workflow (migration `007`). `interactions.phone_number` cannot be used: it holds whatever number the caller *said*, in whatever format the LLM passed along.

Calls made before migration 007 have no `caller_phone_digits`, so a returning caller's first call after deployment has no "last call".

---

## Node 6: Build Response (Code node, JS)

Returns what VAPI expects:

```json
{
  "assistantId": "<VAPI_ASSISTANT_ID>",
  "assistantOverrides": {
    "variableValues": {
      "callerKnown": "true",
      "firstName": "Sarah",
      "claimNumber": "CLM-2024-001",
      "claimStatus": "approved",
      "lastCallSummary": "Caller checked claim status. Claim approved.",
      "lastCallSentiment": "positive",
      "callerNumber": "+14155551234"
    },
    "firstMessage": "Thank you for calling Observe Insurance, Sarah. ... could you please verify your date of birth?"
  }
}
```

| Variable | Known caller | Unknown caller / error |
|----------|--------------|------------------------|
| `callerKnown` | `"true"` | `"false"` |
| `firstName` | first name | `""` |
| `claimNumber`, `claimStatus` | from `customers` | `""` |
| `lastCallSummary` | last summary, whitespace collapsed, max 300 chars | `""` |
| `lastCallSentiment` | `positive` / `neutral` / `negative`, or `""` if no earlier call | `""` |
| `callerNumber` | E.164 caller ID (lets the agent call `lookup_caller` without asking) | `""` |

Design points:

- **All values are strings.** VAPI does not document how booleans or nulls render inside a prompt, and the prompt tests for the literal text `true`.
- **The greeting is overridden with `assistantOverrides.firstMessage`, only for known callers.** Unknown callers get no `firstMessage` override, so they hear the assistant's own `firstMessage`: today's greeting, unchanged. This avoids relying on template conditionals inside `firstMessage`, which VAPI's docs do not confirm.
- The first name is spoken aloud, so it must be letters/spaces/hyphens/apostrophes. Anything else downgrades the caller to unknown.
- The greeting contains the first name and nothing else from the account.
- `assistantId` comes from `__VAPI_ASSISTANT_ID__`, filled in from `.env` at deploy time. The deploy fails if it is unset.
- A non-`assistant-request` event gets `{}`.

**Caller ID is not authentication.** The variables are context for the prompt, not permission. `vapi/system_prompt.md` sections 1 and 2 forbid saying anything but the first name until date-of-birth verification passes.

---

## Node 7: Respond (Respond to Webhook)

Sends `Build Response`'s JSON back to VAPI.

---

## Failure behaviour

| What goes wrong | Result |
|-----------------|--------|
| Unknown number | Default assistant, `callerKnown = "false"`, today's greeting |
| Caller ID withheld / malformed | Same |
| Supabase error or slower than 2.5 s on the customer lookup | Same (error item has no `id`) |
| Supabase error on the history lookup | Caller still recognised, `lastCall*` empty |
| Two customers share the number | Default assistant, `callerKnown = "false"` |
| Wrong/missing `x-vapi-secret` | n8n rejects the request → **VAPI fails the call** |
| n8n Cloud down or the whole workflow exceeds 7.5 s | **VAPI fails the call**. Roll back with `configure-vapi-phone.sh disable` |

Worst case inside the workflow is two timeouts, about 5 s, plus n8n overhead.

---

## Not verified (needs live accounts)

- The exact path of the caller's number in a real `assistant-request` (three documented candidates are handled; log one real payload to confirm).
- That VAPI accepts `server.headers` on a phone number through the API (documented for the dashboard only).
- That `assistantOverrides.firstMessage` and `variableValues` are applied to an inbound call as documented.
- Real latency of the two Supabase reads from n8n Cloud.
- HTTP Request node behaviour with the `supabaseApi` predefined credential on the current n8n Cloud version.
