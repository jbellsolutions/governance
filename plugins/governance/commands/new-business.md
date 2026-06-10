---
description: Spin up a new autonomous business (a new isolated company) on the Paperclip board.
argument-hint: <business name and what it does>
---

Spin up a new business on the Paperclip governance board: **$ARGUMENTS**

Use the `spin-up-team` skill (Recipe A for a preset, or Recipe B to generate a custom org inline).
Requirements: confirm `PAPERCLIP_API_URL`, `PAPERCLIP_API_KEY`, `OPENROUTER_API_KEY` are set (see the
`governance` skill). Then:

1. Decide preset vs custom from the description. Default to the `_template` preset unless it's clearly
   sales/lead-gen (use `lead-gen-agency`) or clearly bespoke (generate inline).
2. Create the company and import the package as a NEW company; set every agent to `opencode_local`
   with the OpenRouter model via `adapterOverrides`.
3. **Create the team's routine(s)** and verify `GET /api/companies/{id}/routines` is non-empty —
   a business with no routine won't run on its own.
4. Report: the new company id, the org (agents + reporting lines), the routine(s) + first-fire, and
   any secrets/Composio apps the owner must connect.

Be idempotent: check `GET /api/companies` for the name first; reuse if it exists.
