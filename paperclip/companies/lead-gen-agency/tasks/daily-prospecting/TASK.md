---
name: Daily Prospecting
assignee: sdr
project: growth-engine
schedule:
  timezone: America/Chicago
  startsAt: 2026-06-08T08:00:00-05:00
  recurrence:
    frequency: weekly
    interval: 1
    weekdays:
      - monday
      - tuesday
      - wednesday
      - thursday
      - friday
    time:
      hour: 8
      minute: 0
---

Source and enrich today's batch of qualified leads against the Growth Engine ICP.

- Read the current ICP and daily target from the Growth Engine project.
- Use the `lead-generation` skill to source prospects.
- Enrich each with a verified contact and one specific outreach trigger.
- Add qualified leads to the pipeline at stage `new`.
- Comment with counts (sourced / qualified) and any notable ICP signal.

Hand the qualified leads to the Outreach Specialist via the pipeline.
