# governance — Claude Code plugin

Spin up and manage teams of AI agents on a [Paperclip](https://github.com/paperclipai/paperclip)
board — whole businesses (companies) or departments (teams inside a company) — from Claude Code or
the terminal. This is the local-operator counterpart to the in-board **Architect** agent: same
governance API, driven from your machine.

## Install

```
/plugin marketplace add jbellsolutions/governance
/plugin install governance
```

Then set your board credentials in the environment:

```bash
export PAPERCLIP_API_URL="https://<your-board-host>"
export PAPERCLIP_API_KEY="pcp_board_…"        # board key with company-management perms
export OPENROUTER_API_KEY="sk-or-…"
```

## What's inside

**Skills** (auto-loaded by Claude when relevant):
- `governance` — setup, concepts, the verified API map, and gotchas. Start here.
- `spin-up-team` — create a new business (preset or custom inline) or a department in an existing
  company; always sets the `opencode_local` engine and creates the team's routine.
- `manage-teams` — stats (budget/spend/activity), budgets, pause/resume/retire, edit instructions,
  archive a company.

**Commands:**
- `/new-business <name and what it does>`
- `/new-department <department> in <company>`
- `/team-stats [company]`

## Concepts

- **Company** = a whole business. **Agent** = a team member. **Team/department** = a department-head
  agent + its reports (`reportsTo`) + a project.
- **Routine** = a cron-scheduled task that wakes an agent — *what makes a team run autonomously*.
- Agents run on `opencode_local` with an OpenRouter model.

See the [main repo](https://github.com/jbellsolutions/governance) for the company templates
(`_template`, `lead-gen-agency`) and the in-board Architect (`governance-hq`).
