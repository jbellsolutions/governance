---
description: Report stats for a company/team — budget, spend, agents, and activity.
argument-hint: [company name, or blank for all]
---

Report governance stats for: **$ARGUMENTS** (if blank, summarize every company).

Use the `manage-teams` skill. Ensure `PAPERCLIP_API_URL` + `PAPERCLIP_API_KEY` are set.

For each target company, produce a concise, scannable summary:

- **Budget**: `budgetMonthlyCents` vs `spentMonthlyCents` (format as dollars).
- **Agents**: name · status · monthly spend, grouped by reporting line.
- **Activity**: open issues, and the routines that are scheduled (with cadence).
- **Flags**: any agent `paused`/`error`, any company near/over budget.

Pull from `GET /api/companies`, `GET /api/companies/{C}`, `GET /api/companies/{C}/agents`,
`GET /api/companies/{C}/issues`, `GET /api/companies/{C}/routines`. Don't fabricate — report only
what the API returns.
