# BUILD — Agent-Runnable Setup Guide

**You are an AI agent (Claude Code, Codex, Cursor, etc.). A human gave you this repo and wants a
live, autonomous lead-gen + fulfillment business running on Paperclip.** Follow these steps in order.
Each step is concrete and verifiable. Stop and ask the human only where a step says **[ASK HUMAN]**.

> Goal end state: Paperclip running with the **Governance HQ** company + **Architect** agent (your
> standing point of contact) deployed, the Integrations sidecar up, backups flowing to
> Obsidian/Notion, and (optionally) Slack chat — on a VPS, running every day without prompting. Once
> the Architect is live, you (or the human) spin up businesses/departments by chatting with it on the
> Architecture Board — no more scripts.

> **Fast path for the Architect:** after Paperclip is running, set `PAPERCLIP_API_URL`,
> `PAPERCLIP_API_KEY` (board key), and `OPENROUTER_API_KEY`, then run `scripts/deploy-architect.sh`.
> It imports Governance HQ, configures the Architect on the `opencode_local` engine, and opens the
> Architecture Board. See **[docs/ARCHITECT.md](docs/ARCHITECT.md)**.

---

## 0. Preconditions — collect from the human  [ASK HUMAN]

Ask for these and put them in `.env` (copy from `.env.example`):

- `OPENROUTER_API_KEY` (required)
- `COMPOSIO_API_KEY` (required for real email/calendar/CRM actions)
- Where to run: **a VPS** (recommended: DigitalOcean droplet) or **local** for a test run.
- Optional: `SLACK_BOT_TOKEN`, `NOTION_API_KEY` + `NOTION_PARENT_PAGE_ID`, `OBSIDIAN_VAULT_PATH`.

If anything required is missing, ask once, then proceed with what you have (the system degrades
gracefully and flags what's unconnected).

---

## 1. Install

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e . -r requirements.txt
cp .env.example .env        # then fill in the keys from step 0
```

Verify: `python main.py --status` prints the service + backup-sink checklist.

---

## 2. Start Paperclip (the panel / control plane)

```bash
npx -y paperclipai@latest onboard --yes        # local/trusted
# VPS: npx -y paperclipai@latest onboard --yes --bind lan   (then put nginx+TLS in front)
```

Verify: the Paperclip board is reachable (default http://localhost:3000). For a VPS, claim the
instance: `npx paperclipai auth bootstrap-ceo` and give the human the one-time admin URL. **[ASK HUMAN]**
to open it and sign in.

---

## 3. Start the Integrations sidecar (the agents' tools)

```bash
python main.py --specialists --port 8080 &
```

Verify: `curl -s localhost:8080/health` returns ok. Set `INTEGRATIONS_URL=http://localhost:8080`
as a Paperclip **company secret** in the next step.

---

## 4. Import the business into Paperclip

The business is the company package at `paperclip/companies/lead-gen-agency/`. Import it as a NEW
company so it's fully isolated:

- **Via the board UI:** Import company → source GitHub → this repo URL → path
  `paperclip/companies/lead-gen-agency` → target: new company.
- **Or via API** (get `companyId` of any existing company first, or use the board):

  ```bash
  curl -sS -X POST "$PAPERCLIP_API_URL/api/companies/$CID/imports/apply" \
    -H "Authorization: Bearer $PAPERCLIP_API_KEY" -H "Content-Type: application/json" \
    -d '{"source":{"type":"github","url":"<THIS_REPO_URL>"},
         "include":{"company":true,"agents":true,"projects":true,"issues":true},
         "target":{"mode":"new_company","newCompanyName":"My Agency"},
         "collisionStrategy":"rename"}'
  ```

To spin up **another** business, run `scripts/new-business.sh "Second Agency"` (or import again with a
different `newCompanyName`). Each is isolated.

Verify: the new company appears in the board with 8 agents (CEO, Onboarding Concierge, Head of
Growth, SDR, Outreach, Head of Delivery, Fulfillment, QA) and 5 routines/tasks.

---

## 5. Set company secrets + choose the adapter  [ASK HUMAN where noted]

In the board, set these **company secrets**: `OPENROUTER_API_KEY`, `COMPOSIO_API_KEY`,
`INTEGRATIONS_URL=http://localhost:8080` (+ optional `SLACK_*`, `NOTION_*`, `OBSIDIAN_VAULT_PATH`).

Pick the agent adapter (see README "Choosing how agents run"):
- **`claude_local`** — best autonomy (needs Claude Code on the host). Recommended.
- **`process` + OpenRouter** — one model key for all agents:
  command `python`, args `["-m","governance.paperclip_worker"]`, env `AGENT_MODEL=...`.

---

## 6. Let onboarding configure the business

The **Welcome & Setup** task auto-appears as `todo`, assigned to the Onboarding Concierge. On the
first heartbeat it interviews the human (offer, ICP, trigger, daily target, calendar, deliverable,
quality bar) via a structured Slack/board interaction and writes the answers into the Growth Engine
and Client Delivery projects. **[ASK HUMAN]** to answer that interaction in the board (or Slack).

Verify: when the onboarding task is `done`, the Growth Engine + Client Delivery projects show the
human's real config.

---

## 7. Turn on backups + Slack (optional but recommended)

```bash
python main.py --archivist &      # mirrors every action/thought → Obsidian + Notion
python main.py --slack-relay &    # talk to the CEO from Slack: /ceo <message>
```

Slack app setup: `docs/SLACK.md`.

---

## 8. Deploy live (VPS)

For a fresh Ubuntu VPS, the whole stack installs via:

```bash
DOMAIN=board.example.com OPENROUTER_API_KEY=... COMPOSIO_API_KEY=... bash scripts/deploy-vps.sh
```

This sets up systemd services for Paperclip, the sidecar, the archivist, and the Slack relay, plus
nginx + TLS. See README "VPS deployment". **[ASK HUMAN]** for the domain and to run the one-time
instance-claim command.

---

## Done — what "running" looks like

- The board shows the company; routines fire on schedule (prospecting 08:00, outreach 09:30,
  delivery 10:00, weekly review Monday).
- The human talks only to the CEO (board chat or `/ceo` in Slack).
- Every action/thought is mirrored to Obsidian + Notion.
- The human takes the booked sales calls; the agents do the rest.

If a step failed, report exactly which one and the error — do not claim success you didn't verify.
