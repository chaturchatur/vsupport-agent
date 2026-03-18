---
name: vapi
description: Manage VAPI voice assistants, calls, phone numbers, tools, and webhooks via the CLI. Use this skill whenever the user asks to list, create, update, delete, or inspect VAPI resources (assistants, calls, phone numbers, tools), deploy assistant configs, view logs/errors, or forward webhooks locally. Trigger on mentions of VAPI, voice agents, or assistant deployment.
---

# VAPI CLI Skill

Manage VAPI voice assistants, calls, phone numbers, tools, and webhooks via the CLI.

## Instructions

Execute VAPI CLI commands based on the user's request. The CLI binary is at `~/.vapi/bin/vapi`.

### Command Reference

The CLI follows a `vapi <resource> <action>` pattern. Here are the key resources and their actions:

**assistant** — Manage voice assistants
| Action | Command | Notes |
|--------|---------|-------|
| list | `vapi assistant list` | |
| get | `vapi assistant get <id>` | |
| create | `vapi assistant create` | Interactive — or use `update` with `--file` after creating |
| update | `vapi assistant update <id> --file <path>` | Also accepts `--json '<json>'` or `--json -` for stdin |
| delete | `vapi assistant delete <id>` | |

**call** — Manage phone calls
| Action | Command |
|--------|---------|
| list | `vapi call list` |
| get | `vapi call get <id>` |
| create | `vapi call create` |
| end | `vapi call end <id>` |

**phone** — Manage phone numbers
| Action | Command |
|--------|---------|
| list | `vapi phone list` |
| get | `vapi phone get <id>` |
| create | `vapi phone create` |
| update | `vapi phone update <id>` |
| delete | `vapi phone delete <id>` |

**tool** — Manage custom tools/functions
| Action | Command |
|--------|---------|
| list | `vapi tool list` |
| get | `vapi tool get <id>` |
| create | `vapi tool create` |
| update | `vapi tool update <id>` |
| delete | `vapi tool delete <id>` |
| test | `vapi tool test <id>` |
| types | `vapi tool types` |

**logs** — View logs and debugging info
| Action | Command |
|--------|---------|
| list | `vapi logs list` |
| calls | `vapi logs calls` |
| errors | `vapi logs errors` |
| webhooks | `vapi logs webhooks` |

**Other commands**
| Command | Purpose |
|---------|---------|
| `vapi listen --forward-to localhost:8000/webhook` | Forward webhook events to local server (replaces ngrok for VAPI webhooks) |
| `vapi login` | Authenticate with VAPI |
| `vapi auth` | Manage auth and switch accounts |
| `vapi webhook` | Manage webhook endpoints |

### Special Behaviors

**`--from-config` flag**: When the user says `/vapi create-assistant --from-config` or `/vapi update-assistant --from-config`, read `vapi/assistant_config.json` from the project root and pass it via `--file` or `--json`:
```bash
~/.vapi/bin/vapi assistant update <id> --file vapi/assistant_config.json
```

**Deploying config changes**: When updating an assistant from the project config, always:
1. Read `vapi/assistant_config.json` to confirm it exists and looks valid
2. If no assistant ID is provided, run `vapi assistant list` to find the right one
3. Run the update command with `--file`

### Usage Examples

- `/vapi list assistants` → `~/.vapi/bin/vapi assistant list`
- `/vapi get assistant abc123` → `~/.vapi/bin/vapi assistant get abc123`
- `/vapi create-assistant --from-config` → read config, create/update assistant
- `/vapi list calls` → `~/.vapi/bin/vapi call list`
- `/vapi get call xyz789` → `~/.vapi/bin/vapi call get xyz789`
- `/vapi list phone-numbers` → `~/.vapi/bin/vapi phone list`
- `/vapi logs errors` → `~/.vapi/bin/vapi logs errors`
- `/vapi listen 8000` → `~/.vapi/bin/vapi listen --forward-to localhost:8000/webhook`
- `/vapi tool types` → `~/.vapi/bin/vapi tool types`

Always show the raw CLI output to the user.

User arguments: $ARGUMENTS
