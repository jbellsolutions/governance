"""
Paperclip process-adapter worker (OpenRouter path).

This is an ALTERNATIVE to Paperclip's first-class `claude_local` adapter, for operators who want
every agent driven by a single OpenRouter key instead of local Claude Code / Codex.

Register an agent in Paperclip with the built-in `process` adapter:
    command: python
    args:    ["-m", "governance.paperclip_worker"]
    env:     { OPENROUTER_API_KEY: "...", AGENT_MODEL: "anthropic/claude-sonnet-4-6" }

Paperclip injects PAPERCLIP_* env vars and spawns this process for each heartbeat. The worker
follows the Paperclip heartbeat procedure: identify → pick work → checkout → read context →
act (via OpenRouter) → comment + update status → exit. All output goes to stdout for the run viewer.

This is intentionally a LIGHTWEIGHT runner: it reasons and reports, and can call the Integrations
sidecar over HTTP, but it does not have a local shell/filesystem agent loop the way claude_local
does. For richer autonomous execution, prefer the claude_local adapter (see the repo README).
"""
import os
import sys
import json
import urllib.request
import urllib.error

API_URL = os.environ.get("PAPERCLIP_API_URL", "").rstrip("/")
API_KEY = os.environ.get("PAPERCLIP_API_KEY", "")
AGENT_ID = os.environ.get("PAPERCLIP_AGENT_ID", "")
COMPANY_ID = os.environ.get("PAPERCLIP_COMPANY_ID", "")
RUN_ID = os.environ.get("PAPERCLIP_RUN_ID", "")
TASK_ID = os.environ.get("PAPERCLIP_TASK_ID", "")
WAKE_REASON = os.environ.get("PAPERCLIP_WAKE_REASON", "")

MODEL = os.environ.get("AGENT_MODEL", os.environ.get("EXEC_MODEL", "anthropic/claude-sonnet-4-6"))
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
OPENROUTER_BASE = os.environ.get("OPENAI_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")


def log(msg: str) -> None:
    print(msg, flush=True)


def api(method: str, path: str, body: dict | None = None) -> dict | None:
    """Call the Paperclip API. Returns parsed JSON or None on error."""
    url = f"{API_URL}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {API_KEY}")
    req.add_header("Content-Type", "application/json")
    if RUN_ID:
        req.add_header("X-Paperclip-Run-Id", RUN_ID)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        log(f"[api] {method} {path} -> HTTP {e.code}: {e.read().decode()[:300]}")
        return {"_status": e.code}
    except Exception as e:
        log(f"[api] {method} {path} -> error: {e}")
        return None


def llm(system: str, user: str) -> str:
    """Single OpenRouter completion. Returns the assistant text."""
    if not OPENROUTER_KEY:
        return "[worker] No OPENROUTER_API_KEY set — cannot reason. Marking blocked."
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    req = urllib.request.Request(
        f"{OPENROUTER_BASE}/chat/completions",
        data=json.dumps(payload).encode(),
        method="POST",
    )
    req.add_header("Authorization", f"Bearer {OPENROUTER_KEY}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode())
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[worker] LLM error: {e}"


def pick_issue() -> str | None:
    """Determine which issue to work this heartbeat."""
    if TASK_ID:
        return TASK_ID
    inbox = api("GET", "/api/agents/me/inbox-lite")
    if not inbox:
        return None
    items = inbox.get("issues") or inbox.get("items") or []
    # Priority: in_progress -> in_review -> todo
    for status in ("in_progress", "in_review", "todo"):
        for it in items:
            if it.get("status") == status:
                return it.get("id") or it.get("issueId")
    return None


def main() -> int:
    log(f"[worker] heartbeat start — agent={AGENT_ID} company={COMPANY_ID} "
        f"wake={WAKE_REASON or 'scheduled'} model={MODEL}")

    if not (API_URL and API_KEY):
        log("[worker] Missing PAPERCLIP_API_URL/PAPERCLIP_API_KEY — not running under Paperclip. Exiting 0.")
        return 0

    me = api("GET", "/api/agents/me") or {}
    role = me.get("title") or me.get("role") or "agent"
    instructions = me.get("instructions") or me.get("description") or ""

    issue_id = pick_issue()
    if not issue_id:
        log("[worker] No assigned work. Exiting heartbeat.")
        return 0

    # Checkout (must happen before work)
    checkout = api("POST", f"/api/issues/{issue_id}/checkout", {
        "agentId": AGENT_ID,
        "expectedStatuses": ["todo", "backlog", "blocked", "in_review", "in_progress"],
    })
    if checkout and checkout.get("_status") == 409:
        log(f"[worker] Issue {issue_id} owned by another agent (409). Exiting — never retry a 409.")
        return 0

    ctx = api("GET", f"/api/issues/{issue_id}/heartbeat-context") or {}
    issue = ctx.get("issue") or api("GET", f"/api/issues/{issue_id}") or {}
    title = issue.get("title", "(untitled)")
    description = issue.get("description", "")
    goal = (ctx.get("goal") or {}).get("description", "") or (issue.get("goal") or {}).get("description", "")

    log(f"[worker] Working issue {issue_id}: {title}")

    system = (
        f"You are {role}. {instructions}\n\n"
        "You are running one Paperclip heartbeat. Do the most useful concrete work you can in this "
        "single step, then report it. Be specific and actionable. If you genuinely cannot proceed, "
        "say exactly what blocks you and who must act."
    )
    user = (
        f"Company goal: {goal}\n\n"
        f"Task: {title}\n{description}\n\n"
        "Produce your work product now as a concise markdown report of what you did and what remains. "
        "End with one line: STATUS: done | in_progress | blocked"
    )

    output = llm(system, user)
    log("\n--- agent output ---\n" + output + "\n--------------------")

    # Parse the declared status
    status = "in_progress"
    for line in output.splitlines():
        s = line.strip().lower()
        if s.startswith("status:"):
            val = s.split(":", 1)[1].strip()
            if val in ("done", "in_progress", "blocked"):
                status = val
            break

    # Report back: comment + status
    api("PATCH", f"/api/issues/{issue_id}", {"status": status, "comment": output[:6000]})
    log(f"[worker] Updated issue {issue_id} -> {status}. Heartbeat complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
