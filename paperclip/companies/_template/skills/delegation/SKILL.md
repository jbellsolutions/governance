---
name: delegation
description: >
  How to delegate, track, and escalate work inside a team using Paperclip issues. Use when a manager
  (CEO or department head) needs to hand work to a report and follow it to completion, or when any
  agent needs to escalate a decision to the owner.
---

# Delegation

Coordinate work through Paperclip issues instead of doing everything yourself.

## Delegating down

- Create a **child issue** for the work, assigned to the report who should do it. Set `parentId` to
  your current issue (and `goalId` if it ladders to a goal) so the work is traceable.
- State the **objective** and the **constraints/quality bar**, not the step-by-step. Let the report
  decide how.
- Don't poll. The report wakes on its own heartbeat, does the work, and comments back. Review when it
  reports `in_review` or asks a question.

## Tracking

- Watch your child issues' status (`todo` → `in_progress` → `in_review` → `done`).
- If something sits in `blocked`, read the blocker and clear it (provide the input, make the call, or
  escalate it).

## Escalating up / to the owner

- Only escalate decisions a human (or your manager) must make — budget, strategy, judgment, anything
  off-plan or reputational.
- Escalate to the **owner** with a Paperclip issue-thread interaction (`ask_user_questions` or
  `request_confirmation`) on the owner-facing issue — never bare free-text. Give a default
  recommendation so the owner can accept quickly.
- Everything an agent can decide, decide. Never ask a human to do what an agent could do.
