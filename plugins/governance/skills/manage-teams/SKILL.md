---
name: manage-teams
description: >
  Inspect and modify existing teams on a Paperclip board — check stats (budgets, spend, activity),
  adjust budgets, pause/resume/retire agents, edit instructions, and retire companies. Use when the
  user asks "how is <company> doing", "pause <agent>", "raise the budget", "add/remove an agent", or
  "archive <company>". Requires PAPERCLIP_API_URL + PAPERCLIP_API_KEY (see the governance skill).
---

# Manage teams

```bash
B="${PAPERCLIP_API_URL:?}"; T="${PAPERCLIP_API_KEY:?}"
H=(-H "Authorization: Bearer $T" -H "Content-Type: application/json")
cid(){ curl -sS "$B/api/companies" "${H[@]}" | python3 -c "import sys,json;print(next((c['id'] for c in json.load(sys.stdin) if c['name']=='$1'),''))"; }
```

## Stats / report

```bash
C=$(cid "Lead-Gen Agency")
# Company budget + spend
curl -sS "$B/api/companies/$C" "${H[@]}" | python3 -c "import sys,json;d=json.load(sys.stdin);print('budget',d['budgetMonthlyCents'],'spent',d['spentMonthlyCents'])"
# Per-agent spend / status
curl -sS "$B/api/companies/$C/agents" "${H[@]}" | python3 -c "
import sys,json
for a in json.load(sys.stdin):
    print(a['name'], a['status'], 'spent', a.get('spentMonthlyCents'), 'budget', a.get('budgetMonthlyCents'))"
# Activity
curl -sS "$B/api/companies/$C/issues"   "${H[@]}" | python3 -c "import sys,json;d=json.load(sys.stdin);xs=d if isinstance(d,list) else d.get('issues',[]);print('issues:',len(xs))"
curl -sS "$B/api/companies/$C/routines" "${H[@]}" | python3 -c "import sys,json;d=json.load(sys.stdin);xs=d if isinstance(d,list) else d.get('routines',d.get('items',[]));print('routines:',[ (r.get('title') or r.get('name')) for r in xs])"
```

## Modify

```bash
# Budgets (cents/month)
curl -sS "$B/api/companies/$C" -X PATCH "${H[@]}" -d '{"budgetMonthlyCents":20000}'
curl -sS "$B/api/agents/$AID"  -X PATCH "${H[@]}" -d '{"budgetMonthlyCents":5000}'

# Pause / resume an agent  (status enum: active|paused|idle|running|error|pending_approval|terminated)
curl -sS "$B/api/agents/$AID" -X PATCH "${H[@]}" -d '{"status":"paused"}'
curl -sS "$B/api/agents/$AID" -X PATCH "${H[@]}" -d '{"status":"active"}'

# Rename / retitle / re-point reporting line
curl -sS "$B/api/agents/$AID" -X PATCH "${H[@]}" -d '{"title":"Senior Analyst","reportsTo":"'$HEAD'"}'

# Edit an agent's behavior: rewrite its on-disk AGENTS.md
#   (…/companies/$C/agents/$AID/instructions/AGENTS.md) on the host, or re-import the package.
```

## Add / remove

```bash
# Add an agent (see spin-up-team skill, Recipe C)
# Remove an agent:
curl -sS "$B/api/agents/$AID" -X DELETE "${H[@]}"
#   If it 500s (manager with reports / run history): retire instead
curl -sS "$B/api/agents/$AID" -X PATCH "${H[@]}" -d '{"status":"terminated"}'
```

## Retire a company

Hard-delete is disabled (`companyDeletionEnabled=false`). Archive instead:

```bash
curl -sS "$B/api/companies/$C" -X PATCH "${H[@]}" -d '{"status":"archived"}'
```

## Notes

- "Stats on a team" = the company's budget/spend plus each member agent's spend/status, plus
  issues/routines/goals for activity.
- Pausing a department head does not pause its reports — pause each agent you intend to stop.
