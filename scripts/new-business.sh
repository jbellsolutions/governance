#!/usr/bin/env bash
#
# Spin up a NEW, isolated business in Paperclip from the lead-gen-agency template.
#
#   scripts/new-business.sh "Acme Outbound"
#
# Imports the company package as a new Paperclip company (complete data isolation from your other
# businesses). Needs a board API key.
#
#   PAPERCLIP_API_URL   e.g. http://localhost:3000   (default)
#   PAPERCLIP_API_KEY   board key with import permission   (required)
#   REPO_URL            this repo's GitHub URL            (default below)
#   PACKAGE_PATH        path to the company package in the repo (default below)

set -euo pipefail

NAME="${1:-}"
if [ -z "$NAME" ]; then
  echo "usage: scripts/new-business.sh \"Business Name\""
  exit 1
fi

API_URL="${PAPERCLIP_API_URL:-http://localhost:3000}"
API_KEY="${PAPERCLIP_API_KEY:-}"
REPO_URL="${REPO_URL:-https://github.com/jbellsolutions/governance}"
PACKAGE_PATH="${PACKAGE_PATH:-paperclip/companies/lead-gen-agency}"

if [ -z "$API_KEY" ]; then
  echo "Set PAPERCLIP_API_KEY (a board key)." >&2
  exit 1
fi

# Find any existing company id to scope the safe-import route (new_company mode still creates a
# brand-new isolated company; the :companyId in the path is just the caller's scope).
CID="$(curl -sS "$API_URL/api/companies" -H "Authorization: Bearer $API_KEY" \
  | python3 -c 'import sys,json; d=json.load(sys.stdin); xs=d.get("companies") or d.get("items") or d if isinstance(d,list) else []; print((xs[0].get("id") if xs else ""))' 2>/dev/null || true)"

echo "Importing '$NAME' from $REPO_URL ($PACKAGE_PATH) …"
curl -sS -X POST "$API_URL/api/companies/${CID:-bootstrap}/imports/apply" \
  -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" \
  -d "{
    \"source\": { \"type\": \"github\", \"url\": \"$REPO_URL\", \"path\": \"$PACKAGE_PATH\" },
    \"include\": { \"company\": true, \"agents\": true, \"projects\": true, \"issues\": true },
    \"target\": { \"mode\": \"new_company\", \"newCompanyName\": \"$NAME\" },
    \"collisionStrategy\": \"rename\"
  }" | python3 -m json.tool || true

echo
echo "Done. Open the board — '$NAME' is a new, isolated company."
echo "Its Onboarding Concierge will walk you through setup on its first heartbeat."
