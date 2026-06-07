"""
Paperclip → Obsidian/Notion sync.

Polls the Paperclip API for every company's issues and comments and mirrors them through the
archivist, so the ENTIRE board (every agent, every action, regardless of adapter) is backed up to
Obsidian + Notion — not just the OpenRouter worker. Run as a long-lived service:

    python main.py --archivist

or directly:  python -m governance.backup.paperclip_sync

State (last-seen cursor per company) is kept in the local SQLite store so restarts don't
re-archive everything. Needs a board API key with read access:

    PAPERCLIP_API_URL   e.g. http://localhost:3000
    PAPERCLIP_API_KEY   a board/agent API key (read scope)
    ARCHIVE_POLL_SECONDS  poll interval (default 60)
"""
import os
import time
import json
import urllib.request
import urllib.error

from governance.backup import archivist
from governance.core import state_manager

API_URL = os.environ.get("PAPERCLIP_API_URL", os.environ.get("PAPERCLIP_URL", "http://localhost:3000")).rstrip("/")
API_KEY = os.environ.get("PAPERCLIP_API_KEY", "")
POLL = int(os.environ.get("ARCHIVE_POLL_SECONDS", "60"))

_CURSOR_TENANT = "system"
_CURSOR_ENTITY = "archive_cursor"


def _api(path: str) -> dict | list | None:
    req = urllib.request.Request(f"{API_URL}{path}", method="GET")
    req.add_header("Authorization", f"Bearer {API_KEY}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else None
    except Exception as e:
        print(f"[archive-sync] GET {path} failed: {e}")
        return None


def _seen(company_id: str, key: str) -> float:
    val = state_manager.get_entity_key(_CURSOR_TENANT, _CURSOR_ENTITY, f"{company_id}:{key}")
    return float(val) if val else 0.0


def _mark(company_id: str, key: str, ts: float) -> None:
    state_manager.save_entity(_CURSOR_TENANT, _CURSOR_ENTITY, f"{company_id}:{key}", ts)


def _companies() -> list:
    data = _api("/api/companies")
    if isinstance(data, dict):
        return data.get("companies") or data.get("items") or []
    return data or []


def _sync_company(company: dict) -> int:
    cid = company.get("id") or company.get("companyId")
    name = company.get("name", cid)
    if not cid:
        return 0
    issues = _api(f"/api/companies/{cid}/issues?status=todo,in_progress,in_review,blocked,done") or []
    if isinstance(issues, dict):
        issues = issues.get("issues") or issues.get("items") or []

    last = _seen(cid, "comment_ts")
    newest = last
    count = 0
    for issue in issues:
        iid = issue.get("id") or issue.get("issueId")
        if not iid:
            continue
        comments = _api(f"/api/issues/{iid}/comments") or []
        if isinstance(comments, dict):
            comments = comments.get("comments") or comments.get("items") or []
        for c in comments:
            cts = c.get("createdAt") or c.get("created_at") or 0
            # createdAt may be ISO or epoch; normalize to epoch seconds
            cts = _to_epoch(cts)
            if cts <= last:
                continue
            archivist.record(
                kind="comment",
                business=name,
                agent=c.get("authorName") or c.get("agentName") or c.get("author") or "agent",
                title=f"{issue.get('title','(issue)')}",
                body=c.get("body") or c.get("content") or "",
                issue=issue.get("identifier") or iid,
                meta={"issue_status": issue.get("status", ""), "company_id": cid},
                ts=cts or time.time(),
            )
            count += 1
            newest = max(newest, cts)
    if newest > last:
        _mark(cid, "comment_ts", newest)
    return count


def _to_epoch(v) -> float:
    if isinstance(v, (int, float)):
        # milliseconds vs seconds heuristic
        return float(v) / 1000.0 if v > 1e12 else float(v)
    if isinstance(v, str) and v:
        try:
            import datetime
            return datetime.datetime.fromisoformat(v.replace("Z", "+00:00")).timestamp()
        except Exception:
            return 0.0
    return 0.0


def run_once() -> int:
    total = 0
    for company in _companies():
        total += _sync_company(company)
    return total


def main() -> int:
    cfg = archivist.configured()
    print(f"[archive-sync] starting. sinks: {cfg}. poll={POLL}s api={API_URL}")
    if not API_KEY:
        print("[archive-sync] No PAPERCLIP_API_KEY — set a board read key. Exiting.")
        return 1
    if not any(cfg.values()):
        print("[archive-sync] WARNING: no Obsidian/Notion sink configured — only SQLite log will hold data.")
    while True:
        try:
            n = run_once()
            if n:
                print(f"[archive-sync] archived {n} new event(s)")
        except Exception as e:
            print(f"[archive-sync] cycle error: {e}")
        time.sleep(POLL)


if __name__ == "__main__":
    raise SystemExit(main())
