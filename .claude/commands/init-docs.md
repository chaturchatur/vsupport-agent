---
description: Performs a deep scan of the codebase to initialize the .agent documentation structure from scratch.
allowed-tools: Bash(mkdir:*), Bash(touch:*), Read, Glob, Grep
---

# Context

You are an expert code documentation engineer. Your goal is to do a deep scan & analysis to provide super accurate & up-to-date documentation to give new engineers full context.

# Task: Initialize Documentation

1. **Deep Scan:** Please do a deep scan of the codebase, both frontend & backend, to grab full context.
2. **Generate Architecture Docs:** Create the `.agent` folder. Generate the system & architecture documentation, including:
   - Project architecture (goal, structure, tech stack, integration points).
   - Database schema.
   - _Note: Please consolidate docs as much as possible (no overlap). The most basic version just needs `System.md`, but you can create specific docs for critical/complex parts._
3. **Generate Standard Docs:** Create `.agent/SOP.md` (for best practices), `.agent/Tasks.md` (for PRDs/plans), `.agent/Decisions.md` (for tracking architectural/design decisions and reversals with rationale), and `.agent/Gotchas.md` (for known landmines, quirks, and non-obvious behaviors).
   - Add a `Last verified: YYYY-MM-DD` marker at the top of every doc.
   - Add a Glossary section at the bottom of `System.md` for domain-specific terms.
4. **Generate the Index:** Update `.agent/README.md`. Make sure you include an index of all documentation created in `.agent`, so anyone can just look at `README.md` to get a full understanding of where to look for what information.
