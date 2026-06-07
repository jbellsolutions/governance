#!/bin/bash
# Deploy governance stack to a fresh Hetzner/DigitalOcean VPS
# Usage: ./scripts/deploy.sh <VPS_IP> [--key ~/.ssh/id_rsa]
set -euo pipefail

VPS_IP="${1:?Usage: $0 <VPS_IP> [--key <keyfile>]}"
SSH_KEY="${3:-$HOME/.ssh/id_rsa}"
REMOTE_DIR="/opt/governance"

echo "=== Deploying Governance System to $VPS_IP ==="

# Ensure .env exists locally
if [ ! -f ".env" ]; then
    echo "ERROR: .env not found. Copy .env.example and fill in your keys."
    exit 1
fi

# Pack project (exclude non-essentials)
echo "→ Packing project..."
tar --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.venv' \
    --exclude='venv' \
    --exclude='council/output' \
    -czf /tmp/governance.tar.gz .

# Upload
echo "→ Uploading to $VPS_IP..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "root@$VPS_IP" "mkdir -p $REMOTE_DIR"
scp -i "$SSH_KEY" /tmp/governance.tar.gz ".env" "root@$VPS_IP:$REMOTE_DIR/"

# Remote setup
echo "→ Running remote setup..."
ssh -i "$SSH_KEY" "root@$VPS_IP" << 'REMOTE'
set -euo pipefail
cd /opt/governance

# Install Docker if not present
if ! command -v docker &>/dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
fi

if ! command -v docker-compose &>/dev/null; then
    apt-get install -y docker-compose-plugin 2>/dev/null || \
    pip3 install docker-compose 2>/dev/null || \
    curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
        -o /usr/local/bin/docker-compose && chmod +x /usr/local/bin/docker-compose
fi

# Unpack
tar -xzf governance.tar.gz

# Build and start
cd paperclip
docker compose pull 2>/dev/null || true
docker compose build --no-cache
docker compose up -d

echo "=== Deployment complete ==="
docker compose ps
REMOTE

echo ""
echo "=== Done ==="
echo "Paperclip dashboard:        http://$VPS_IP:3000"
echo "Governance control plane:   http://$VPS_IP:8000/docs"
echo "OpenSwarm specialists:      http://$VPS_IP:8080/docs"
echo "Slack bridge:               http://$VPS_IP:3001"
