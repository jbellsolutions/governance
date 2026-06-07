# Governance — Autonomous Lead-Gen + Fulfillment Businesses on Paperclip

Run real, autonomous businesses on a VPS where **you talk to one agent (the CEO)** and a team of
AI agents handles lead generation and fulfillment. You take the sales calls; the system does the
rest. Run **many separate businesses in one panel**, each fully isolated.

This repo is **not** a custom dashboard. The dashboard, budgets, org chart, multi-business
isolation, approvals, and audit trail are all provided by **[Paperclip](https://github.com/paperclipai/paperclip)** —
a mature (69k★, MIT) open-source control plane for managing AI agents. This repo provides the two
things Paperclip doesn't ship out of the box:

1. **A ready-to-run business** — a Paperclip *company package* (`paperclip/companies/lead-gen-agency/`)
   defining a CEO, a Growth team, a Delivery team, their skills, and the recurring schedules that
   make it run every day without you.
2. **An Integrations sidecar** — a small service that gives those agents real tools (lead sourcing,
   email outreach, calendar booking, CRM) via [Composio](https://composio.dev).

---

## Why Paperclip is the foundation

Your requirements map almost one-to-one onto features Paperclip already has:

| You asked for | Paperclip provides |
|---|---|
| Runs on a VPS | Self-hosted Node + embedded Postgres; `authenticated/public` mode behind nginx |
| One point of contact (a CEO) | Agent org charts with a top-level CEO you chat with directly |
| A panel where you watch agents work | The board: live runs, tool-call traces, transcripts, dashboards |
| Many businesses, separate & independent | Native multi-company with **complete data isolation**, unlimited companies |
| Budgets / don't let it run away | Per-agent monthly budgets, hard stops at 100%, board approvals |
| Autonomous daily work | Routines (recurring scheduled tasks) that wake agents on a cron |
| Audit / governance | Immutable audit log, every mutating action traced to an actor |

So the job here isn't to rebuild any of that — it's to **define the business** and **give the agents
hands**.

---

## Architecture

```
        You (owner)  ──chat──►  CEO agent
                                   │  delegates via child issues
              ┌────────────────────┼────────────────────┐
              ▼                                          ▼
        Head of Growth                            Head of Delivery
        ├── SDR (prospecting)                     ├── Fulfillment Specialist
        └── Outreach (sequences + booking)        └── QA Specialist
              │                                          │
              └──────────────► skills call ◄─────────────┘
                                   │
                                   ▼
                    Integrations sidecar (:8080)
              research · email · calendar · CRM  (Composio)
              ───────────────────────────────────────────
   ALL OF THE ABOVE RUNS INSIDE PAPERCLIP (the board / panel / budgets / audit)
```

- **Paperclip** = the panel, the company model, budgets, multi-business isolation, scheduling, audit.
- **Company package** (this repo) = the org chart, agent instructions, business skills, and daily routines.
- **Integrations sidecar** (this repo) = the real tools the agents use to source leads, send email,
  book calls, and track the pipeline.

---

## Quick start (local)

```bash
git clone https://github.com/jbellsolutions/governance.git
cd governance
python3 -m venv .venv && source .venv/bin/activate
pip install -e . -r requirements.txt
cp .env.example .env          # add OPENROUTER_API_KEY and (optional) COMPOSIO_API_KEY

# 1. Start Paperclip (the panel) — the canonical installer:
npx -y paperclipai@latest onboard --yes

# 2. Start the Integrations sidecar (the agents' tools):
python main.py --specialists --port 8080      # serves /health, /delegate
```

Then in the Paperclip board:

1. **Import the business.** Import a company package from this repo:
   - source: `github`, url: `https://github.com/jbellsolutions/governance`,
     path: `paperclip/companies/lead-gen-agency`
   - or via API: `POST /api/companies/:companyId/imports/apply` with
     `{"source":{"type":"github","url":"…"},"target":{"mode":"new_company","newCompanyName":"My Agency"}}`
2. **Set company secrets:** `OPENROUTER_API_KEY`, `COMPOSIO_API_KEY`,
   `INTEGRATIONS_URL=http://127.0.0.1:8080`.
3. **Pick an adapter** for the agents (see below).
4. **Chat with the CEO.** The Growth and Delivery teams start running on their daily routines.

---

## Choosing how agents run (the adapter)

Paperclip runs each agent through an **adapter**. Two supported paths:

### A) `claude_local` — the golden path (recommended)
Each agent runs as a local **Claude Code** session. Paperclip ships first-class support: it injects
the `PAPERCLIP_*` env, mounts the `paperclip` API skill, and streams a rich transcript. Agents get a
real shell + tools. Best autonomy and reliability. Requires Claude Code on the host.

### B) `process` + OpenRouter — single-key path
Every agent driven by one OpenRouter key via `paperclip_worker.py` (this repo). Configure each agent
with the built-in **`process`** adapter:

```
command: python
args:    ["-m", "governance.paperclip_worker"]
env:     { OPENROUTER_API_KEY: "...", AGENT_MODEL: "anthropic/claude-sonnet-4-6" }
```

The worker follows Paperclip's heartbeat protocol (identify → checkout → read context → act via
OpenRouter → comment + status → exit). It's a **lighter** runner than `claude_local` — it reasons and
reports and can call the Integrations sidecar over HTTP, but it has no local shell agent loop. Use it
when you want one model key for everything; use `claude_local` when you want maximum capability.

---

## The business: Lead-Gen Agency

`paperclip/companies/lead-gen-agency/` is a complete, importable company:

```
COMPANY.md                     # the business + goals + required secrets
agents/
  ceo/AGENTS.md                # single point of contact; delegates, escalates sparingly
  head-of-growth/AGENTS.md     # owns top of funnel
  sdr/AGENTS.md                # sources + enriches leads
  outreach/AGENTS.md           # sequences + books calls
  head-of-delivery/AGENTS.md   # owns post-sale delivery
  fulfillment/AGENTS.md        # does the client work
  qa/AGENTS.md                 # reviews before anything ships
teams/{growth,delivery}/TEAM.md
projects/{growth-engine,client-delivery}/PROJECT.md
tasks/
  daily-prospecting/TASK.md    # weekday 08:00 — SDR sources leads
  daily-outreach/TASK.md       # weekday 09:30 — Outreach sends + books
  daily-delivery/TASK.md       # weekday 10:00 — Delivery progresses work
  weekly-review/TASK.md        # Monday 08:00 — CEO reports to you
skills/{lead-generation,outreach-email,crm-pipeline,fulfillment}/SKILL.md
```

**Configure it for your business** by editing two project descriptions in the board (or the files
before import):
- `growth-engine` — your ICP, daily lead target, offer, booking calendar.
- `client-delivery` — what you actually deliver, the quality bar, your SLA.

**Multiple businesses** = import the package again as another new company (or copy the folder, change
`slug`/`name`, and import). Each becomes a fully isolated company in the same Paperclip panel.

---

## VPS deployment

```bash
# On a fresh Ubuntu 22.04+ VPS:
export DOMAIN=board.youragency.com
export OPENROUTER_API_KEY=sk-or-...
export COMPOSIO_API_KEY=...
curl -fsSL https://raw.githubusercontent.com/jbellsolutions/governance/main/scripts/deploy-vps.sh | bash
```

The script installs Node 20 + Python, clones the repo, creates two systemd services
(`paperclip` on :3000, `governance-integrations` on :8080), and — if `DOMAIN` is set — configures
nginx + TLS with SSE-friendly proxy settings. Then claim the instance
(`npx paperclipai auth bootstrap-ceo`) and import the business as above.

Docker alternative: `cd paperclip && docker compose up -d` (Paperclip + Integrations sidecar).

---

## The Integrations sidecar

`python main.py --specialists --port 8080` — a FastAPI service the agents' skills call:

| Endpoint | Purpose |
|---|---|
| `GET /health` | health check |
| `POST /delegate` | run a specialist: `research`, `email`, `calendar`, `crm` (Composio-backed) |
| `GET /entity/{id}/memory` | shared context store |

The business skills (`lead-generation`, `outreach-email`, `crm-pipeline`, `fulfillment`) call
`POST $INTEGRATIONS_URL/delegate` with a `specialist_type` and a `task_spec`. Set
`COMPOSIO_API_KEY` and connect your apps (Gmail, Google Calendar, a CRM, a search provider) in
Composio for the tools to do real work.

---

## What's real vs. what you must wire

Being honest about the gap between "scaffolded" and "earning money on autopilot":

**Real and working now:**
- Paperclip gives you the panel, budgets, multi-business isolation, scheduling, and audit today.
- The company package is valid and importable; the org chart, instructions, and daily routines are real.
- The Integrations sidecar and the OpenRouter worker run and follow the Paperclip protocols.

**You must provide / wire (these need your accounts + judgment):**
- **A Composio account** + connected apps (email sender, calendar, CRM, a lead/search source). Until
  connected, the agents reason but can't send real email or pull real leads — the skills will mark
  tasks `blocked` rather than fabricate data (by design).
- **Your ICP, offer, and deliverable definition** — edit the `growth-engine` and `client-delivery`
  projects. Generic targeting produces generic results.
- **Deliverability + compliance** — warm up a sending domain, respect CAN-SPAM/GDPR, throttle sends.
  The system has guardrails but you own the sending reputation and legal posture.
- **Judgment loop for the first weeks** — watch the board, correct the CEO, tune messaging. Autonomy
  is earned as you confirm each stage works; start with outreach in a review-before-send posture.

This is a governance and operations framework with a real business template — not a money printer.
It removes the daily operational grind so you can focus on sales calls and strategy.

---

## Repo layout

```
paperclip/
  companies/lead-gen-agency/   # the importable business (company package)
  docker-compose.yml           # Paperclip + Integrations sidecar
specialists/                   # the Integrations sidecar (FastAPI + Composio)
  app.py
  tools/composio_tools.py
paperclip_worker.py            # OpenRouter process-adapter worker (path B)
crews/, council/, core/        # earlier CrewAI/council work (optional; see Legacy below)
scripts/deploy-vps.sh          # one-shot VPS provisioning
main.py                        # CLI: --specialists, --status, --council, …
```

### Legacy components

Earlier in development this repo also built a standalone custom panel (`panel.py`, `web/`,
`orchestrator.py`, `business_registry.py`, `event_bus.py`) and a CrewAI crew layer. These work, but
they **duplicate what Paperclip provides natively** and are not the recommended path now that the
system is Paperclip-native. They remain in the repo as a reference / offline fallback. The 5-round
expert council (`council/`) that produced the original architecture also remains and is runnable via
`python main.py --council`.

---

## License

MIT.
