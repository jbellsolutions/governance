---
name: Lead-Gen Agency
description: A done-for-you agency that autonomously generates leads, books sales calls onto the owner's calendar, and fulfills client work after deals close.
slug: lead-gen-agency
schema: agentcompanies/v1
version: 1.0.0
license: MIT
authors:
  - name: Governance Template
goals:
  - Fill the owner's calendar with qualified sales calls every week
  - Run outbound prospecting and outreach daily without human intervention
  - Fulfill and deliver client work after deals close, at consistent quality
  - Escalate to the owner only for sales calls, budget approvals, and judgment calls
requirements:
  secrets:
    - OPENROUTER_API_KEY
    - COMPOSIO_API_KEY
    - INTEGRATIONS_URL
---

# Lead-Gen Agency

A fully autonomous agency built to run on Paperclip. The **owner** (a human) does one thing:
takes the sales calls that land on their calendar. Everything else — finding prospects,
enriching them, running outreach, booking calls, and fulfilling the work after a deal closes —
is run by a team of AI agents coordinated by the **CEO**.

## How the owner interacts with it

You talk to **one agent: the CEO.** Open the CEO's chat in the Paperclip board (or comment on
any issue the CEO owns) and give direction in plain language:

- "Focus this week on SaaS founders in fintech."
- "Pause outreach — I'm booked solid through Friday."
- "What's our pipeline look like?"
- "We closed Acme. Kick off fulfillment."

The CEO delegates to the Growth and Delivery teams, who run their own recurring routines.
You never have to talk to the individual agents unless you want to.

## Org structure

```
CEO  (single point of contact — reports to the owner)
├── Head of Growth
│   ├── SDR / Prospector       — finds + enriches leads
│   └── Outreach Specialist    — runs sequences, books calls
└── Head of Delivery
    ├── Fulfillment Specialist — does the client work
    └── QA Specialist          — reviews before anything ships
```

## Autonomy model

Recurring tasks (Paperclip routines) drive daily operation with no human trigger:

- **Daily prospecting** (weekday mornings) — SDR finds and enriches new leads
- **Daily outreach** (weekday) — Outreach sends sequences and books calls
- **Daily delivery standup** (weekday) — Delivery progresses active client work
- **Weekly review** (Monday) — CEO reviews pipeline, spend, and priorities, then reports to the owner

Budgets, approvals, and audit are handled natively by Paperclip. Agents auto-pause at 100% budget
and focus only on critical work above 80%.
