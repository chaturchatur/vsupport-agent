---
name: n8n
description: Manage n8n Cloud workflows, executions, and credentials via the REST API. Use this skill whenever the user asks to list, get, create, update, activate, deactivate, delete, or inspect n8n workflows or executions, sync workflow JSON between n8n Cloud and local files, view execution logs, or manage n8n credentials. Trigger on mentions of n8n, n8n workflows, n8n executions, workflow sync, or when the user wants to pull/push workflow JSON.
---

# n8n REST API Skill

Manage n8n Cloud workflows, executions, and credentials via `curl` calls to the n8n REST API.

## Environment

The `.env` file provides two variables (load them before making requests):

- `N8N_API_KEY` — API key for authentication (goes in `X-N8N-API-KEY` header)
- `N8N_WEBHOOK_BASE_URL` — Your n8n Cloud instance URL (e.g., `https://your-instance.app.n8n.cloud`)

The API base is `${N8N_WEBHOOK_BASE_URL}/api/v1`.

To load these in a shell command:

```bash
source .env  # or export manually
```

Every `curl` call must include:
```
-H 'X-N8N-API-KEY: '"$N8N_API_KEY"''
-H 'accept: application/json'
```

## Command Reference

All endpoints are under `${N8N_WEBHOOK_BASE_URL}/api/v1`. Responses are JSON.

### Workflows

| Action | Method | Endpoint | Notes |
|--------|--------|----------|-------|
| List all | GET | `/workflows` | Supports `?active=true\|false`, `?limit=N`, `?cursor=<next>` |
| Get one | GET | `/workflows/{id}` | Returns full workflow JSON including nodes and connections |
| Create | POST | `/workflows` | Body: workflow JSON |
| Update | PUT | `/workflows/{id}` | Body: full workflow JSON (replaces entire workflow) |
| Delete | DELETE | `/workflows/{id}` | |
| Activate | PATCH | `/workflows/{id}/activate` | Makes workflow live |
| Deactivate | PATCH | `/workflows/{id}/deactivate` | Stops workflow from triggering |

### Executions

| Action | Method | Endpoint | Notes |
|--------|--------|----------|-------|
| List all | GET | `/executions` | `?workflowId=X`, `?status=success\|error\|waiting`, `?limit=N` |
| Get one | GET | `/executions/{id}` | Full execution data including node outputs |
| Delete | DELETE | `/executions/{id}` | |

### Credentials

| Action | Method | Endpoint | Notes |
|--------|--------|----------|-------|
| List all | GET | `/credentials` | |
| Get one | GET | `/credentials/{id}` | Does NOT return secret values |
| Create | POST | `/credentials` | Body: `{name, type, data, nodesAccess}` |
| Delete | DELETE | `/credentials/{id}` | |

### Tags

| Action | Method | Endpoint |
|--------|--------|----------|
| List | GET | `/tags` |
| Create | POST | `/tags` |
| Update | PUT | `/tags/{id}` |
| Delete | DELETE | `/tags/{id}` |

## Workflow Sync

This is the most project-specific feature. The local workflow exports live in `n8n/workflows/`.

### Pull (n8n Cloud → local)

Fetch a workflow by ID and save it locally. Use this to keep the repo's JSON exports up to date with what's running in n8n Cloud.

```bash
source .env
# Fetch workflow JSON and save to local file
curl -s -H "X-N8N-API-KEY: $N8N_API_KEY" -H 'accept: application/json' \
  "${N8N_WEBHOOK_BASE_URL}/api/v1/workflows/{id}" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(json.dumps(data, indent=2))
" > n8n/workflows/{filename}.json
```

When pulling, match the workflow ID to the correct local file using the mapping in `.agent/System.md`:
- `MbxKTCGUszqbCafS` → `lookup-caller.json`
- `fS60qOqtDuWyIReD` → `log-interaction.json`
- `oRACRgI5oTF5TSGk` → `end-of-call-report.json`

To pull ALL workflows at once, list them first, then fetch each by ID.

### Push (local → n8n Cloud)

Read the local JSON file and PUT it to n8n Cloud to update the live workflow.

```bash
source .env
curl -s -X PUT \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  -H 'Content-Type: application/json' \
  -H 'accept: application/json' \
  --data-binary @n8n/workflows/{filename}.json \
  "${N8N_WEBHOOK_BASE_URL}/api/v1/workflows/{id}"
```

After pushing, consider activating the workflow if it should be live.

### Sync All

To sync all three project workflows, loop through the ID→filename mapping and pull or push each one. Always confirm with the user before pushing (it overwrites the live workflow).

## Usage Examples

```bash
# List active workflows
source .env && curl -s -H "X-N8N-API-KEY: $N8N_API_KEY" -H 'accept: application/json' \
  "${N8N_WEBHOOK_BASE_URL}/api/v1/workflows?active=true" | python3 -m json.tool

# Get a specific workflow
source .env && curl -s -H "X-N8N-API-KEY: $N8N_API_KEY" -H 'accept: application/json' \
  "${N8N_WEBHOOK_BASE_URL}/api/v1/workflows/MbxKTCGUszqbCafS" | python3 -m json.tool

# List recent failed executions
source .env && curl -s -H "X-N8N-API-KEY: $N8N_API_KEY" -H 'accept: application/json' \
  "${N8N_WEBHOOK_BASE_URL}/api/v1/executions?status=error&limit=5" | python3 -m json.tool

# Activate a workflow
source .env && curl -s -X PATCH -H "X-N8N-API-KEY: $N8N_API_KEY" -H 'accept: application/json' \
  "${N8N_WEBHOOK_BASE_URL}/api/v1/workflows/MbxKTCGUszqbCafS/activate"

# Pull lookup-caller workflow to local
source .env && curl -s -H "X-N8N-API-KEY: $N8N_API_KEY" -H 'accept: application/json' \
  "${N8N_WEBHOOK_BASE_URL}/api/v1/workflows/MbxKTCGUszqbCafS" | python3 -m json.tool > n8n/workflows/lookup-caller.json

# List credentials (names/types only, no secrets)
source .env && curl -s -H "X-N8N-API-KEY: $N8N_API_KEY" -H 'accept: application/json' \
  "${N8N_WEBHOOK_BASE_URL}/api/v1/credentials" | python3 -m json.tool
```

## Important Notes

- **Push is destructive** — it replaces the entire live workflow. Always confirm with the user before pushing.
- **Credential secrets** — the GET credentials endpoint does NOT return secret values. You can see names and types but not keys/passwords.
- **Pagination** — list endpoints support `?limit=N&cursor=<next>`. The `nextCursor` field in the response tells you if there are more results.
- **Workflow IDs** — n8n Cloud uses string IDs (not numeric). The three project workflows are mapped in `.agent/System.md`.
- **Rate limits** — n8n Cloud has rate limits. Don't loop rapidly over many requests.

User arguments: $ARGUMENTS
