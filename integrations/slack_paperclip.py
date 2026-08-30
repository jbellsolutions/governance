"""
Slack <-> Paperclip relay — talk to your CEO agent (and team) from Slack.

Two directions:
  • Inbound  : a Slack slash command  `/ceo <message>`  (and `/team <agent> <message>`) posts the
               owner's message as a comment on the CEO's "Owner channel" issue and @-mentions the
               CEO, which wakes it. The agent replies in the issue thread.
  • Outbound : a poller watches each company's Owner-channel issue for new agent comments and posts
               them to the owner's Slack channel, so the conversation shows up in Slack.

This needs a Paperclip board API key and Slack app credentials:
    PAPERCLIP_API_URL, PAPERCLIP_API_KEY     (board key, read+comment)
    SLACK_BOT_TOKEN                          (xoxb-…, chat:write + commands)
    SLACK_SIGNING_SECRET                     (verifies inbound requests actually came from Slack —
                                               required; the relay refuses to run without it)
    SLACK_OWNER_CHANNEL                       (default: #governance)
    SLACK_RELAY_PORT                          (default: 3001 — the slash-command receiver)

Run:  python main.py --slack-relay
Slack app setup: paste integrations/slack-manifest.yaml at api.slack.com/apps — see docs/SLACK.md.
"""
import os
import hmac
import hashlib
import json
import time
import threading
import http.server
import urllib.parse

from governance.integrations import slack_bridge as sb
from governance.core import state_manager

API_URL = os.environ.get("PAPERCLIP_API_URL", os.environ.get("PAPERCLIP_URL", "http://localhost:3000")).rstrip("/")
API_KEY = os.environ.get("PAPERCLIP_API_KEY", "")
OWNER_CHANNEL = os.environ.get("SLACK_OWNER_CHANNEL", "#governance")
RELAY_PORT = int(os.environ.get("SLACK_RELAY_PORT", "3001"))
POLL = int(os.environ.get("SLACK_RELAY_POLL_SECONDS", "20"))
SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET", "")
MAX_TIMESTAMP_SKEW = 60 * 5  # Slack's own recommendation: reject requests older than 5 minutes

_CURSOR_TENANT = "system"
_CURSOR_ENTITY = "slack_relay"


# ── Paperclip helpers (urllib, board key) ─────────────────────────────────────

def _pc(method: str, path: str, body: dict | None = None):
    import urllib.request
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{API_URL}{path}", data=data, method=method)
    req.add_header("Authorization", f"Bearer {API_KEY}")
    req.add_header("Content-Type", "application/json")
    try:
        import urllib.request as u
        with u.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except Exception as e:
        print(f"[slack-relay] {method} {path} failed: {e}")
        return None


def _companies() -> list:
    data = _pc("GET", "/api/companies")
    if isinstance(data, dict):
        return data.get("companies") or data.get("items") or []
    return data or []


def _ceo_agent(company_id: str) -> dict | None:
    agents = _pc("GET", f"/api/companies/{company_id}/agents") or []
    if isinstance(agents, dict):
        agents = agents.get("agents") or agents.get("items") or []
    for a in agents:
        title = (a.get("title") or a.get("role") or "").lower()
        if "ceo" in title or "chief executive" in title or a.get("reportsTo") in (None, "", "null"):
            return a
    return agents[0] if agents else None


def _owner_issue(company_id: str, ceo: dict) -> str | None:
    """Find or create the persistent Owner-channel issue assigned to the CEO."""
    key = f"owner_issue:{company_id}"
    existing = state_manager.get_entity_key(_CURSOR_TENANT, _CURSOR_ENTITY, key)
    if existing:
        return existing
    created = _pc("POST", f"/api/companies/{company_id}/issues", {
        "title": "Owner ↔ CEO (Slack channel)",
        "description": "Conversation thread between the human owner (via Slack) and the CEO.",
        "assigneeAgentId": ceo.get("id"),
        "status": "todo",
        "priority": "high",
    })
    iid = (created or {}).get("id") or (created or {}).get("issueId")
    if iid:
        state_manager.save_entity(_CURSOR_TENANT, _CURSOR_ENTITY, key, iid)
    return iid


def _agent_mention(agent: dict) -> str:
    name = agent.get("name") or agent.get("title") or "CEO"
    aid = agent.get("id", "")
    return f"[@{name}](agent://{aid})" if aid else f"@{name}"


def send_to_ceo(message: str, company_id: str | None = None) -> str:
    """Post the owner's message to the CEO's issue and wake the CEO. Returns a status string."""
    companies = _companies()
    if not companies:
        return "No companies found in Paperclip yet — create/import a business first."
    company = next((c for c in companies if c.get("id") == company_id), companies[0])
    cid = company.get("id")
    ceo = _ceo_agent(cid)
    if not ceo:
        return f"No CEO agent found in {company.get('name', cid)}."
    iid = _owner_issue(cid, ceo)
    if not iid:
        return "Couldn't open the owner channel issue."
    _pc("POST", f"/api/issues/{iid}/comments", {
        "body": f"**Owner (via Slack):** {message}\n\n{_agent_mention(ceo)} — please respond.",
    })
    return f"Sent to {ceo.get('name','CEO')} in {company.get('name', cid)}. Watch for the reply here."


# ── Outbound poller: CEO comments → Slack ─────────────────────────────────────

def _poll_loop():
    print(f"[slack-relay] outbound poller every {POLL}s")
    while True:
        try:
            for company in _companies():
                cid = company.get("id")
                ceo = _ceo_agent(cid)
                if not ceo:
                    continue
                iid = _owner_issue(cid, ceo)
                if not iid:
                    continue
                cur_key = f"cursor:{cid}"
                last = state_manager.get_entity_key(_CURSOR_TENANT, _CURSOR_ENTITY, cur_key) or 0
                comments = _pc("GET", f"/api/issues/{iid}/comments") or []
                if isinstance(comments, dict):
                    comments = comments.get("comments") or comments.get("items") or []
                newest = last
                for c in comments:
                    cts = c.get("createdAt") or c.get("created_at") or 0
                    cts = cts / 1000.0 if isinstance(cts, (int, float)) and cts > 1e12 else cts
                    try:
                        cts = float(cts)
                    except Exception:
                        cts = 0.0
                    if cts <= float(last):
                        continue
                    author = (c.get("authorName") or c.get("agentName") or "").lower()
                    body = c.get("body") or c.get("content") or ""
                    # Only relay agent messages (skip the owner's own relayed messages)
                    if "owner (via slack)" in body.lower():
                        newest = max(newest, cts)
                        continue
                    sb._slack_post("chat.postMessage", {
                        "channel": OWNER_CHANNEL,
                        "text": f":speech_balloon: *{company.get('name','CEO')} — {c.get('authorName','CEO')}*\n{body[:2500]}",
                        "unfurl_links": False,
                    })
                    newest = max(newest, cts)
                if newest > float(last):
                    state_manager.save_entity(_CURSOR_TENANT, _CURSOR_ENTITY, cur_key, newest)
        except Exception as e:
            print(f"[slack-relay] poll error: {e}")
        time.sleep(POLL)


# ── Inbound: slash-command receiver ───────────────────────────────────────────

HELP_TEXT = (
    "*Available commands*\n"
    "`/ceo <message>` — message the CEO agent of your default company; wakes it, reply lands here\n"
    "`/team <agent> <message>` — message a specific team agent (MVP: currently routes to the CEO)\n"
    "`/ceo help` or `/team help` — show this list\n"
)


def _verify_slack_signature(raw_body: bytes, timestamp: str, signature: str) -> bool:
    """HMAC verification per Slack's request-signing spec. Rejects if SLACK_SIGNING_SECRET is
    unset — refuse to run an unverified webhook rather than silently accept anything."""
    if not SIGNING_SECRET:
        return False
    if not timestamp or not signature:
        return False
    try:
        if abs(time.time() - float(timestamp)) > MAX_TIMESTAMP_SKEW:
            return False
    except ValueError:
        return False
    base = f"v0:{timestamp}:{raw_body.decode()}".encode()
    digest = hmac.new(SIGNING_SECRET.encode(), base, hashlib.sha256).hexdigest()
    expected = f"v0={digest}"
    return hmac.compare_digest(expected, signature)


class _Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)

        if not _verify_slack_signature(
            raw,
            self.headers.get("X-Slack-Request-Timestamp", ""),
            self.headers.get("X-Slack-Signature", ""),
        ):
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "invalid signature"}).encode())
            return

        params = dict(urllib.parse.parse_qsl(raw.decode()))
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

        command = params.get("command", "")
        text = params.get("text", "").strip()
        if command in ("/ceo", "/team") and text.lower() in ("help", "commands", "?"):
            resp = {"text": HELP_TEXT}
        elif command in ("/ceo", "/team") and text:
            # /team <agent> <message> could target a specific agent; MVP routes all to CEO.
            status = send_to_ceo(text)
            resp = {"response_type": "in_channel", "text": f":outbox_tray: {status}"}
        elif command in ("/ceo", "/team"):
            resp = {"text": HELP_TEXT}
        else:
            resp = {"text": f"Unknown command: {command}"}
        self.wfile.write(json.dumps(resp).encode())


def main() -> int:
    if not API_KEY:
        print("[slack-relay] PAPERCLIP_API_KEY required (board key). Exiting.")
        return 1
    if not sb.SLACK_BOT_TOKEN:
        print("[slack-relay] SLACK_BOT_TOKEN required. Exiting.")
        return 1
    if not SIGNING_SECRET:
        print("[slack-relay] SLACK_SIGNING_SECRET required — without it every inbound request is "
              "rejected (this endpoint can wake an agent and post as the owner, so it refuses to "
              "run unverified). Get it from the Slack app's Basic Information page. Exiting.")
        return 1
    threading.Thread(target=_poll_loop, daemon=True).start()
    server = http.server.HTTPServer(("0.0.0.0", RELAY_PORT), _Handler)
    print(f"[slack-relay] slash-command receiver on :{RELAY_PORT}  (point Slack /ceo here)")
    print(f"[slack-relay] owner channel: {OWNER_CHANNEL}")
    sb._slack_post("chat.postMessage", {
        "channel": OWNER_CHANNEL,
        "text": f":electric_plug: Governance relay connected.\n{HELP_TEXT}",
        "unfurl_links": False,
    })
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
