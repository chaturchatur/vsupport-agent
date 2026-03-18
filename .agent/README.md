# .agent Documentation Index

This folder contains living documentation for the **Vsupport-agent** project. Read this file first to understand what's available.

## Documentation Files

| File | Description |
|------|-------------|
| [System.md](System.md) | Project architecture, tech stack, structure, integration points, database schema |
| [SOP.md](SOP.md) | Best practices, coding standards, and standard operating procedures |
| [Tasks.md](Tasks.md) | Full implementation plan (Phase 0–8) with trackable checkboxes per step |
| [Decisions.md](Decisions.md) | Chronological log of architectural/design decisions and reversals with rationale |
| [Gotchas.md](Gotchas.md) | Known landmines, quirks, and non-obvious behaviors — check before debugging |

## How to Maintain

- **From scratch:** Run `/init-docs` to regenerate all documentation
- **Incremental:** Run `/update-docs` to update only changed sections
- Always update this index when adding or removing documentation files
- **Freshness:** Each doc has a `Last verified: YYYY-MM-DD` marker at the top. `/update-docs` should bump this on any doc it touches.
