---
description: Add a new department/team of agents inside an existing company.
argument-hint: <department> in <existing company>
---

Add a new department to an existing company on the Paperclip governance board: **$ARGUMENTS**

Use the `spin-up-team` skill (Recipe C, or an inline `existing_company` import for rich
instructions). Ensure `PAPERCLIP_API_URL`, `PAPERCLIP_API_KEY`, `OPENROUTER_API_KEY` are set.

1. Resolve the target company id (`GET /api/companies`, match by name) and its CEO agent id.
2. Create a department-head agent `reportsTo` the CEO, plus its specialist(s) `reportsTo` the head —
   all on `opencode_local` with the OpenRouter model.
3. **Create a routine** for the department (a weekly review at minimum) so it runs autonomously, and
   verify `GET /api/companies/{id}/routines`.
4. Report the new agents (names + IDs), the reporting lines, and the routine + first-fire.

Prefer an inline `existing_company` import when the agents need real role instructions (it writes
their `AGENTS.md` to disk and creates the routine in one call).
