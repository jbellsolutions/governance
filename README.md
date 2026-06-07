# Governance — Autonomous Agent Business Platform

A production-grade system for running fully autonomous AI businesses. You talk to one agent (the CEO). The CEO delegates to specialized teams. You watch everything happen live in a web panel, and can interject at any time.

Multiple businesses run in the same panel, each fully isolated with their own memory, budgets, and audit trail.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   GOVERNANCE PANEL                       │
│         (Web UI — real-time activity + CEO chat)        │
│                  http://localhost:8000                   │
└──────────────────────────┬──────────────────────────────┘
                           │  REST + SSE
┌──────────────────────────▼──────────────────────────────┐
│                   CEO ORCHESTRATOR                       │
│     Single conversational entry point per business.      │
│     Delegates to teams via tool calls. State persists.   │
└────────┬──────────────┬──────────────────────┬──────────┘
         │              │                      │
   ┌─────▼─────┐  ┌─────▼─────┐        ┌──────▼──────┐
   │  Exec     │  │  Sales    │        │  Marketing  │
   │  Team     │  │  Team     │        │  Team       │
   │ CEO·CMO   │  │ SDR·AE    │        │ Content·SEO │
   │ CTO·CFO   │  │ CSM       │        │ PaidAds     │
   └─────┬─────┘  └─────┬─────┘        └──────┬──────┘
         └──────────────┼──────────────────────┘
                        │
         ┌──────────────▼──────────────┐
         │      GOVERNANCE LAYER       │
         │  Budget gates (Paperclip)   │
         │  Audit stream (JSONL)       │
         │  State / memory (SQLite)    │
         │  Event bus (SSE)            │
         └──────────────┬──────────────┘
                        │
         ┌──────────────▼──────────────┐
         │   OPENSWARM SPECIALISTS     │
         │  Slack · Email · CRM · etc  │
         │  (Composio 10k+ apps)       │
         │  http://localhost:8080      │
         └─────────────────────────────┘
```

### How the three layers work together

| Layer | Platform | Responsibility |
|-------|----------|----------------|
| Dashboard & financial controls | **Paperclip** (optional) | Budget pre-flight, agent spend limits, immutable audit logs, org chart |
| Orchestration & memory | **CrewAI** | Crew execution, task delegation, SQLite state, checkpoint/resume |
| Specialist integrations | **OpenSwarm / Agency Swarm** | Slack, Gmail, HubSpot, Calendar via Composio |

The three platforms fill gaps the others don't cover:
- **Paperclip alone**: no execution engine, no memory, no integrations
- **CrewAI alone**: no budget controls, no visual dashboard, limited integrations
- **OpenSwarm alone**: no persistence, no financial guardrails, no dashboard

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/governance.git
cd governance
python -m venv .venv && source .venv/bin/activate
pip install -e .
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and add your keys
```

Required:
```env
OPENROUTER_API_KEY=sk-or-...
```

Optional (for full feature set):
```env
SLACK_BOT_TOKEN=xoxb-...
PAPERCLIP_URL=http://localhost:3000
COMPOSIO_API_KEY=...
```

### 3. Launch the panel

```bash
python main.py --panel
```

Open **http://localhost:8000** in your browser.

---

## Using the Panel

### Create a business

1. Click **+** in the sidebar
2. Enter a name (e.g., "Acme Corp")
3. Select initial teams (Executive is default)
4. Click **Create Business**

The business appears in the sidebar with its tenant ID. All state, memory, and logs are isolated per business.

### Talk to the CEO

Type in the chat at the bottom. The CEO responds conversationally. When the CEO delegates to a team, you'll see it appear in the live event feed on the right.

Example messages:
- *"Give me a status update on the business"*
- *"Run a full executive review"*
- *"Launch a marketing campaign targeting SaaS founders"*
- *"Review our sales pipeline and identify blockers"*

### Watch agents work

The event feed shows every step in real-time:
- `agent_step` — a specific agent used a tool or completed a task
- `team_start` — CEO delegated to a team
- `team_complete` — team finished with a result preview
- `user_message` / `ceo_response` — conversation events

Color indicators: blue = info, green = success, yellow = warning, red = error.

### Multiple businesses

Each business is fully isolated. Switch between them in the sidebar — the event feed and chat context switch instantly. Businesses share no state, memory, or budget.

### Add/remove teams

Click **+ Team** in the business header and enter the team type:
- `exec_team` — CEO, CMO, CTO, CFO
- `sales` — SDR, AE, CSM
- `marketing` — Content, SEO, Paid Ads

---

## CLI Reference

```bash
python main.py --panel                      # Web panel (primary)
python main.py --status                     # Health check all services
python main.py --council                    # Run 5-round expert deliberation
python main.py --business exec_team         # Run exec crew directly (CLI)
python main.py --business sales             # Run sales crew directly (CLI)
python main.py --business marketing         # Run marketing crew directly (CLI)
python main.py --specialists --port 8080    # Start OpenSwarm specialist layer
python main.py --serve --port 8000          # Start governance API (no UI)
python main.py --slack                      # Start Slack bridge on :3001
```

---

## API Reference

All endpoints are available at **http://localhost:8000/docs** (Swagger UI).

### Businesses

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/businesses` | List all businesses |
| `POST` | `/businesses` | Create a business |
| `GET` | `/businesses/{id}` | Get business details |
| `DELETE` | `/businesses/{id}` | Delete a business |
| `POST` | `/businesses/{id}/teams` | Add a team |
| `DELETE` | `/businesses/{id}/teams/{type}` | Remove a team |

### CEO Chat

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/businesses/{id}/chat` | Send message to CEO |
| `DELETE` | `/businesses/{id}/chat` | Reset conversation history |

Body: `{ "message": "your message here" }`

### Real-time Events

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/stream/{business_id}` | SSE stream for a business |
| `GET` | `/stream/all` | SSE stream for all businesses |
| `GET` | `/events` | Recent event history (REST) |

Query params for `/stream`: `since=<unix_timestamp>` to replay events from a point in time.

### System

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/status` | Service status |

---

## Configuration

All settings via environment variables (`.env` file supported):

### LLM Models (via OpenRouter)

```env
OPENROUTER_API_KEY=sk-or-...       # Required
OPENAI_BASE_URL=https://openrouter.ai/api/v1

EXEC_MODEL=anthropic/claude-sonnet-4-6       # CEO + executive team
SALES_MODEL=moonshotai/kimi-2                # Sales team
MARKETING_MODEL=moonshotai/kimi-2            # Marketing team
EXPERT_MODEL=deepseek/deepseek-chat-v4       # Council experts
SPECIALIST_MODEL=deepseek/deepseek-chat-v4   # OpenSwarm specialists
```

Any OpenRouter-supported model works. See [openrouter.ai/models](https://openrouter.ai/models).

### Storage

```env
STATE_DB_PATH=/data/governance.db    # SQLite path (default: ./data/governance.db)
AUDIT_LOG_PATH=/data/audit.jsonl     # Fallback audit log (default: ./data/audit.jsonl)
```

### Paperclip (optional financial controls)

```env
PAPERCLIP_URL=http://localhost:3000   # Paperclip API URL
BUDGET_OVERRIDE=false                 # Set to "true" to bypass all budget gates
```

When Paperclip is unreachable the system **fails open** — all agent actions are allowed and logged locally.

### Slack (optional)

```env
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
```

### Composio (optional — 10,000+ app integrations)

```env
COMPOSIO_API_KEY=...
COMPOSIO_MAX_CONCURRENT=10    # max concurrent Composio actions per tenant
```

---

## Governance Contracts

The system implements 5 API contracts between layers:

### Contract 1: Budget Pre-flight
Before any expensive action, CrewAI asks Paperclip for approval:
```
POST /api/v1/budget/preflight
{ tool_name, estimated_cost_usd, entity_id, tenant_id }
→ { decision: "allow" | "deny" }
```
If Paperclip is unreachable, a circuit breaker opens after 5 failures and allows all actions (fail-open) with a 60-second cooldown.

### Contract 2: Audit Event Stream
Every agent step is streamed to Paperclip's immutable log:
```
POST /api/v1/audit/event
{ step_id, agent_id, tool_calls, entity_state_hash, timestamp, tenant_id }
```
Falls back to a local `.jsonl` file if Paperclip is unreachable.

### Contract 3: Checkpoint Suspend
Paperclip can pause a crew via webhook:
```
POST /webhook/budget-exceeded
{ workflow_id, reason, checkpoint_id }
```
GovernanceCrew checks for this pause signal before every `kickoff()`. Resume via Slack or the REST API.

### Contract 4: Context Bridge
OpenSwarm specialists query CrewAI entity memory before acting:
```
GET /entity/{entity_id}/memory?tenant_id=...
→ { entity_id, context: { ... } }
```

### Contract 5: Specialist Handoff
CrewAI delegates Composio-backed tasks to OpenSwarm:
```
POST /delegate
{ task_spec, specialist_type, tenant_id, entity_id, context_snapshot }
→ { delegation_id, status, result }
```
Specialist types: `slack`, `email`, `calendar`, `crm`, `research`, `code`

---

## Teams

### Executive Team (`exec_team`)
Agents: CEO, CMO, CTO, CFO

Tasks run per cycle:
1. **Strategy Review** (CEO) — KPIs, top priorities, escalations
2. **Marketing Plan** (CMO) — targeting, channels, budget
3. **Tech Review** (CTO) — reliability, cost, technical decisions
4. **Financial Review** (CFO) — burn rate, runway, budget alerts

Model: `EXEC_MODEL` (default `anthropic/claude-sonnet-4-6`)

### Sales Team (`sales`)
Agents: SDR, AE, CSM

Tasks:
1. **Prospect & Outreach** (SDR)
2. **Pipeline & Close** (AE)
3. **Retention & Expansion** (CSM)

Model: `SALES_MODEL` (default `moonshotai/kimi-2`)

### Marketing Team (`marketing`)
Agents: Content, SEO, Paid Ads

Tasks:
1. **Content Calendar** (Content)
2. **SEO Audit** (SEO)
3. **Campaign Review** (Paid Ads)

Model: `MARKETING_MODEL` (default `moonshotai/kimi-2`)

---

## VPS Deployment

### Prerequisites
- Ubuntu 22.04+ VPS (2 vCPU / 4 GB RAM minimum)
- Python 3.11+
- `git`, `nginx`

### Automated deploy

```bash
# On your local machine
export VPS_HOST=user@your-vps-ip
bash scripts/deploy.sh
```

The script:
1. SSHs into the VPS
2. Clones / pulls the repo
3. Installs dependencies in a venv
4. Sets up a systemd service for the panel
5. Configures nginx as a reverse proxy

### Manual setup

```bash
# On VPS
git clone https://github.com/YOUR_USERNAME/governance.git /opt/governance
cd /opt/governance
python3 -m venv .venv && source .venv/bin/activate
pip install -e . -r requirements.txt

# Configure
cp .env.example .env && nano .env  # add OPENROUTER_API_KEY

# Run (foreground test)
python main.py --panel --port 8000

# systemd service (production)
sudo tee /etc/systemd/system/governance.service <<EOF
[Unit]
Description=Governance Panel
After=network.target

[Service]
WorkingDirectory=/opt/governance
EnvironmentFile=/opt/governance/.env
ExecStart=/opt/governance/.venv/bin/python main.py --panel --port 8000
Restart=always
RestartSec=5
User=www-data

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now governance
sudo systemctl status governance
```

### nginx reverse proxy

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 86400;   # keep SSE connections alive
        proxy_buffering off;        # required for SSE
    }
}
```

For HTTPS: `sudo certbot --nginx -d your-domain.com`

### Docker Compose

```bash
cd paperclip/
docker-compose up -d
```

This starts:
- `paperclip:3000` — financial controls dashboard
- `governance:8000` — governance panel
- `specialists:8080` — OpenSwarm specialist layer

---

## Local Development

```bash
# Install in editable mode
pip install -e . -r requirements.txt

# Run tests
bash scripts/test_local.sh

# Panel on :8000
python main.py --panel

# Specialist layer on :8080 (optional, separate terminal)
python main.py --specialists

# Health check
bash scripts/healthcheck.sh
```

---

## Project Structure

```
governance/
├── main.py                        # Entry point — all CLI commands
├── panel.py                       # FastAPI panel server (web UI backend)
├── orchestrator.py                # CEO conversational orchestrator
├── business_registry.py           # Multi-business / multi-team registry
├── event_bus.py                   # In-process SSE event broadcast bus
│
├── core/
│   ├── budget_gate.py             # Contract 1: Paperclip budget pre-flight
│   ├── audit_stream.py            # Contract 2: audit event stream
│   └── state_manager.py          # SQLite: checkpoints, entity memory, logs
│
├── crews/
│   ├── base_crew.py               # GovernanceCrew wrapper (contracts 1-3)
│   ├── executive_crew.py          # CEO, CMO, CTO, CFO
│   ├── sales_crew.py              # SDR, AE, CSM
│   └── marketing_crew.py         # Content, SEO, Paid Ads
│
├── council/                       # 5-round Expert Council deliberation
│   ├── expert_council_flow.py
│   ├── agents/
│   │   ├── paperclip_expert.py
│   │   ├── crewai_expert.py
│   │   ├── openswarm_expert.py
│   │   └── council_moderator.py
│   └── tools/doc_scraper.py
│
├── specialists/                   # OpenSwarm + Composio specialist layer
│   ├── app.py                     # FastAPI on :8080 (contracts 4-5)
│   └── tools/composio_tools.py   # Rate-limited Composio tool factory
│
├── integrations/
│   ├── slack_bridge.py            # Slack Bolt webhook bridge
│   └── composio_setup.py         # Composio connection helpers
│
├── web/
│   └── index.html                 # Single-page governance panel UI
│
├── paperclip/
│   └── docker-compose.yml        # 3-service Docker stack
│
├── scripts/
│   ├── test_local.sh              # Import + smoke tests
│   ├── deploy.sh                  # SSH-based VPS deploy
│   └── healthcheck.sh             # Check all endpoints
│
├── data/                          # Auto-created; gitignored
│   ├── governance.db              # SQLite state (checkpoints, memory, logs)
│   └── audit.jsonl               # Fallback audit log
│
├── pyproject.toml                 # Editable package install
├── requirements.txt               # Python dependencies
└── .env.example                  # Environment variable template
```

---

## State & Memory

All state persists in `data/governance.db` (SQLite with WAL mode). Zero cold starts.

**Tables:**

| Table | Content |
|-------|---------|
| `checkpoints` | Last crew execution state per `(tenant_id, crew_id)` |
| `entity_memory` | Key-value store per agent entity, per tenant |
| `workflow_log` | Full event log per `(tenant_id, crew_id)` |

**Business registry** is stored in `entity_memory` under `tenant_id=system`. Adding a business creates a new entry; all its crews share the same `tenant_id` namespace.

**CEO conversation history** is stored in `checkpoints` as `ceo_conversation:{business_id}`. The last 60 turns persist across server restarts.

---

## Failure Modes & Guardrails

| Failure | Behavior |
|---------|----------|
| Paperclip unreachable | Circuit breaker opens after 5 failures; all actions allowed (fail-open) with 60 s cooldown |
| Budget exceeded | Crew paused via webhook; persisted to SQLite; resume via `/webhook/budget-resume` or Slack |
| Agent step fails | GovernanceCrew catches exception, saves failure checkpoint, publishes `team_error` event |
| SSE client disconnects | Subscription cleaned up immediately; no memory leak |
| CEO LLM error | Returns HTTP 500 with error detail; conversation state preserved |
| Composio rate limit | Per-tenant semaphore (default 10 concurrent); exponential backoff; circuit breaker |

---

## Security Notes

- The panel has no authentication by default. For production, put it behind nginx with HTTP Basic Auth or an SSO proxy.
- All CORS origins are allowed (`*`). Restrict to your domain in production via the `CORS_ORIGINS` env var (update `panel.py`).
- API keys are read from environment variables / `.env` — never commit `.env`.
- The `.gitignore` excludes `data/`, `.env`, and `__pycache__/`.

---

## License

MIT — see [LICENSE](LICENSE).
