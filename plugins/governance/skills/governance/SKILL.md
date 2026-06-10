---
name: governance
description: >
  Operate a Paperclip "governance" board from Claude Code or the terminal — spin up and manage teams
  of AI agents, where a "team" is either a whole business (a company) or a department (a team inside
  an existing company). Use when the user wants to create, inspect, modify, or report on companies,
  agents, projects, budgets, or routines on their Paperclip board. Start here for setup, then use the
  spin-up-team and manage-teams skills for specific operations.
---

# Governance (Paperclip control plane)

This skill set lets you drive a Paperclip board's governance API: create businesses and departments,
configure agents, set budgets, and read stats — the same operations the in-board **Architect** agent
performs, but from your own machine (Claude Code, a script, or the `governance` CLI).

## Setup (required)

Set these in the environment before calling the API:

```bash
export PAPERCLIP_API_URL="https://<your-board-host>"          # e.g. https://137-184-151-136.sslip.io
export PAPERCLIP_API_KEY="pcp_board_…"                        # board key with company-management perms
export OPENROUTER_API_KEY="sk-or-…"                           # propagated to agents you create
export GOV_MODEL="openrouter/anthropic/claude-sonnet-4.5"     # default engine model (optional)
```

Quick check: `curl -sS "$PAPERCLIP_API_URL/api/companies" -H "Authorization: Bearer $PAPERCLIP_API_KEY"`
should return your companies as JSON.

## Concepts

- **Company** = a whole business (its own org chart, budget, secrets, isolation).
- **Agent** = a team member. A **team/department** = a department-head agent + its reports (via
  `reportsTo`) + a project.
- **Routine** = a recurring scheduled task that wakes an agent (this is what makes a team run on its
  own). **A team with no routine does not run autonomously.**
- **Engine** = each agent runs on the `opencode_local` adapter with an OpenRouter model.

## API map (verified)

Path rule: *collection* ops (create/list) are nested under `/api/companies/{C}/…`; *single-item* ops
(get/update/delete) are TOP-LEVEL `/api/{resource}/{id}`.

| Action | Call |
|---|---|
| List / read companies | `GET /api/companies` · `GET /api/companies/{C}` |
| Create company | `POST /api/companies` `{name,description}` |
| Update company | `PATCH /api/companies/{C}` `{name?,description?,budgetMonthlyCents?,status?}` |
| List agents | `GET /api/companies/{C}/agents` |
| Read agent (+stats) | `GET /api/agents/{id}` → `budgetMonthlyCents`,`spentMonthlyCents`,`status` |
| Create agent | `POST /api/companies/{C}/agents` |
| Update agent | `PATCH /api/agents/{id}` (status enum: `active`,`paused`,`idle`,`running`,`error`,`pending_approval`,`terminated`) |
| Delete agent | `DELETE /api/agents/{id}` (managers with reports may 500 → set `status:terminated`) |
| Projects | `POST /api/companies/{C}/projects` · `PATCH /api/projects/{id}` |
| Routines | `GET`/`POST /api/companies/{C}/routines` (cron `triggers`) — what makes a team run on its own |
| Activity | `GET /api/companies/{C}/issues` · `/goals` |
| Import a team/business | `POST /api/companies/{C}/imports/apply` |

## Choosing the operation

- **Create a business or a department** → use the **spin-up-team** skill.
- **Stats, modify, budgets, pause/retire, reports** → use the **manage-teams** skill.

## Gotchas (learned the hard way)

- GitHub package import resolves a subdirectory only when the `source.url` points at the
  `…/tree/<branch>/<path>` URL — there is no separate `path` field.
- Safe imports (board key) reject the `process` adapter and the `replace` collision strategy. Force
  `opencode_local` via `adapterOverrides` (which requires `adapterConfig.model`), and use `rename`.
- Company **hard-delete is disabled** by default (`companyDeletionEnabled=false`) → archive via
  `PATCH … {"status":"archived"}`.
- Agent instructions live on the host filesystem (`instructionsFilePath`), written by an import — not
  a plain API field. To give agents real instructions, import a package (inline or github).
