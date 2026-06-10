#!/usr/bin/env bash
#
# Stand up "Governance HQ" + the Architect agent on a Paperclip board, entirely over the API.
# The Architect is your permanent point of contact: chat with it on the Architecture Board issue to
# spin up businesses and departments. See docs/ARCHITECT.md.
#
#   PAPERCLIP_API_URL    base URL of the board            (required, e.g. https://board.example.com)
#   PAPERCLIP_API_KEY    board key (company-management)    (required)
#   OPENROUTER_API_KEY   model access for the Architect    (required)
#   REPO_URL             public repo holding the package   (default below)
#   MODEL                opencode model id                 (default openrouter/anthropic/claude-sonnet-4.5)
#
# Notes:
# - GitHub package import resolves a SUBDIRECTORY when the url points at the tree path
#   (…/tree/<branch>/<path>), not via a separate "path" field.
# - Safe imports (board key) reject the "process" adapter; we force opencode_local via adapterOverrides,
#   which requires adapterConfig.model in provider/model format.

set -euo pipefail

B="${PAPERCLIP_API_URL:?set PAPERCLIP_API_URL}"
T="${PAPERCLIP_API_KEY:?set PAPERCLIP_API_KEY}"
OR="${OPENROUTER_API_KEY:?set OPENROUTER_API_KEY}"
REPO_URL="${REPO_URL:-https://github.com/jbellsolutions/governance}"
MODEL="${MODEL:-openrouter/anthropic/claude-sonnet-4.5}"
BRANCH="${BRANCH:-main}"
PKG="paperclip/companies/governance-hq"
TREE_URL="${REPO_URL}/tree/${BRANCH}/${PKG}"

auth=(-H "Authorization: Bearer $T" -H "Content-Type: application/json")

# Need any existing company id to scope the import call (the import still creates a NEW company).
CID="$(curl -sS "$B/api/companies" "${auth[@]}" | python3 -c 'import sys,json;xs=json.load(sys.stdin);print(xs[0]["id"] if isinstance(xs,list) and xs else "")')"
[ -z "$CID" ] && { echo "No existing company to scope the import; create one in the board first." >&2; exit 1; }

echo "Importing Governance HQ from $TREE_URL …"
RESP="$(curl -sS -X POST "$B/api/companies/$CID/imports/apply" "${auth[@]}" -d @- <<JSON
{
  "source": { "type": "github", "url": "$TREE_URL" },
  "include": { "company": true, "agents": true, "projects": true, "issues": true, "skills": true },
  "target": { "mode": "new_company", "newCompanyName": "Governance HQ" },
  "collisionStrategy": "rename",
  "adapterOverrides": {
    "architect": {
      "adapterType": "opencode_local",
      "adapterConfig": {
        "cwd": "/home/paperclip",
        "model": "$MODEL",
        "env": { "OPENROUTER_API_KEY": "$OR", "PAPERCLIP_API_KEY": "$T", "PAPERCLIP_API_URL": "$B" }
      }
    }
  }
}
JSON
)"
echo "$RESP" | python3 -m json.tool 2>/dev/null || echo "$RESP"

HQ="$(echo "$RESP" | python3 -c 'import sys,json;print((json.load(sys.stdin).get("company") or {}).get("id",""))' 2>/dev/null || true)"
[ -z "$HQ" ] && { echo "Import did not return a company id; check the response above." >&2; exit 1; }

# The standing "Architecture Board" issue imports in 'backlog'; flip it to 'todo' so the Architect
# picks it up on its next heartbeat.
ARCH="$(curl -sS "$B/api/companies/$HQ/agents" "${auth[@]}" | python3 -c 'import sys,json;xs=json.load(sys.stdin);print(next((a["id"] for a in xs if a.get("name")=="Architect"), ""))')"
IID="$(curl -sS "$B/api/companies/$HQ/issues" "${auth[@]}" | python3 -c 'import sys,json;d=json.load(sys.stdin);xs=d if isinstance(d,list) else d.get("issues",[]);print(xs[0]["id"] if xs else "")')"
if [ -n "$IID" ]; then
  curl -sS -X PATCH "$B/api/issues/$IID" "${auth[@]}" -d "{\"status\":\"todo\",\"assigneeAgentId\":\"$ARCH\"}" >/dev/null
  echo "Architecture Board issue set to todo (assignee: Architect $ARCH)."
fi

echo
echo "Done. Governance HQ: $HQ — Architect: $ARCH"
echo "Open the board → Governance HQ → 'Architecture Board' and tell the Architect what to build."
