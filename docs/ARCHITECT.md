# The Architect — your permanent point of contact

The **Architect** is a standing agent that lives inside the Paperclip dashboard, in a company called
**Governance HQ**. It is the "company that makes companies": you describe an idea in plain language
and it designs and provisions a team of agents — a whole new business, or a new department inside an
existing one — over the Paperclip API. It keeps working whether or not anyone is at a terminal.

This replaces the old flow where a developer (or a local Claude Code session) had to run scripts to
spin up a business. Now you just chat with the Architect.

## How to use it

1. Open the board → **Governance HQ** company → the issue **"Architecture Board — describe a team,
   I'll build it"**.
2. Post a comment describing what you want:
   - **New business:** *"Spin up a lead-gen business for B2B fintech SaaS."*
   - **New department:** *"Add a 3-person customer-success team to Lead-Gen Agency."*
   - **Modify:** *"Pause outreach in Lead-Gen Agency and raise its budget to $200/mo."*
   - **Stats:** *"How is Lead-Gen Agency doing this week?"*
3. The Architect asks a few structured questions (size, roles, cadence), proposes an org chart for
   your approval, and on confirmation builds it — then reports back with links and when its routines
   start.

The Architecture Board issue is **permanent** — it stays open; every new comment is a new request.

## What it can do (full lifecycle, all over the API)

| You ask for… | The Architect does |
|---|---|
| A new business | Creates a new isolated **company**, imports a template, wires the org + routines |
| A new department/division | Adds a department-head agent + specialists into an **existing company**, reporting to its CEO, with a team routine |
| Stats / a report | Reads budgets, spend, and activity per company and per agent and summarizes |
| Modify a team | Adds/removes agents, edits instructions, retargets routines, changes budgets, pauses/resumes agents |
| Retire a team | Archives a company (hard-delete is disabled on this instance) or removes individual agents |

"Team" means either a **team/department** or a **whole company** — both are covered.

## Two granularities

- **Whole business** = a new **company** in the panel: its own org chart, budget, secrets, and
  isolation. Use for a distinct line of business.
- **Department / division** = new agents added **inside an existing company**, reporting to that
  company's CEO. Use to grow an existing org (e.g. add Customer Success to your agency).

## How a team is structured

Every team the Architect builds follows the governance template:

```
CEO  (single point of contact — reports to you)
├── Head of Department A → Specialist(s)
└── Head of Department B → Specialist(s)
```

with a **daily standup** (weekday mornings) and a **weekly review** (Monday) that run on Paperclip
routines — no human trigger. The generic skeleton lives at `paperclip/companies/_template/`; the
**Lead-Gen Agency** package (`paperclip/companies/lead-gen-agency/`) is a worked-example preset the
Architect can clone for sales/lead-gen businesses.

## Build it yourself / scripting

Everything the Architect does is plain Paperclip API calls, so you can build your own skill or CLI
on top of the same endpoints. The verified recipes (create/modify/stats/import, with correct paths)
are in `paperclip/companies/governance-hq/skills/team-architect/SKILL.md`. To recreate Governance HQ
from scratch on any board, see `scripts/deploy-architect.sh`.

## Live deployment (this instance)

- Board: `https://137-184-151-136.sslip.io`
- Governance HQ company: `bab0fbf1-ccec-427a-a3ce-0aee70b4baf8`
- Architect agent: `1ea8fa51-a804-456c-8661-7f3dcbe9f47e` (opencode_local · OpenRouter claude-sonnet-4.5)
- Architecture Board issue: `GOVAAA-1`

## Notes & limits

- The Architect holds a **board key** in its environment — that's what lets it create/modify across
  companies. Treat the host as trusted; rotate the key periodically.
- **Company hard-delete is disabled** on this instance; retire via archive instead.
- Routine schedules use **weekly** recurrence with weekday filters (Paperclip rejects a `daily`
  frequency combined with weekday filters).
