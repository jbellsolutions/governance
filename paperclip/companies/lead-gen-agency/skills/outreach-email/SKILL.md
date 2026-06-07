---
name: outreach-email
description: >
  Run personalized outbound email sequences and book sales calls onto the owner's calendar. Use
  when sending a first touch, a follow-up, or scheduling a booked call. Calls the Integrations
  service (Composio-backed email + calendar). Do NOT use for sourcing leads (use lead-generation).
---

# Outreach & Booking

You turn qualified leads into booked calls. Sending and scheduling happen through the
**Integrations service** (`INTEGRATIONS_URL`), which wraps Composio email (Gmail) and calendar.

## Send an outreach email

```bash
curl -s "$INTEGRATIONS_URL/delegate" \
  -H 'content-type: application/json' \
  -d '{
    "specialist_type": "email",
    "task_spec": "Send a first-touch email to jane@acme.com. Open with this specific trigger: <the SDR-found trigger>. One-sentence offer: <offer from Growth Engine>. Soft CTA asking for a 15-min call. Keep it under 90 words, no fluff.",
    "tenant_id": "lead-gen-agency",
    "entity_id": "outreach"
  }'
```

## Book a call on the owner's calendar

```bash
curl -s "$INTEGRATIONS_URL/delegate" \
  -H 'content-type: application/json' \
  -d '{
    "specialist_type": "calendar",
    "task_spec": "Check the owner calendar for open 30-min slots over the next 3 business days, propose 3 times to jane@acme.com, and on confirmation create the event with a context note: <who they are, the trigger, the offer>.",
    "tenant_id": "lead-gen-agency",
    "entity_id": "outreach"
  }'
```

## Sequence rules

- **First touch**: lead with the lead's specific trigger. Personalized, short, one clear ask.
- **Follow-ups**: spaced and additive — each adds a new angle or proof point. Never "just bumping."
- **Cap** the sequence (default 4 touches). After that, mark `closed-lost: no-response`.
- **Positive reply** → propose times and book. Only offer slots the calendar actually shows free.
- **Hard no** → `closed-lost` with the reason. **Out of office / later** → snooze and re-sequence.

## After a booking

1. Move the lead to `call-booked` in the pipeline (`crm-pipeline` skill).
2. Attach the context note so the owner can prep.
3. Notify the Head of Growth, who confirms it up to the CEO → the owner.

## Guardrails

- Respect daily send limits the Integrations service enforces; never spam.
- Never send to `needs-verification` emails — send those back to the SDR.
- If the service is unavailable, mark the task `blocked` with the error. Do not claim sends you
  didn't make.
