"""
Archivist — mirrors every agent action and thought to two durable backups:

  1. Obsidian  — local markdown vault (OBSIDIAN_VAULT_PATH), one file per event,
                 organized by business / date. Instantly browsable, git-friendly.
  2. Notion    — a Notion database/page via Composio (the Integrations sidecar's
                 `notion` specialist) or the Notion API directly (NOTION_API_KEY).

Both sinks are optional and fail-safe: if neither is configured, record() is a no-op
(it always also appends to the local SQLite workflow_log via state_manager, so nothing
is ever lost). Never raises — archiving must not break agent execution.

Env:
  OBSIDIAN_VAULT_PATH   absolute path to an Obsidian vault folder (e.g. /opt/governance/vault)
  NOTION_API_KEY        Notion integration token (direct API path), optional
  NOTION_PARENT_PAGE_ID parent page id under which to create the backup database, optional
  INTEGRATIONS_URL      sidecar URL for the Composio Notion path (fallback if no NOTION_API_KEY)
"""
import os
import re
import json
import time
import threading
import urllib.request
import urllib.error

VAULT = os.environ.get("OBSIDIAN_VAULT_PATH", "")
NOTION_API_KEY = os.environ.get("NOTION_API_KEY", "")
NOTION_PARENT = os.environ.get("NOTION_PARENT_PAGE_ID", "")
INTEGRATIONS_URL = os.environ.get("INTEGRATIONS_URL", "http://localhost:8080").rstrip("/")

_lock = threading.Lock()


def configured() -> dict:
    return {
        "obsidian": bool(VAULT),
        "notion_api": bool(NOTION_API_KEY),
        "notion_via_sidecar": bool(not NOTION_API_KEY and INTEGRATIONS_URL),
    }


def _slug(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9 _-]", "", str(s)).strip().replace(" ", "-").lower()
    return (s or "untitled")[:60]


def _stamp(ts: float) -> tuple[str, str]:
    """Return (YYYY-MM-DD, HHMMSS) for the given epoch seconds, UTC."""
    lt = time.gmtime(ts)
    return time.strftime("%Y-%m-%d", lt), time.strftime("%H%M%S", lt)


# ── Obsidian sink ─────────────────────────────────────────────────────────────

def _write_obsidian(event: dict) -> None:
    if not VAULT:
        return
    try:
        day, hms = _stamp(event["ts"])
        biz = _slug(event.get("business") or "default")
        folder = os.path.join(VAULT, biz, day)
        os.makedirs(folder, exist_ok=True)
        agent = _slug(event.get("agent") or "agent")
        kind = _slug(event.get("kind") or "event")
        fname = f"{hms}-{agent}-{kind}.md"
        path = os.path.join(folder, fname)

        fm = {
            "business": event.get("business", ""),
            "agent": event.get("agent", ""),
            "kind": event.get("kind", ""),
            "issue": event.get("issue", ""),
            "ts": event["ts"],
            "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(event["ts"])),
        }
        meta = event.get("meta") or {}
        for k, v in meta.items():
            if isinstance(v, (str, int, float, bool)):
                fm[k] = v
        lines = ["---"]
        for k, v in fm.items():
            lines.append(f"{k}: {json.dumps(v) if isinstance(v, str) else v}")
        # tags for Obsidian graph
        lines.append(f"tags: [governance, {_slug(event.get('business') or 'default')}, "
                     f"{_slug(event.get('kind') or 'event')}]")
        lines.append("---")
        lines.append(f"# {event.get('title', event.get('kind','event'))}")
        lines.append("")
        lines.append(event.get("body", ""))
        with open(path, "w") as f:
            f.write("\n".join(lines))
    except Exception as e:
        print(f"[archivist] obsidian write failed: {e}")


# ── Notion sink ───────────────────────────────────────────────────────────────

def _write_notion(event: dict) -> None:
    # Direct Notion API path (preferred if token present)
    if NOTION_API_KEY and NOTION_PARENT:
        try:
            title = f"[{event.get('business','')}] {event.get('agent','')} — {event.get('title', event.get('kind',''))}"
            body = (event.get("body", "") or "")[:1900]
            payload = {
                "parent": {"page_id": NOTION_PARENT},
                "properties": {
                    "title": {"title": [{"text": {"content": title[:200]}}]},
                },
                "children": [{
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"type": "text", "text": {"content": body}}]},
                }],
            }
            req = urllib.request.Request(
                "https://api.notion.com/v1/pages",
                data=json.dumps(payload).encode(),
                method="POST",
            )
            req.add_header("Authorization", f"Bearer {NOTION_API_KEY}")
            req.add_header("Notion-Version", "2022-06-28")
            req.add_header("Content-Type", "application/json")
            urllib.request.urlopen(req, timeout=10)
            return
        except Exception as e:
            print(f"[archivist] notion api write failed: {e}")
            return

    # Fallback: route through the Integrations sidecar's `notion` specialist (Composio)
    if INTEGRATIONS_URL:
        try:
            spec = {
                "specialist_type": "notion",
                "task_spec": (
                    f"Create a Notion page titled "
                    f"'[{event.get('business','')}] {event.get('agent','')} — "
                    f"{event.get('title', event.get('kind',''))}' with this content:\n\n"
                    f"{(event.get('body','') or '')[:1500]}"
                ),
                "tenant_id": _slug(event.get("business") or "default"),
                "entity_id": "archivist",
            }
            req = urllib.request.Request(
                f"{INTEGRATIONS_URL}/delegate",
                data=json.dumps(spec).encode(),
                method="POST",
            )
            req.add_header("Content-Type", "application/json")
            urllib.request.urlopen(req, timeout=15)
        except Exception:
            pass  # sidecar may be down / notion not connected — Obsidian + SQLite still hold it


# ── Public API ────────────────────────────────────────────────────────────────

def record(
    kind: str,
    business: str,
    agent: str = "",
    title: str = "",
    body: str = "",
    issue: str = "",
    meta: dict | None = None,
    ts: float | None = None,
    block: bool = False,
) -> None:
    """
    Archive one event to all configured sinks + the local SQLite workflow_log.
    Non-blocking by default (dispatches sinks to a daemon thread). Never raises.
    """
    event = {
        "kind": kind, "business": business, "agent": agent,
        "title": title or kind, "body": body, "issue": issue,
        "meta": meta or {}, "ts": ts if ts is not None else time.time(),
    }

    # Local SQLite log — always, synchronously (this is the source-of-truth backstop)
    try:
        from governance.core import state_manager
        state_manager.log_event(
            tenant_id=_slug(business or "default"),
            crew_id=agent or "agent",
            event_type=kind,
            payload={"title": event["title"], "body": body[:2000], "issue": issue, "meta": meta or {}},
        )
    except Exception:
        pass

    def _sinks():
        with _lock:
            _write_obsidian(event)
            _write_notion(event)

    if block:
        _sinks()
    else:
        threading.Thread(target=_sinks, daemon=True).start()


def record_thought(business: str, agent: str, thought: str, issue: str = "", meta: dict | None = None) -> None:
    record("thought", business, agent, title="Reasoning", body=thought, issue=issue, meta=meta)


def record_action(business: str, agent: str, action: str, result: str = "", issue: str = "", meta: dict | None = None) -> None:
    body = action if not result else f"{action}\n\n**Result:**\n{result}"
    record("action", business, agent, title="Action", body=body, issue=issue, meta=meta)
