---
name: spin-up-team
description: >
  Provision a new team of agents on a Paperclip board — either a whole new business (a new isolated
  company) or a new department (agents added inside an existing company). Use when the user says
  things like "spin up a business for X", "create a team that does Y", or "add a Z department to
  <company>". Requires PAPERCLIP_API_URL, PAPERCLIP_API_KEY, OPENROUTER_API_KEY (see the governance
  skill for setup).
---

# Spin up a team

Provision a business or a department. Always (1) set every agent's engine to `opencode_local`,
(2) create the team's routine(s) so it runs autonomously, and (3) report what you built.

```bash
B="${PAPERCLIP_API_URL:?}"; T="${PAPERCLIP_API_KEY:?}"; OR="${OPENROUTER_API_KEY:?}"
MODEL="${GOV_MODEL:-openrouter/anthropic/claude-sonnet-4.5}"
H=(-H "Authorization: Bearer $T" -H "Content-Type: application/json")
REPO="https://github.com/jbellsolutions/governance"
```

## A. New business (preset, fastest)

Import a committed preset as a new company. `_template` is the generic CEO+2-departments skeleton;
`lead-gen-agency` is a sales/lead-gen preset.

```bash
PRESET="paperclip/companies/_template"      # or paperclip/companies/lead-gen-agency
NAME="Acme Research"
ANY=$(curl -sS "$B/api/companies" "${H[@]}" | python3 -c 'import sys,json;xs=json.load(sys.stdin);print(xs[0]["id"])')
curl -sS "$B/api/companies/$ANY/imports/apply" "${H[@]}" -d "{
  \"source\": { \"type\": \"github\", \"url\": \"$REPO/tree/main/$PRESET\" },
  \"include\": { \"company\": true, \"agents\": true, \"projects\": true, \"issues\": true, \"skills\": true },
  \"target\": { \"mode\": \"new_company\", \"newCompanyName\": \"$NAME\" },
  \"collisionStrategy\": \"rename\",
  \"adapterOverrides\": { \"ceo\": $(engine_override), \"lead-a\": $(engine_override), \"lead-b\": $(engine_override),
                           \"specialist-a\": $(engine_override), \"specialist-b\": $(engine_override) }
}"
```

where `engine_override` is:

```bash
engine_override(){ echo "{\"adapterType\":\"opencode_local\",\"adapterConfig\":{\"cwd\":\"/home/paperclip\",\"model\":\"$MODEL\",\"env\":{\"OPENROUTER_API_KEY\":\"$OR\"}}}"; }
```

(Keys in `adapterOverrides` are the agent **slugs** from the package's `agents/<slug>/`.)

## B. New business (custom, generated inline)

For a bespoke org, generate the package files and import them inline — no GitHub needed. This writes
each agent's `AGENTS.md` to disk (real instructions). Build a `files` map of `COMPANY.md`,
`agents/<slug>/AGENTS.md`, `projects/<slug>/PROJECT.md`, `tasks/<slug>/TASK.md` (routines —
`schedule.recurrence.frequency: weekly` with `weekdays`; **`daily` is rejected**), `skills/...`.

```bash
curl -sS "$B/api/companies/$ANY/imports/apply" "${H[@]}" -d @- <<JSON
{ "source": { "type":"inline", "rootPath":".", "files": {
    "COMPANY.md": { "content": $(jq -Rs . < pkg/COMPANY.md) },
    "agents/ceo/AGENTS.md": { "content": $(jq -Rs . < pkg/agents/ceo/AGENTS.md) }
    /* … one entry per file … */
  } },
  "include": { "company":true, "agents":true, "projects":true, "issues":true, "skills":true },
  "target": { "mode":"new_company", "newCompanyName":"$NAME" },
  "collisionStrategy": "rename",
  "adapterOverrides": { "ceo": $(engine_override) /* …per slug… */ }
}
JSON
```

## C. New department (inside an existing company)

```bash
C=$(curl -sS "$B/api/companies" "${H[@]}" | python3 -c 'import sys,json;print(next(c["id"] for c in json.load(sys.stdin) if c["name"]=="Lead-Gen Agency"))')
CEO=$(curl -sS "$B/api/companies/$C/agents" "${H[@]}" | python3 -c 'import sys,json;print(next(a["id"] for a in json.load(sys.stdin) if a.get("role")=="ceo" or "Chief Executive" in (a.get("title") or "")))')

# Department head
HEAD=$(curl -sS "$B/api/companies/$C/agents" "${H[@]}" -d "{
  \"name\":\"Head of Research\",\"title\":\"Head of Research\",\"role\":\"general\",
  \"reportsTo\":\"$CEO\",\"adapterType\":\"opencode_local\",
  \"adapterConfig\":{\"cwd\":\"/home/paperclip\",\"model\":\"$MODEL\",\"env\":{\"OPENROUTER_API_KEY\":\"$OR\"}}
}" | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')

# Specialist(s) under the head
curl -sS "$B/api/companies/$C/agents" "${H[@]}" -d "{
  \"name\":\"Research Analyst\",\"title\":\"Research Analyst\",\"role\":\"general\",
  \"reportsTo\":\"$HEAD\",\"adapterType\":\"opencode_local\",
  \"adapterConfig\":{\"cwd\":\"/home/paperclip\",\"model\":\"$MODEL\",\"env\":{\"OPENROUTER_API_KEY\":\"$OR\"}}
}"
```

> Direct agent creation gives the new agents a **default instruction file**. To give them rich,
> role-specific instructions, instead import a small inline department package
> (`target.mode: existing_company`) — that writes proper `AGENTS.md` files and creates the routine.

## Create a routine directly (API)

If you built the team by direct agent creation (not a package import with `tasks/*.md`), create the
routine explicitly so the team runs autonomously. Routines use **cron** triggers:

```bash
curl -sS "$B/api/companies/$C/routines" "${H[@]}" -d "{
  \"title\": \"Weekly Review\",
  \"assigneeAgentId\": \"$CEO\",
  \"description\": \"Weekly review + report to the owner.\",
  \"status\": \"active\",
  \"priority\": \"medium\",
  \"triggers\": [{ \"kind\": \"schedule\", \"enabled\": true,
                   \"timezone\": \"America/Chicago\",
                   \"cronExpression\": \"0 9 * * 1\" }]   // Mon 09:00; weekdays = 0 8 * * 1,2,3,4,5
}"
```

## Always finish with

1. **Create the routine** — via the import's `tasks/*.md`, or the direct API call above. Verify:
   `GET /api/companies/$C/routines` is non-empty (each routine's `triggers[].nextRunAt` shows the
   first fire).
2. **Confirm engine** on every new agent: `GET /api/agents/{id}` → `adapterType: opencode_local`.
3. **Report**: company/department, agent names + IDs, routine + first-fire, and any secrets/Composio
   apps the owner must connect.
