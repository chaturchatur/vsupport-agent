# Gotchas & Pitfalls

> Last verified: 2026-11-11 (pre-call / post-call workflows added; those entries come from docs and tests, not from a live call)

Known landmines, quirks, and non-obvious behaviors. Check here before debugging something that "should work."

---

## VAPI

| Gotcha | Detail |
|--------|--------|
| Tools must be in `model.tools[]` | Placing tools at the assistant config top level is silently ignored by the VAPI API. |
| `server.secret` doesn't work | Despite appearing in some docs, VAPI doesn't support `server.secret` for **tool calls**. Use `server.headers["x-vapi-secret"]` instead. However, Knowledge Base `server.secret` **does** work — it sends `x-vapi-signature` (HMAC SHA256) to the KB endpoint. |
| KB is a separate resource | `knowledgeBase` at the assistant top level returns 400. Create KB via `POST /knowledge-base`, then reference via `model.knowledgeBaseId`. |
| `analysisPlan.summaryPrompt` is a flat string | Not `analysisPlan.summaryPlan.prompt` — the nested form doesn't work. |
| `structuredDataPlan` must declare all extracted fields | The EOC workflow extracts fields from `message.analysis.structuredData`. If a field (e.g., `callerName`) isn't in the schema's `properties`, VAPI won't extract it and it will always be `undefined`/`"Unknown"`. Fixed 2026-03-18. |
| VAPI CLI `create` is interactive-only | No `--body` flag exists. Use the REST API (`POST /assistant`) for scripted deployments. |
| VAPI CLI `update` also interactive | Same issue — use `PATCH /assistant/:id` via REST API. |
| `assistant-request` is NOT a `serverMessages` value | It is not in the assistant `serverMessages` enum (checked against the API reference 2026-11-11). VAPI sends it only when the **phone number has no `assistantId`**, to the **phone number's** server URL. Do not add it to `assistant_config.json`. |
| `assistant-request` has a fixed 7.5 s deadline and no fallback | Not configurable, the dashboard timeout slider does not apply. If the webhook is slow, down, or rejects the secret, the inbound call fails. Rollback: `./scripts/configure-vapi-phone.sh disable`. |
| Caller number path in `assistant-request` is not pinned down by the docs | One doc page uses `call.from.phoneNumber`, the variables page implies `customer.number`. `pre-call-context` checks `message.call.customer.number`, `message.customer.number`, `message.call.from.phoneNumber`. Confirm with one real payload. |
| Template conditionals in `firstMessage` are undocumented | VAPI documents `{{variable}}` substitution and LiquidJS in system prompts, not `{% if %}` in `firstMessage`. The known-caller greeting is therefore sent as `assistantOverrides.firstMessage` from n8n instead. |
| Variable values are sent as strings | How booleans/nulls render in a prompt is undocumented, so `callerKnown` is the string `"true"`/`"false"` and the prompt tests for the literal text. |

## n8n

| Gotcha | Detail |
|--------|--------|
| Webhook auth is Header Auth credential | n8n validates `x-vapi-secret` via a Header Auth credential, not built-in webhook auth. |
| n8n Cloud cannot reach Supabase Postgres wire protocol | IPv6 routing issues (`ENETUNREACH`) block connections to `db.<ref>.supabase.co:5432` and the pooler on `:6543`. Use the Supabase node (REST API over HTTPS) instead of the Postgres node. |
| Supabase node returns 0 items for 0 rows | Same as old Postgres node behavior — use `alwaysOutputData: true` to ensure downstream nodes execute. |
| Supabase credential uses host URL + service role key | Configure as: Host `https://<ref>.supabase.co`, Service Role Key from Dashboard → Settings → API. Credential ID: `Zhs4bVeCvuPXCQkF`. |
| Supabase node `defineInNode` is unreliable — use `autoMapInputData` | The Supabase node v1's `defineInNode` mode with `fieldsUi` hits a schema cache bug: `"Could not find the '' column"`. The node creates rows with all defaults/nulls instead of the mapped values. **Fix:** Use `dataToSend: "autoMapInputData"` instead — it maps input JSON keys directly to columns, bypassing the schema cache. Ensure Code nodes upstream only output keys matching actual DB columns (strip metadata like `toolCallId`, `is_eoc`, etc. before the Supabase node). |
| PostgREST `+` in phone numbers must be URL-encoded | The `+` in E.164 numbers (e.g. `+17185557777`) is interpreted as a space in URL query params. The Supabase node's `encodeURI()` preserves `+` (bad) and double-encodes `%2B` to `%252B` (also bad). **Fix:** Query the `phone_digits` generated column (strips `+`) instead of `phone_number`. The filter value is digits-only (e.g., `phone_digits.eq.17185557777`), so `encodeURI()` has nothing to mangle. See migration `002_phone_digits_column.sql`. |
| PostgREST `ilike` for case-insensitive match | Used in lookup filter: `last_name.ilike.johnson`. This is case-insensitive exact match (no wildcards). Replaces the old `LOWER(last_name) = LOWER(...)` SQL pattern. |
| Dedup via unique constraint + onError | End-of-call-report uses Supabase create with `onError: continueRegularOutput`. The UNIQUE constraint on `vapi_call_id` silently rejects duplicates — equivalent to `ON CONFLICT DO NOTHING`. |
| Phone normalization is JS-only in n8n | The lookup-caller workflow normalizes phones using basic JS (strip non-digits + prepend +1). This handles common US formats but won't work for international numbers. |
| Workflow JSONs are NOT auto-deployed | The repo exports (`n8n/workflows/`) are reference copies only. After editing them locally, run `./scripts/deploy-n8n.sh` to push to n8n Cloud via the REST API. There is no CI/CD trigger — forgetting this step means live workflows diverge from repo. |
| n8n API rejects read-only fields | The `PUT /workflows/{id}` endpoint rejects `id`, `active`, `createdAt`, `updatedAt`, `versionId` in the request body. The deploy script strips these automatically. |
| The EOC "upsert" alone drops data on the happy path | When `log_interaction` already wrote the row, the EOC `create` is rejected by the UNIQUE constraint and everything in the report is discarded. Outcome columns are therefore patched on with a second node (`Merge Outcomes`, Supabase `update` on `vapi_call_id`). Don't remove it. |
| Apply migrations before deploying `end-of-call-report` | `autoMapInputData` sends every key as a column. Without migration 007 the insert fails, the error is swallowed, and dropped calls are no longer logged at all. |
| `__PLACEHOLDER__` values in workflow JSON | Resolved from `.env` by `scripts/resolve_n8n_placeholders.py` during `deploy-n8n.sh`. Importing a workflow JSON by hand in the n8n UI leaves them unresolved: alert email and SMS are then skipped, and `pre-call-context` returns a bogus assistant id. Always deploy with the script. |
| n8n `$vars` needs Cloud Pro | Custom variables are Pro/Enterprise only, which is why deploy-time placeholders are used for the alert recipient and Twilio sender. |
| Supabase node has no request timeout | Fine for tool calls (VAPI's own 10 s timeout applies). Not fine for `pre-call-context`, which uses HTTP Request nodes with a 2.5 s timeout against the Supabase REST API. |
| New workflow exports start with `"id": ""` | `deploy-n8n.sh` creates the workflow and prints the new id. Paste it into the JSON, or the next deploy creates a duplicate. |

## Testing

| Gotcha | Detail |
|--------|--------|
| `pytest` needs `-p no:playwright` | A globally installed `pytest-playwright` plugin conflicts with this project's test runner. Always run: `pytest tests/ -p no:playwright` |
| Tests need Node.js | The parsing logic lives in n8n Code nodes (JavaScript). `tests/n8n_harness.py` extracts it from the workflow JSON and runs it with `node`. Without Node those tests are skipped, not failed: check the skip count. |
| `.env` must exist for tests | `app/config.py` uses Pydantic Settings which reads `.env`. Tests may fail if it's missing — copy from `.env.example`. |
| `config.py` uses `extra: "ignore"` | The `.env` file may contain legacy vars (Airtable, Supabase, etc.) that aren't in the Settings model. `extra: "ignore"` prevents Pydantic from rejecting them. Don't remove this. |

## Supabase / Database

| Gotcha | Detail |
|--------|--------|
| Phone numbers must be E.164 | All phone comparisons in queries assume E.164 format (`+14155551234`). Raw input like `(415) 555-1234` won't match — normalize first. |
| Two Johnsons are intentional | Sample data has two records with last_name "Johnson" to test multi-match lookup flows. Don't "fix" this. |
| `phone_digits` is a generated column — don't write to it | `phone_digits` on `customers` is `GENERATED ALWAYS AS (replace(phone_number, '+', '')) STORED`. Postgres maintains it automatically. Inserting/updating `phone_digits` directly will error. Only write to `phone_number`; `phone_digits` updates itself. |
| DOB verification is LLM-side only | The `date_of_birth` field is returned in the `lookup_caller` response. The LLM compares the caller's spoken DOB against it — there is no server-side verification tool. The system prompt strictly forbids the LLM from reading back or revealing the stored DOB. If the DOB field is empty, the step is skipped. |
| DOB matching must be flexible | Callers say dates in many formats ("March 15th, 1985", "3/15/85", "March fifteenth nineteen eighty-five"). The LLM is instructed to extract month/day/year and compare against the `YYYY-MM-DD` stored value. Don't add strict format validation — let the LLM handle natural language dates. |
| `interactions.phone_number` is not the caller ID | On the happy path it is whatever number the caller said, as passed by the LLM. To find a caller's previous calls use `caller_phone_digits` (caller ID, digits only, written by the EOC workflow since migration 007). |
| Outcome columns are NULL for unscored calls | NULL means "no analysis", not "false". `v_call_outcomes_daily.containment_rate` divides by `scored_calls`, not `calls`. |
| Outcomes are an LLM's judgement | `resolved_without_human` etc. come from VAPI's post-call analysis. Treat the containment rate as an estimate until spot-checked. |
| `vapi_call_id UNIQUE` is the dedup mechanism | The interactions table's unique constraint on `vapi_call_id` enables `INSERT ON CONFLICT DO NOTHING`. This replaced the old 10-second wait + Airtable search hack. |

---

**Related docs:** [SOP.md](SOP.md) (procedures), [Decisions.md](Decisions.md) (why things are the way they are), [System.md](System.md) (architecture)
