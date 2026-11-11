# Grafana: call outcomes dashboard

`dashboard.json` is a Grafana dashboard that reads the Supabase database through Grafana's PostgreSQL data source.

| Panel | Source |
|-------|--------|
| Containment rate (stat + per day) | `v_call_outcomes_daily` |
| Calls per day | `v_call_outcomes_daily` |
| Escalations per day | `v_call_outcomes_daily` |
| Authenticated share | `v_call_outcomes_daily` |
| Sentiment mix | `interactions` |
| Average call duration | `interactions` |

Days are UTC. Containment rate is `contained_calls / scored_calls`; calls without outcome data (anything logged before migration 007) are not scored.

> **Status:** the JSON is checked by tests for structure and for which tables it reads. It has **not** been imported into a Grafana instance or run against a database.

## Prerequisites

- Migration `supabase/migrations/007_interaction_outcomes.sql` applied (creates the view).
- Grafana 10 or newer (Grafana Cloud free tier works).

## 1. Create a read-only database role

Run in the Supabase SQL Editor. Pick your own password and keep it in a password manager, not in this repo.

```sql
-- Read-only login for Grafana. Replace the password before running.
CREATE ROLE grafana_reader WITH LOGIN PASSWORD 'REPLACE_WITH_A_LONG_RANDOM_PASSWORD';

GRANT USAGE ON SCHEMA public TO grafana_reader;

-- Only what the dashboard reads. Not customers, not follow_ups, not faqs.
GRANT SELECT ON public.interactions TO grafana_reader;
GRANT SELECT ON public.v_call_outcomes_daily TO grafana_reader;

-- Belt and braces: this role can never write, and cannot run long queries.
ALTER ROLE grafana_reader SET default_transaction_read_only = on;
ALTER ROLE grafana_reader SET statement_timeout = '15s';
```

Notes:

- The view is created with `security_invoker = true`, so it runs with `grafana_reader`'s own privileges. That is why the role needs `SELECT` on `interactions` as well as on the view.
- `interactions` contains caller names, phone numbers and call summaries. Anyone who can edit dashboards on this data source can query them. If that is too broad, grant `SELECT` on specific columns instead:
  `GRANT SELECT (timestamp, sentiment, duration_seconds, authenticated, resolved_without_human, escalation_requested) ON public.interactions TO grafana_reader;`
- If you later enable row level security on `interactions`, add a `SELECT` policy for `grafana_reader` or the panels will go empty.

To remove the role: `DROP OWNED BY grafana_reader; DROP ROLE grafana_reader;`

## 2. Add the data source

Grafana → Connections → Data sources → Add data source → **PostgreSQL**.

| Field | Value |
|-------|-------|
| Host URL | The **Session pooler** host and port from Supabase → Project Settings → Database → Connection string |
| Database | `postgres` |
| Username | `grafana_reader.<project-ref>` when using the pooler; `grafana_reader` on a direct connection |
| Password | The password from step 1 |
| TLS/SSL mode | `require` |

Use the pooler host rather than `db.<project-ref>.supabase.co`: the direct host is IPv6-only on most Supabase projects, the same issue that kept n8n Cloud off the Postgres wire protocol (see `.agent/Gotchas.md`).

Click **Save & test**.

The connection details live only in Grafana. Do not paste a connection string into this repo, the dashboard JSON, or `.env.example`.

## 3. Import the dashboard

Grafana → Dashboards → New → Import → upload `grafana/dashboard.json` → choose the data source from step 2 for **Supabase (PostgreSQL)** → Import.

The dashboard JSON refers to the data source through an import-time input (`${DS_SUPABASE}`), so it contains no host, user or password.

## Checking it against the database

```sql
SELECT * FROM v_call_outcomes_daily ORDER BY day DESC LIMIT 14;
```

The stat panels should match the sums of this query for the selected time range.
