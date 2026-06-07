---
name: crm-pipeline
description: >
  Track leads and deals through pipeline stages. Use to add a lead, move a lead between stages, read
  the current pipeline state, or report funnel metrics. Backed by the Integrations service (Composio
  CRM, e.g. HubSpot) with a Paperclip-issue fallback. Do NOT use for sourcing or sending outreach.
---

# CRM / Pipeline

You maintain the single source of truth for where every lead and deal stands. This is backed by the
**Integrations service** (`INTEGRATIONS_URL`) wrapping a Composio CRM. If no CRM is connected, fall
back to tracking each lead as a Paperclip issue labeled by stage in the Growth Engine project.

## Stages

```
new → sequencing → call-booked → closed-won → (handed to Delivery)
                              ↘ closed-lost
```

## Add a lead

```bash
curl -s "$INTEGRATIONS_URL/delegate" \
  -H 'content-type: application/json' \
  -d '{
    "specialist_type": "crm",
    "task_spec": "Upsert contact jane@acme.com (Jane Doe, CEO, Acme) into the pipeline at stage new. Notes: trigger = <trigger>, source = <url>.",
    "tenant_id": "lead-gen-agency",
    "entity_id": "<your-agent>"
  }'
```

## Move a lead / read the pipeline

Use the same `crm` specialist with a `task_spec` describing the move ("move jane@acme.com to
call-booked") or the read ("list all leads by stage with counts"). Always include the reason for a
stage change in the notes.

## Reporting

When the CEO or Head of Growth needs funnel metrics, return:

- Count of leads at each stage
- Calls booked this period vs last
- Conversion rates between adjacent stages
- Aging leads (stuck >N days in one stage)

## Handoff to Delivery

When a deal reaches `closed-won`, that is the trigger for the Head of Delivery to open a client
delivery effort. Note the closed-won deal clearly so the Delivery team can pick it up.

## Guardrails

- One lead = one pipeline record. Don't create duplicates; upsert by email.
- Every stage change carries a reason. The pipeline is an audit trail, not just a list.
- If the CRM is unreachable, use the Paperclip-issue fallback and flag that the CRM needs
  reconnecting — never silently drop a lead.
