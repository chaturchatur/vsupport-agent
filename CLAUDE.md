# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Vsupport-agent** — VoiceAI insurance claims support agent. VAPI handles voice (Deepgram STT + GPT-4o + ElevenLabs TTS), n8n Cloud is the primary integration layer (all webhooks + Airtable CRUD), FastAPI is a thin utility layer (phone normalization only).

## Tech Stack

- **Voice**: VAPI (telephony orchestration) → Deepgram Nova-2 (STT) → GPT-4o (LLM) → ElevenLabs (TTS)
- **Workflows**: n8n Cloud — receives ALL VAPI webhooks, handles ALL Airtable reads/writes
- **Backend**: Python + FastAPI — utility only (`/health`, `/normalize-phone`)
- **Data**: Airtable (Customers table for reads, Interactions table for writes)
- **CLI Tools**: `vapi` CLI, `pyairtable` CLI (wrapped via custom skills `/vapi` and `/airtable`)

## Commands

```bash
# FastAPI
uvicorn app.main:app --reload          # Run dev server
pytest tests/                           # Run all tests
pytest tests/test_phone_normalize.py    # Single test file

# CLI tools
vapi assistants list                    # List VAPI assistants
pyairtable --help                       # Airtable CLI
```

# DOCS (CRITICAL CONTEXT ROUTING)

We keep all important architectural docs, SOPs, and tasks in the `.agent` folder.

**Before you plan any implementation or write any code, you MUST always read `.agent/README.md` first to get context.**

Do not guess the architecture or workflow rules. Instead, read the `.agent/README.md` index to find the exact file you need:

- `.agent/Tasks.md`: PRD & implementation plans.
- `.agent/System.md`: Current state of the system, data flows, LLM strategy, stealth implementations, and domain glossary.
- `.agent/SOP.md`: Best practices, workflow orchestration, MCP usage rules, and self-improvement loops.
- `.agent/Decisions.md`: Chronological log of architectural/design decisions and reversals with rationale.
- `.agent/Gotchas.md`: Known landmines, quirks, and non-obvious behaviors — check before debugging.

**Post-Implementation Rule:**
We should always update the `.agent` docs after we implement a certain feature, to make sure it fully reflects the up-to-date information. If you change a data flow or add a new module, you must update `.agent/System.md`. If you hit a non-obvious bug or quirk, add it to `.agent/Gotchas.md`.
