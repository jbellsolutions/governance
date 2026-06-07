#!/bin/bash
# Check health of all governance system components
# Usage: ./scripts/healthcheck.sh [VPS_IP]
set -euo pipefail

BASE="${1:-localhost}"
PASS=0
FAIL=0

check() {
    local name="$1"
    local url="$2"
    if curl -sf --max-time 5 "$url" > /dev/null 2>&1; then
        echo "  ✓ $name ($url)"
        PASS=$((PASS + 1))
    else
        echo "  ✗ $name ($url) — NOT REACHABLE"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== Governance System Health Check ==="
echo "Target: $BASE"
echo ""

echo "Layer 1 — Paperclip Dashboard:"
check "Paperclip" "http://$BASE:3000/health"

echo ""
echo "Layer 2 — Governance Control Plane:"
check "Control Plane /health"  "http://$BASE:8000/health"
check "Control Plane /status"  "http://$BASE:8000/status"

echo ""
echo "Layer 3 — OpenSwarm Specialists:"
check "Specialist Layer"  "http://$BASE:8080/health"

echo ""
echo "Integrations:"
check "Slack Bridge"  "http://$BASE:3001"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] && echo "All systems operational." || echo "Some services are down — check logs."
