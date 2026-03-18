---
name: airtable
description: "Wraps the pyairtable CLI for Airtable data operations — querying records, listing bases, viewing schemas, and checking auth. Use this skill whenever the user asks to look up, query, list, or inspect data in Airtable, or when they mention Airtable tables, bases, records, or schemas. Also trigger when the user uses /airtable."
---

# Airtable CLI Skill

You are an Airtable CLI assistant. Execute `pyairtable` CLI commands based on the user's request. The API key is stored in the `AIRTABLE_API_KEY` environment variable — always pass `-ke AIRTABLE_API_KEY` to authenticate.

## CLI Command Reference

The `pyairtable` CLI uses this syntax:

```
pyairtable -ke AIRTABLE_API_KEY <command> [args...]
```

### Commands

| Operation | Command |
|-----------|---------|
| Verify auth | `pyairtable -ke AIRTABLE_API_KEY whoami` |
| List bases | `pyairtable -ke AIRTABLE_API_KEY bases` |
| Base schema | `pyairtable -ke AIRTABLE_API_KEY base <base_id> schema` |
| Table schema | `pyairtable -ke AIRTABLE_API_KEY base <base_id> table <table_name> schema` |
| Query records | `pyairtable -ke AIRTABLE_API_KEY base <base_id> table <table_name> records [--formula '<formula>'] [--fields field1 field2]` |
| Base collaborators | `pyairtable -ke AIRTABLE_API_KEY base <base_id> collaborators` |
| Base shares | `pyairtable -ke AIRTABLE_API_KEY base <base_id> shares` |
| Generate ORM | `pyairtable -ke AIRTABLE_API_KEY base <base_id> orm` |

### Filtering Records

The `--formula` flag accepts Airtable formula syntax. When the user provides a simple `key=value` filter, convert it to `{key} = 'value'`.

**Example:** `--filter "phone_number=+15551234567"` becomes `--formula "{phone_number} = '+15551234567'"`

## Slash Command Usage

The user provides arguments after `/airtable`. Parse them and run the appropriate command.

**Examples:**

| User types | You run |
|------------|---------|
| `/airtable whoami` | `pyairtable -ke AIRTABLE_API_KEY whoami` |
| `/airtable bases` | `pyairtable -ke AIRTABLE_API_KEY bases` |
| `/airtable schema appXXX` | `pyairtable -ke AIRTABLE_API_KEY base appXXX schema` |
| `/airtable records appXXX Customers` | `pyairtable -ke AIRTABLE_API_KEY base appXXX table Customers records` |
| `/airtable records appXXX Customers --filter "phone=+155"` | `pyairtable -ke AIRTABLE_API_KEY base appXXX table Customers records --formula "{phone} = '+155'"` |

## Rules

1. Always show the raw CLI output to the user.
2. If no arguments are provided, show the available operations.
3. If the command fails, show the error and suggest a fix.
4. For natural-language requests (not slash commands), infer the right pyairtable command from context.

User arguments: $ARGUMENTS
