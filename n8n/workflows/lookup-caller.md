# Workflow 1: Lookup Caller

**Workflow ID:** `MbxKTCGUszqbCafS` | **Webhook:** `POST /webhook/lookup-caller` | **5 nodes, linear pipeline**

```
Webhook → Parse Envelope → Query Customers → Format Result → Respond
```

---

## Node 1: Webhook (trigger)

- Listens for `POST /webhook/lookup-caller`
- **Auth:** Header Auth — validates `x-vapi-secret` header against the stored credential (`PQXagW16N8ErYDM7`)
- Uses `responseNode` mode — the response is sent explicitly by the final Respond node (not auto-returned)

**Who calls it:** VAPI's GPT-4o LLM issues a `lookup_caller` tool call during conversation. VAPI sends this as a POST with the standard VAPI tool-call envelope.

---

## Node 2: Parse Envelope (Code node — JS)

This is the heaviest node. It does three things:

### a) Unwrap the VAPI envelope

```
body.message.toolCallList[0] → extracts toolCallId + function arguments
```

Arguments expected: `phone_number`, `last_name`, `claim_number` (all optional)

### b) Normalize US phone to E.164

- Strips non-digit chars
- 10 digits → prepends `+1` (US)
- 11 digits starting with `1` → prepends `+`
- Already has `+` prefix → keeps it
- Anything else → sets `error = 'invalid_phone'`

### c) Build a PostgREST OR filter string

Constructs a filter like:

```
or=(phone_digits.eq.14155551234,last_name.ilike.johnson)
```

Key detail: queries the **`phone_digits` generated column** (which stores `14155551234` without the `+`) instead of `phone_number`. This avoids the Supabase node's `encodeURI()` bug that would mangle `+` into `%2B`.

Uses `ilike` (case-insensitive) for `last_name` and `claim_number`.

**Error handling:** If no params provided at all → `error = 'no_params'`.

---

## Node 3: Query Customers (Supabase node)

- **Operation:** `getAll` on `customers` table
- **Filter:** The PostgREST filter string from Parse Envelope (e.g., `or=(phone_digits.eq.14155551234)`)
- **`alwaysOutputData: true`** — if zero rows match, still outputs one empty item so Format Result runs (instead of being skipped by n8n's default behavior)
- Connects via REST API (PostgREST over HTTPS), not the Postgres wire protocol

---

## Node 4: Format Result (Code node — JS)

Handles four cases and wraps the result in VAPI's expected format:

| Case | Condition | Response |
|------|-----------|----------|
| **Invalid phone** | `error === 'invalid_phone'` | `{ found: false, error: true, message: "...invalid..." }` |
| **No params** | `error === 'no_params'` | `{ found: false, error: true, message: "...no search parameters..." }` |
| **No match** | 0 rows returned | `{ found: false, message: "No matching record found" }` |
| **Single match** | Exactly 1 row | `{ found: true, multiple: false, first_name, last_name, claim_number, claim_status, claim_details, phone_number, date_of_birth }` |
| **Multiple matches** | 2+ rows (e.g., two Johnsons) | `{ found: true, multiple: true, matches: [{first_name, last_name, claim_number, claim_status}, ...] }` |

**Single match** includes `date_of_birth` — used by the VAPI assistant's DOB verification step. **Multiple matches** omit sensitive fields, returning only enough for the caller to disambiguate (name + claim number + status).

The final output is wrapped as:

```json
{ "results": [{ "toolCallId": "...", "result": "<stringified JSON>" }] }
```

This is VAPI's required tool-call response format.

---

## Node 5: Respond (Respond to Webhook)

Sends the JSON from Format Result back to VAPI as the HTTP response body. VAPI then feeds this result back into GPT-4o, which uses it to continue the conversation (e.g., "I found your account, Sarah. Can you please verify your date of birth?").

---

## FAQ

### Why does the `phone_digits` column exist? What was the `encodeURI()` bug?

We don't call `encodeURI()` ourselves — the **n8n Supabase node** does it internally on filter values before sending them to PostgREST. If you filter on `phone_number.eq.+14155551234`, the node silently encodes `+` as `%2B`, producing `phone_number.eq.%2B14155551234`. PostgREST then tries to match the literal string `%2B14155551234` against the database — which matches nothing.

**The fix:** Instead of filtering on `phone_number` (which contains `+`), we created a **generated column** `phone_digits` that strips the `+` via `replace(phone_number, '+', '')`. Now the filter value is just digits (`14155551234`) — no `+`, so `encodeURI()` has nothing to mangle. The bug is in n8n's node internals, not something we control, so we worked around it at the schema level.

### What happens when there are multiple matched rows?

The Format Result node returns a **reduced response** — just enough to disambiguate:

```json
{
  "found": true,
  "multiple": true,
  "matches": [
    { "first_name": "Sarah", "last_name": "Johnson", "claim_number": "CLM-2024-001", "claim_status": "approved" },
    { "first_name": "Michael", "last_name": "Johnson", "claim_number": "CLM-2024-002", "claim_status": "pending" }
  ]
}
```

Sensitive fields (`date_of_birth`, `phone_number`, `claim_details`) are **omitted**. GPT-4o then asks the caller to narrow down — typically by claim number. This is the "re-verification" flow. The seed data has two Johnsons specifically to test this path.

### Why REST API (PostgREST) instead of the Postgres wire protocol?

n8n Cloud runs on servers that can only talk to the internet using **IPv4** (the older addressing system). Supabase's database port (5432/6543) only listens on **IPv6** (the newer one). When n8n tries to connect directly, it gets `ENETUNREACH` ("network unreachable") — the call simply can't go through.

But Supabase's **REST API** runs over regular HTTPS (port 443), which works on both IPv4 and IPv6. So we talk to the database over HTTP instead of a direct database connection. Same data, different door.

The built-in Supabase node uses this REST API (PostgREST over HTTPS) under the hood, which is why it works reliably while the Postgres node doesn't.

---

## End-to-end example

1. Caller says: "I'd like to check on my claim"
2. GPT-4o asks for their phone number, caller says "415-555-1234"
3. GPT-4o issues `lookup_caller({ phone_number: "415-555-1234" })`
4. VAPI POSTs the tool-call envelope to n8n
5. Parse Envelope normalizes → `+14155551234`, builds filter `or=(phone_digits.eq.14155551234)`
6. Supabase returns Sarah Johnson's row
7. Format Result returns `{ found: true, first_name: "Sarah", ..., date_of_birth: "1985-03-15" }`
8. GPT-4o says "I found your account, Sarah. For verification, could you please tell me your date of birth?"
