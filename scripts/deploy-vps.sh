#!/usr/bin/env bash
#
# Deploy the Paperclip-native governance stack to a fresh Ubuntu 22.04+ VPS.
#
#   Paperclip board (the panel)  → :3000  (put behind nginx + TLS)
#   Integrations sidecar         → :8080  (loopback only; agents call it locally)
#
# Run this ON the VPS as a sudo-capable user:
#   curl -fsSL https://raw.githubusercontent.com/<you>/governance/main/scripts/deploy-vps.sh | bash
# or copy it over and `bash deploy-vps.sh`.
#
# Idempotent-ish: safe to re-run. Edit the CONFIG block first.

set -euo pipefail

# ── CONFIG ────────────────────────────────────────────────────────────────────
DOMAIN="${DOMAIN:-}"                       # e.g. board.youragency.com (for nginx+TLS). Empty = skip nginx.
REPO_URL="${REPO_URL:-https://github.com/jbellsolutions/governance.git}"
APP_DIR="${APP_DIR:-/opt/governance}"
PAPERCLIP_BIND="${PAPERCLIP_BIND:-lan}"    # lan = 0.0.0.0 (behind nginx). loopback for reverse-proxy only.
# Secrets — export these before running, or edit here:
OPENROUTER_API_KEY="${OPENROUTER_API_KEY:-}"
COMPOSIO_API_KEY="${COMPOSIO_API_KEY:-}"
# ──────────────────────────────────────────────────────────────────────────────

log() { printf '\033[1;36m[deploy]\033[0m %s\n' "$*"; }

log "Installing system dependencies (Node 20, Python 3, nginx, git)…"
sudo apt-get update -y
sudo apt-get install -y curl git python3 python3-venv python3-pip build-essential
if ! command -v node >/dev/null 2>&1 || [ "$(node -v | cut -dv -f2 | cut -d. -f1)" -lt 20 ]; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi
[ -n "$DOMAIN" ] && sudo apt-get install -y nginx certbot python3-certbot-nginx || true

log "Cloning / updating the governance repo at $APP_DIR…"
if [ -d "$APP_DIR/.git" ]; then
  sudo git -C "$APP_DIR" pull --ff-only
else
  sudo git clone "$REPO_URL" "$APP_DIR"
fi
sudo chown -R "$USER" "$APP_DIR"

log "Setting up the Integrations sidecar (Python venv)…"
cd "$APP_DIR"
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip >/dev/null
pip install -e . -r requirements.txt >/dev/null
deactivate

log "Writing environment file ($APP_DIR/.env)…"
cat > "$APP_DIR/.env" <<EOF
OPENROUTER_API_KEY=$OPENROUTER_API_KEY
OPENAI_API_KEY=$OPENROUTER_API_KEY
OPENAI_BASE_URL=https://openrouter.ai/api/v1
COMPOSIO_API_KEY=$COMPOSIO_API_KEY
COMPOSIO_MAX_CONCURRENT=10
SPECIALIST_MODEL=deepseek/deepseek-chat-v4
STATE_DB_PATH=$APP_DIR/data/governance.db
EOF

log "Creating systemd service: integrations sidecar (loopback :8080)…"
sudo tee /etc/systemd/system/governance-integrations.service >/dev/null <<EOF
[Unit]
Description=Governance Integrations Sidecar (Composio specialists)
After=network.target

[Service]
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/.venv/bin/python main.py --specialists --port 8080
Restart=always
RestartSec=5
User=$USER

[Install]
WantedBy=multi-user.target
EOF

log "Creating systemd service: Paperclip board (:3000)…"
sudo tee /etc/systemd/system/paperclip.service >/dev/null <<EOF
[Unit]
Description=Paperclip Board (governance panel)
After=network.target

[Service]
WorkingDirectory=$APP_DIR
ExecStart=$(command -v npx) -y paperclipai@latest run --bind $PAPERCLIP_BIND
Restart=always
RestartSec=5
User=$USER
Environment=HOME=$HOME

[Install]
WantedBy=multi-user.target
EOF

log "Starting services…"
sudo systemctl daemon-reload
sudo systemctl enable --now governance-integrations.service
# First Paperclip start needs interactive onboarding; do it once, then enable the service:
if [ ! -d "$HOME/.paperclip" ]; then
  log "First run: completing Paperclip onboarding (non-interactive)…"
  (cd "$APP_DIR" && npx -y paperclipai@latest onboard --yes --bind "$PAPERCLIP_BIND") || true
fi
sudo systemctl enable --now paperclip.service

if [ -n "$DOMAIN" ]; then
  log "Configuring nginx reverse proxy for $DOMAIN (SSE-aware)…"
  sudo tee /etc/nginx/sites-available/paperclip >/dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN;
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_read_timeout 86400;
        proxy_buffering off;
    }
}
EOF
  sudo ln -sf /etc/nginx/sites-available/paperclip /etc/nginx/sites-enabled/paperclip
  sudo nginx -t && sudo systemctl reload nginx
  log "Requesting TLS cert via certbot…"
  sudo certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "admin@$DOMAIN" || \
    log "certbot failed — run it manually later: sudo certbot --nginx -d $DOMAIN"
fi

log "Done."
echo
echo "  Paperclip board : http://${DOMAIN:-<server-ip>}:3000  (or https://$DOMAIN behind nginx)"
echo "  Integrations    : http://127.0.0.1:8080/health"
echo
echo "Next steps:"
echo "  1. Open the board, claim the instance (first admin):  npx paperclipai auth bootstrap-ceo"
echo "  2. Import a business: in the board, import a company package from this repo:"
echo "       source = github  url = $REPO_URL"
echo "       path   = paperclip/companies/lead-gen-agency"
echo "     (or POST /api/companies/:companyId/imports/apply — see README)"
echo "  3. Set company secrets in the board: OPENROUTER_API_KEY, COMPOSIO_API_KEY,"
echo "       INTEGRATIONS_URL=http://127.0.0.1:8080"
echo "  4. Talk to your CEO agent in the board. The teams run on their daily routines."
