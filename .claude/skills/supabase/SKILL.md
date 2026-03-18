---
name: supabase
description: "Wraps the Supabase CLI for managing projects, Edge Functions, databases, migrations, secrets, storage, and local dev containers. Use this skill whenever the user asks to manage Supabase resources — listing projects, deploying or serving Edge Functions, running or creating migrations, pushing/pulling schema changes, managing secrets, inspecting database performance, or controlling local Supabase containers. Trigger on mentions of Supabase, Edge Functions, supabase migrations, supabase db, or local Supabase dev. Also trigger when the user uses /supabase."
---

# Supabase CLI Skill

Execute Supabase CLI commands based on the user's request. The CLI binary is at `supabase` (globally installed).

## Command Reference

The CLI follows a `supabase <resource> <action>` pattern.

### Projects

| Action | Command |
|--------|---------|
| list | `supabase projects list` |
| create | `supabase projects create` |
| delete | `supabase projects delete <project-ref>` |
| api-keys | `supabase projects api-keys --project-ref <ref>` |

### Edge Functions

| Action | Command | Notes |
|--------|---------|-------|
| list | `supabase functions list --project-ref <ref>` | |
| new | `supabase functions new <name>` | Creates locally in `supabase/functions/<name>/` |
| serve | `supabase functions serve` | Serves all functions locally |
| deploy | `supabase functions deploy <name> --project-ref <ref>` | Omit name to deploy all |
| download | `supabase functions download <name> --project-ref <ref>` | |
| delete | `supabase functions delete <name> --project-ref <ref>` | |

### Database

| Action | Command | Notes |
|--------|---------|-------|
| diff | `supabase db diff` | Diffs local schema changes |
| dump | `supabase db dump --project-ref <ref>` | Add `--data-only` for data, `--schema public` to filter |
| lint | `supabase db lint` | Checks for typing errors |
| pull | `supabase db pull --project-ref <ref>` | Pulls remote schema into local migrations |
| push | `supabase db push --project-ref <ref>` | Pushes pending migrations to remote |
| reset | `supabase db reset` | Resets local DB to current migrations |
| start | `supabase db start` | Starts local Postgres |

### Migrations

| Action | Command | Notes |
|--------|---------|-------|
| list | `supabase migration list` | Shows local and remote status |
| new | `supabase migration new <name>` | Creates empty migration file |
| up | `supabase migration up` | Applies pending migrations locally |
| down | `supabase migration down --count <n>` | Rolls back last n migrations |
| repair | `supabase migration repair --status reverted <version>` | Fixes migration history |
| squash | `supabase migration squash` | Squashes into single file |
| fetch | `supabase migration fetch` | Fetches from history table |

### Secrets

| Action | Command |
|--------|---------|
| list | `supabase secrets list --project-ref <ref>` |
| set | `supabase secrets set KEY=VALUE --project-ref <ref>` |
| unset | `supabase secrets unset KEY --project-ref <ref>` |

### Storage

Storage commands use S3-like path syntax: `ss3://<bucket>/<path>`.

| Action | Command |
|--------|---------|
| ls | `supabase storage ls ss3://<bucket>/<path>` |
| cp | `supabase storage cp <src> <dst>` |
| mv | `supabase storage mv <src> <dst>` |
| rm | `supabase storage rm ss3://<bucket>/<path>` |

Add `--local` to target local storage instead of linked project.

### Inspect (Database Performance)

| Action | Command | What it shows |
|--------|---------|---------------|
| db-stats | `supabase inspect db db-stats` | Cache hit rates, sizes, WAL |
| table-stats | `supabase inspect db table-stats` | Table sizes, row counts |
| index-stats | `supabase inspect db index-stats` | Index usage and unused indexes |
| outliers | `supabase inspect db outliers` | Slowest queries by total time |
| calls | `supabase inspect db calls` | Most-called queries |
| bloat | `supabase inspect db bloat` | Dead tuple estimates |
| locks | `supabase inspect db locks` | Active exclusive locks |
| blocking | `supabase inspect db blocking` | Lock contention |
| long-running-queries | `supabase inspect db long-running-queries` | Queries running >5min |
| vacuum-stats | `supabase inspect db vacuum-stats` | Vacuum operation stats |
| replication-slots | `supabase inspect db replication-slots` | Replication slot info |
| role-stats | `supabase inspect db role-stats` | Role statistics |
| traffic-profile | `supabase inspect db traffic-profile` | Read/write ratios |

Add `--local` for local DB or `--linked` (default) for remote. Use `supabase inspect report` to generate a full CSV report.

### Local Development

| Action | Command |
|--------|---------|
| init | `supabase init` |
| start | `supabase start` |
| stop | `supabase stop` |
| status | `supabase status` |
| link | `supabase link --project-ref <ref>` |
| unlink | `supabase unlink` |

### Auth & Config

| Action | Command |
|--------|---------|
| login | `supabase login` |
| logout | `supabase logout` |
| orgs list | `supabase orgs list` |

## Global Flags

These flags work with any command:

- `--project-ref <ref>` — target a specific project (required for most remote operations)
- `-o json` — output as JSON (useful for parsing)
- `--linked` / `--local` — target linked remote or local DB
- `--debug` — verbose logging
- `--workdir <path>` — specify project directory

## Usage Examples

- `/supabase projects` → `supabase projects list`
- `/supabase functions deploy my-func` → `supabase functions deploy my-func --project-ref <ref>`
- `/supabase db push` → `supabase db push --project-ref <ref>`
- `/supabase migration new add_users_table` → `supabase migration new add_users_table`
- `/supabase secrets set OPENAI_KEY=sk-xxx` → `supabase secrets set OPENAI_KEY=sk-xxx --project-ref <ref>`
- `/supabase inspect outliers` → `supabase inspect db outliers`
- `/supabase storage ls ss3://avatars/` → `supabase storage ls ss3://avatars/`
- `/supabase status` → `supabase status`

## Rules

1. Always show the raw CLI output to the user.
2. If no arguments are provided, show the available operations.
3. If a command requires `--project-ref` and none is provided, run `supabase projects list` first to help the user pick one.
4. For `inspect` subcommands, the user may omit "db" — e.g., `/supabase inspect outliers` maps to `supabase inspect db outliers`.
5. If the command fails, show the error and suggest a fix.

User arguments: $ARGUMENTS
