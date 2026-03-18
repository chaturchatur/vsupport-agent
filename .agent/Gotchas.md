# Gotchas & Pitfalls

> Last verified: 2026-03-18 (FAQ RAG with Supabase pgvector + VAPI Custom KB)

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
| Phone normalization is JS-only in n8n | The lookup-caller workflow normalizes phones using basic JS (strip non-digits + prepend +1). This handles common US formats but won't work for international numbers. For robust normalization, use FastAPI's `/normalize-phone` endpoint (Python `phonenumbers` lib). |
| Workflow JSONs are NOT auto-deployed | The repo exports (`n8n/workflows/`) are reference copies only. After editing them locally, run `./scripts/deploy-n8n.sh` to push to n8n Cloud via the REST API. There is no CI/CD trigger — forgetting this step means live workflows diverge from repo. |
| n8n API rejects read-only fields | The `PUT /workflows/{id}` endpoint rejects `id`, `active`, `createdAt`, `updatedAt`, `versionId` in the request body. The deploy script strips these automatically. |

## FastAPI / Testing

| Gotcha | Detail |
|--------|--------|
| `pytest` needs `-p no:playwright` | A globally installed `pytest-playwright` plugin conflicts with this project's test runner. Always run: `pytest tests/ -p no:playwright` |
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
| `vapi_call_id UNIQUE` is the dedup mechanism | The interactions table's unique constraint on `vapi_call_id` enables `INSERT ON CONFLICT DO NOTHING`. This replaced the old 10-second wait + Airtable search hack. |

---

**Related docs:** [SOP.md](SOP.md) (procedures), [Decisions.md](Decisions.md) (why things are the way they are), [System.md](System.md) (architecture)
