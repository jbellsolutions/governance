---
name: team-architect
description: >
  Provision and manage teams of agents on Paperclip from plain-language ideas. Use to create a new
  company (a whole business) or a department (a team inside an existing company), and to modify,
  inspect, and update companies and agents. Contains the exact, verified Paperclip API recipes.
---

# Team Architect

This skill is the Architect's hands. Every call uses the board key and base URL from your own
environment:

```bash
B="${PAPERCLIP_API_URL:?}"          # e.g. https://137-184-151-136.sslip.io
T="${PAPERCLIP_API_KEY:?}"          # board key with company-management permission
H=(-H "Authorization: Bearer $T" -H "Content-Type: application/json")
OR="${OPENROUTER_API_KEY:?}"        # propagated to every agent you create
MODEL="openrouter/anthropic/claude-sonnet-4.5"
```

## API map (verified)

**Path rule:** *collection* ops (create/list) are nested under `/api/companies/{C}/…`; *single-item*
ops (get/update/delete) are **top-level** `/api/{resource}/{id}`.

| Action | Call |
|---|---|
| List companies | `GET /api/companies` |
| Read company | `GET /api/companies/{C}` |
| Create company | `POST /api/companies` `{name,description,metadata?}` |
| Update company | `PATCH /api/companies/{C}` `{name?,description?,budgetMonthlyCents?,status?}` |
| List agents | `GET /api/companies/{C}/agents` |
| Read agent (+stats) | `GET /api/agents/{id}` → `budgetMonthlyCents`,`spentMonthlyCents`,`status` |
| Create agent | `POST /api/companies/{C}/agents` |
| Update agent | `PATCH /api/agents/{id}` |
| Delete agent | `DELETE /api/agents/{id}` |
| Projects | `POST /api/companies/{C}/projects` · `PATCH /api/projects/{id}` |
| Routines / activity | `GET /api/companies/{C}/routines` · `/issues` · `/goals` |
| Import a package | `POST /api/companies/{C}/imports/apply` |
| Ask the owner | `POST /api/issues/{issueId}/interactions` |

> Company **hard-delete is disabled** on this instance (`companyDeletionEnabled=false`). To retire a
> company, archive it via `PATCH /api/companies/{C}` `{"status":"archived"}` instead.

## Mechanism: how instructions reach an agent

An agent's behavioral instructions are **not** an API field — they live on the host at
`…/companies/{C}/agents/{id}/instructions/AGENTS.md`, wired through
`adapterConfig.instructionsFilePath`. The reliable way to set them is an **import** that carries the
`AGENTS.md` files. You have two import sources:

- **inline** — put the package files directly in the request body (`source.type:"inline"`). Best for
  custom orgs you generate on the fly. No GitHub needed.
- **github** — pull a committed preset (`source.type:"github"`). Best for known templates
  (`_template`, `lead-gen-agency`).

After an import, **set each new agent's engine** with a *merge* PATCH (never replace — that would
drop the `instructionsFilePath`).

## Recipe A — New business (new company)

1. **Generate the package** in memory: `COMPANY.md`, one `agents/<slug>/AGENTS.md` per role
   (frontmatter `name`,`title`,`reportsTo`,`skills`; body = role instructions), `projects/*/PROJECT.md`,
   `tasks/*/TASK.md` (routines — use `schedule.recurrence.frequency: weekly` with `weekdays`; **daily
   frequency is rejected**), and any `skills/*/SKILL.md`. Keep a single CEO at the top
   (`reportsTo: null`) as the owner's point of contact.

2. **Idempotency:** `GET /api/companies` and skip if the name already exists.

3. **Inline-import** as a new company:

```bash
curl -sS "$B/api/companies/$ANY_C/imports/apply" "${H[@]}" -d @- <<JSON
{
  "source": { "type": "inline", "rootPath": ".", "files": {
    "COMPANY.md": { "content": $(jq -Rs . < /tmp/pkg/COMPANY.md) },
    "agents/ceo/AGENTS.md": { "content": $(jq -Rs . < /tmp/pkg/agents/ceo/AGENTS.md) }
    /* …one entry per file… */
  }},
  "include": { "company": true, "agents": true, "projects": true, "issues": true, "skills": true },
  "target": { "mode": "new_company", "newCompanyName": "$NAME" },
  "collisionStrategy": "rename"
}
JSON
```

(For a preset instead of generated files, swap `source` for
`{ "type":"github", "url":"https://github.com/jbellsolutions/governance", "path":"paperclip/companies/_template" }`
— or `…/lead-gen-agency` for the lead-gen preset.)

4. **Set the engine on every new agent** (merge PATCH):

```bash
for AID in $(curl -sS "$B/api/companies/$NEW_C/agents" "${H[@]}" | jq -r '.[].id'); do
  curl -sS "$B/api/agents/$AID" -X PATCH "${H[@]}" -d "{
    \"adapterType\": \"opencode_local\",
    \"adapterConfig\": { \"cwd\": \"/home/paperclip\", \"model\": \"$MODEL\",
                          \"env\": { \"OPENROUTER_API_KEY\": \"$OR\" } },
    \"status\": \"active\"
  }"
done
```

5. **Verify** routines exist: `GET /api/companies/$NEW_C/routines`. Report the org + first run time to
   the owner on the Architecture Board.

## Recipe B — New department (team inside an existing company)

1. Find the target company and its CEO:

```bash
C=$(curl -sS "$B/api/companies" "${H[@]}" | jq -r '.[]|select(.name=="Lead-Gen Agency")|.id')
CEO=$(curl -sS "$B/api/companies/$C/agents" "${H[@]}" | jq -r '.[]|select(.role=="ceo" or .title|test("Chief Executive"))|.id' | head -1)
```

2. Inline-import the department into that company (`target.mode: existing_company`). Put the
   department head at the top of the package with `reportsTo` pointing at the CEO slug, its
   specialists under it, a `projects/<dept>/PROJECT.md`, and a weekly `tasks/<dept>-review/TASK.md`:

```bash
curl -sS "$B/api/companies/$C/imports/apply" "${H[@]}" -d @- <<JSON
{
  "source": { "type": "inline", "rootPath": ".", "files": { /* dept package files */ } },
  "include": { "company": false, "agents": true, "projects": true, "issues": true, "skills": true },
  "target": { "mode": "existing_company", "companyId": "$C" },
  "collisionStrategy": "rename"
}
JSON
```

3. Wire reporting + engine: ensure the new department head's `reportsTo` is the CEO's id
   (`PATCH /api/agents/{head}` `{"reportsTo":"$CEO"}`), and run the engine-PATCH loop from Recipe A
   over the newly created agents only.

## Recipe C — Modify / stats / update

- **Stats:** `GET /api/companies/$C` (company budget/spend) and `GET /api/agents/$AID`
  (`spentMonthlyCents`/`budgetMonthlyCents`/`status`); `GET /api/companies/$C/issues|routines|goals`
  for activity. Summarize on the board.
- **Budget:** `PATCH /api/companies/$C {"budgetMonthlyCents":20000}` or
  `PATCH /api/agents/$AID {"budgetMonthlyCents":5000}`.
- **Pause/resume an agent:** `PATCH /api/agents/$AID {"status":"inactive"}` / `{"status":"active"}`.
- **Edit instructions:** rewrite the agent's on-disk `AGENTS.md`
  (`…/companies/$C/agents/$AID/instructions/AGENTS.md`) via your bash tool, or re-import with
  `collisionStrategy:"replace"`.
- **Retire a company:** `PATCH /api/companies/$C {"status":"archived"}` (hard-delete is disabled).
- **Remove an agent:** `DELETE /api/agents/$AID`.

## Recipe D — Self-administration (host)

Run via your bash tool (you are the `paperclip` user):

```bash
systemctl is-active paperclip || sudo systemctl restart paperclip   # scheduler/server
pgrep -f 'main.py --archivist' || (cd /opt/governance && nohup python main.py --archivist &)   # backups
pgrep -f 'main.py --slack-relay' || (cd /opt/governance && nohup python main.py --slack-relay &)  # Slack
# restore human SSH on request:
# echo "ssh-ed25519 AAAA... owner" >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys
```

Report only exceptions to the board.

## Interview template (ask_user_questions)

```bash
curl -sS "$B/api/issues/$BOARD_ISSUE/interactions" "${H[@]}" -d '{
  "kind": "ask_user_questions",
  "idempotencyKey": "architect:<req-id>:v1",
  "title": "Design your team",
  "continuationPolicy": "wake_assignee",
  "payload": { "version": 1, "questions": [
    {"id":"kind","prompt":"New business or a department in an existing company?","selectionMode":"single",
     "options":[{"id":"business","label":"New business (its own company)"},
                {"id":"dept","label":"Department inside an existing company"}]},
    {"id":"purpose","prompt":"One line: what is this team for?","selectionMode":"single",
     "options":[{"id":"custom","label":"Type it"}]},
    {"id":"size","prompt":"How many agents?","selectionMode":"single",
     "options":[{"id":"s","label":"3–5"},{"id":"m","label":"6–8"},{"id":"l","label":"9+"}]},
    {"id":"cadence","prompt":"How often should it sync?","selectionMode":"single",
     "options":[{"id":"daily","label":"Daily standup + weekly review"},
                {"id":"weekly","label":"Weekly review only"}]}
  ]}
}'
```

Each question requires `id`, `prompt`, `selectionMode` (`single`|`multi`), and `options[]`. Provide
defaults; keep it to the few things only the owner can decide.
