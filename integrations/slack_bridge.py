"""
Slack Web API helpers — outbound posting only.

Low-level module used by integrations/slack_paperclip.py (the one inbound/outbound Slack relay —
see that file and docs/SLACK.md). This module has no server of its own; it just posts to the Slack
Web API and builds interactive-button payloads for outbound notifications.

Requires:
  SLACK_BOT_TOKEN   = xoxb-...
"""
import os
import json
import urllib.request
from typing import Optional


SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_API = "https://slack.com/api"


# ── Outbound: Send messages to Slack ────────────────────────────────────────

def _slack_post(method: str, payload: dict) -> dict:
    """POST to Slack Web API."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{SLACK_API}/{method}",
        data=data,
        headers={
            "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"ok": False, "error": str(e)}


def ensure_channel(channel_name: str) -> str:
    """Create channel if it doesn't exist, return channel ID."""
    # Try to find existing channel
    resp = _slack_post("conversations.list", {"limit": 200})
    if resp.get("ok"):
        for ch in resp.get("channels", []):
            if ch["name"] == channel_name.lstrip("#"):
                return ch["id"]

    # Create new channel
    resp = _slack_post("conversations.create", {
        "name": channel_name.lstrip("#"),
        "is_private": False,
    })
    if resp.get("ok"):
        return resp["channel"]["id"]
    return channel_name  # fallback: use name directly


def notify_agent_activity(
    company: str,
    agent_name: str,
    activity: str,
    level: str = "info",
) -> bool:
    """Post agent activity to #company-{name} channel."""
    channel = ensure_channel(f"company-{company.lower().replace(' ', '-')}")
    emoji = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "🚨"}.get(level, "ℹ️")
    resp = _slack_post("chat.postMessage", {
        "channel": channel,
        "text": f"{emoji} *{agent_name}*: {activity}",
        "unfurl_links": False,
    })
    return resp.get("ok", False)


def notify_budget_alert(
    company: str,
    agent_name: str,
    pct_used: float,
    budget_usd: float,
) -> bool:
    """Post budget alert to #agent-alerts channel."""
    channel = ensure_channel("agent-alerts")
    if pct_used >= 100:
        emoji, status = "🛑", "PAUSED — budget exhausted"
    else:
        emoji, status = "⚠️", f"{pct_used:.0f}% consumed"

    resp = _slack_post("chat.postMessage", {
        "channel": channel,
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"{emoji} *Budget Alert* — {company} / {agent_name}\n"
                        f"Status: *{status}*\n"
                        f"Budget: ${budget_usd:.2f}/month\n"
                        f"Utilization: {pct_used:.0f}%"
                    ),
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Resume Agent"},
                        "action_id": "resume_agent",
                        "value": json.dumps({"company": company, "agent": agent_name}),
                        "style": "primary",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Increase Budget"},
                        "action_id": "increase_budget",
                        "value": json.dumps({"company": company, "agent": agent_name}),
                    },
                ],
            },
        ],
    })
    return resp.get("ok", False)


def post_council_round(round_num: int, title: str, summaries: dict) -> bool:
    """Post council deliberation round summary to #agent-council channel."""
    channel = ensure_channel("agent-council")
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"Council Round {round_num}: {title}",
            },
        }
    ]
    for agent_name, summary in summaries.items():
        # Truncate to 2000 chars for Slack block limit
        truncated = summary[:1800] + "..." if len(summary) > 1800 else summary
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{agent_name}*\n{truncated}",
            },
        })

    resp = _slack_post("chat.postMessage", {
        "channel": channel,
        "blocks": blocks,
        "text": f"Council Round {round_num}: {title}",
    })
    return resp.get("ok", False)


def post_approval_request(
    company: str,
    agent_name: str,
    action: str,
    context: str,
    request_id: str,
) -> bool:
    """Post a human approval request with interactive buttons."""
    channel = ensure_channel(f"company-{company.lower().replace(' ', '-')}")
    resp = _slack_post("chat.postMessage", {
        "channel": channel,
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"🤔 *Approval Required* — {agent_name}\n"
                        f"*Action:* {action}\n"
                        f"*Context:* {context}"
                    ),
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Approve"},
                        "action_id": "approve_action",
                        "value": json.dumps({"request_id": request_id, "decision": "approved"}),
                        "style": "primary",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Override / Reject"},
                        "action_id": "reject_action",
                        "value": json.dumps({"request_id": request_id, "decision": "rejected"}),
                        "style": "danger",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Request Clarification"},
                        "action_id": "clarify_action",
                        "value": json.dumps({"request_id": request_id, "decision": "clarify"}),
                    },
                ],
            },
        ],
        "text": f"Approval needed: {action}",
    })
    return resp.get("ok", False)


# ── CLI test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not SLACK_BOT_TOKEN:
        print("Set SLACK_BOT_TOKEN to test Slack integration")
    else:
        ok = notify_agent_activity("TestCo", "CEO", "Daily strategy review completed", "success")
        print(f"Slack notify: {'OK' if ok else 'FAILED'}")
