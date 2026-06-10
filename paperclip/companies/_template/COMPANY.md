---
name: New Team
description: A generic team-of-agents skeleton — one coordinator (CEO) over two departments, with a daily standup and a weekly review. The Architect renames roles and fills in the mission for your specific idea.
slug: new-team
schema: agentcompanies/v1
version: 1.0.0
license: MIT
authors:
  - name: Governance Template
goals:
  - Run the team's core work on recurring routines without human prompting
  - Coordinate two departments under a single point of contact (the CEO)
  - Escalate to the owner only for decisions a human must make
requirements:
  secrets:
    - OPENROUTER_API_KEY
---

# New Team (generic template)

A minimal, valid org skeleton. It is meant to be **customized** — the Architect (or you) renames the
departments and roles, and rewrites the mission for the actual idea. Out of the box it is a working
3-level org:

```
CEO  (single point of contact — reports to the owner)
├── Head of Department A
│   └── Specialist A
└── Head of Department B
    └── Specialist B
```

## Autonomy model

- **Daily standup** (weekday mornings) — each member posts plan + blockers; the CEO unblocks.
- **Weekly review** (Monday) — the CEO summarizes progress and reports to the owner.

Rename the departments, add or remove specialists, and edit the mission project to fit your business.
Every member reads the **Mission** project for what the team is trying to achieve.
