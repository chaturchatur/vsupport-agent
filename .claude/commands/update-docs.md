---
description: Reads the README index and intelligently updates the relevant existing .agent documentation based on recent changes.
allowed-tools: Read, Write, Grep
---

# Context

You are an expert code documentation engineer maintaining the `.agent` folder.

# Task: Update Documentation

1. **Get Context:** Please read `.agent/README.md` FIRST to get an understanding of what already exists.
2. **Targeted Update:** Update the relevant parts in the system & architecture design (`System.md`), OR update the `SOP.md` for new best practices/mistakes we made, OR add/update entries in `Decisions.md` when architectural or design decisions are made or reversed, OR add new entries to `Gotchas.md` for non-obvious bugs/quirks discovered. Do not rewrite everything; only update what has changed.
   - Bump the `Last verified: YYYY-MM-DD` date on any doc you touch.
   - If new domain terms were introduced, add them to the Glossary in `System.md`.
3. **New Doc Rules:** When creating new doc files, please include a "Related doc" section that clearly lists out relevant docs to read for full context.
4. **Update the Index:** In the end, ALWAYS update the `.agent/README.md` too to ensure the index of all documentation files remains perfectly up-to-date.
