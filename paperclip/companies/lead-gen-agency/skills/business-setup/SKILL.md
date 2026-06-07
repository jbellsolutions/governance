---
name: business-setup
description: >
  Guided first-run configuration for a new lead-gen business. Use during onboarding to interview the
  owner with structured interactions and write their answers into the company's projects and secrets.
  Run once per business, then idle.
---

# Business Setup (guided onboarding)

Configure a freshly-created business so it can run autonomously. Collect inputs from the owner with
one `ask_user_questions` interaction, then persist them where the other agents read them.

## The questions (one structured form)

Use `POST /api/issues/{issueId}/interactions` with `kind: "ask_user_questions"`,
`continuationPolicy: "wake_assignee"`:

1. **What do you sell?** (one sentence — the offer the outreach leads with)
2. **Who is the ideal customer?** (industry, company size, buyer role, geography)
3. **What trigger makes a prospect worth contacting?** (funding, hiring, launch, a public pain)
4. **Daily lead target?** (number of qualified leads/day — default 15)
5. **Where should booked calls land?** (calendar / booking link)
6. **What do you deliver after a deal closes?** (the fulfillment scope)
7. **Quality bar / acceptance criteria** (what "good" looks like before anything ships)

Provide sensible defaults so the owner can accept-all quickly.

## Where to store each answer

After the owner responds, write the configuration into the company so every agent picks it up:

- Update the **Growth Engine** project description (`PATCH /api/companies/{companyId}/projects/{id}`
  or the project's issue/document) with: offer, ICP, trigger definition, daily target, booking calendar.
- Update the **Client Delivery** project description with: service definition, quality bar, SLA.
- Post a comment listing the **secrets the owner must set** in the board (you cannot read secret
  values, only flag them): `OPENROUTER_API_KEY`, `COMPOSIO_API_KEY`, `INTEGRATIONS_URL`,
  and (optional) `SLACK_*`, `NOTION_*`, `OBSIDIAN_VAULT_PATH`.

## Connecting tools (tell the owner)

For the agents to take real actions, the owner connects apps in Composio (via the Integrations
sidecar) and sets `COMPOSIO_API_KEY`:

- **Email** (Gmail) — for outreach
- **Calendar** (Google Calendar) — for booking
- **CRM** (HubSpot) — for the pipeline
- **Notion** + **Slack** — optional, for backup and chat

List exactly which are connected vs. missing, and what each unlocks.

## Finish

Confirm the full configuration with a `request_confirmation` interaction. On accept:

- Mark the onboarding task `done`.
- Post a summary to the CEO + owner: the daily routines that now run (prospecting 08:00, outreach
  09:30, delivery 10:00, weekly review Monday), where to watch (the board), and how to talk to the
  team (chat the CEO, or Slack if connected).

The business is now configured and runs on its routines without further prompting.
