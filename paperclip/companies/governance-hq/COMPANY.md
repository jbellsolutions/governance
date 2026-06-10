---
name: Governance HQ
description: The meta-company that turns any idea into a team of agents. Home of the Architect — your single, permanent point of contact for spinning up and managing businesses and departments.
slug: governance-hq
schema: agentcompanies/v1
version: 1.0.0
license: MIT
authors:
  - name: Governance Template
goals:
  - Convert any idea the owner describes into a working team of agents, on demand
  - Provision both whole businesses (new companies) and departments (teams inside existing companies)
  - Manage the full lifecycle — create, modify, check stats, update — across every company in the panel
  - Keep its own infrastructure healthy (scheduler, backups, chat relays) without human ops
requirements:
  secrets:
    - OPENROUTER_API_KEY
    - PAPERCLIP_API_KEY
    - PAPERCLIP_API_URL
---

# Governance HQ

This is the **control plane** of the whole panel — the "company that makes companies." It contains a
single agent, the **Architect**, which is your permanent point of contact. You never need a terminal
or a developer to stand up a new team again: you describe an idea in the dashboard, and the Architect
designs the org and provisions it over the Paperclip API.

## How you use it

Open the **Architecture Board** issue in this company and post what you want, in plain language:

- "Spin up a lead-gen business for B2B fintech SaaS."
- "Add a 3-person customer-success department to Lead-Gen Agency."
- "How is the Acme company doing this week?" (stats)
- "Pause outreach in Lead-Gen Agency and raise its budget to $200/mo." (modify)

The Architect interviews you with structured questions, proposes an org chart, and on your
confirmation builds it — a brand-new isolated company, or a new team inside an existing one.

## What the Architect can do

- **Create** companies and agents (teams or whole businesses).
- **Modify** any team — add/remove agents, change instructions, retarget routines.
- **Check stats** — budget vs spend per company and per agent, pipeline/activity.
- **Update** companies and agents (status, budgets, adapters, schedules).
- **Self-administer** the host — verify the scheduler, run backups, keep the chat relays alive.

It is the only agent you talk to here. Everything else it delegates or builds.
