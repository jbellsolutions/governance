---
name: Daily Outreach
assignee: outreach
project: growth-engine
schedule:
  timezone: America/Chicago
  startsAt: 2026-06-08T09:30:00-05:00
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
      hour: 9
      minute: 30
---

Advance every active lead one step and book calls where prospects are warm.

- Pull leads at stage `new` and `sequencing` from the pipeline.
- Send the next sequence step using the `outreach-email` skill (personalized to each lead's trigger).
- For positive replies, propose times and book against the owner's calendar.
- Move booked leads to `call-booked` and notify the Head of Growth.
- Advance non-responders; mark hard "no" as `closed-lost` with a reason.

Every booked call must include a context note so the owner can walk in prepared.
