"""
Budget Pre-flight Gate — Contract 1 of 5.
Checks Paperclip before any costly tool execution.
Circuit breaker degrades gracefully if Paperclip is unreachable.
"""
import os
import json
import time
import threading
import urllib.request
import urllib.error
from typing import Literal

PAPERCLIP_URL = os.environ.get("PAPERCLIP_URL", "http://localhost:3000")
PREFLIGHT_TIMEOUT = 5

# Circuit breaker: trip after 5 consecutive failures, reset after 60s
_cb = {"failures": 0, "open_until": 0.0, "lock": threading.Lock()}
CB_THRESHOLD = 5
CB_RESET_AFTER = 60


def _circuit_open() -> bool:
    with _cb["lock"]:
        now = time.time()
        if _cb["open_until"] > now:
            return True
        if _cb["failures"] >= CB_THRESHOLD:
            _cb["open_until"] = now + CB_RESET_AFTER
            _cb["failures"] = 0
            return True
        return False


def _record_success():
    with _cb["lock"]:
        _cb["failures"] = 0
        _cb["open_until"] = 0.0


def _record_failure():
    with _cb["lock"]:
        _cb["failures"] += 1


def preflight(
    tool_name: str,
    est_cost_usd: float,
    entity_id: str,
    tenant_id: str = "default",
) -> Literal["allow", "deny"]:
    """
    Check Paperclip budget before executing a tool.
    Returns 'allow' or 'deny'. Fails open (allow) if Paperclip unreachable.

    Emergency override: set BUDGET_OVERRIDE=true in env to bypass.
    """
    if os.environ.get("BUDGET_OVERRIDE", "").lower() == "true":
        return "allow"

    if _circuit_open():
        print(f"[BudgetGate] Circuit open — allowing {tool_name} without check (Paperclip down)")
        return "allow"

    payload = json.dumps({
        "tool_name": tool_name,
        "est_cost_usd": est_cost_usd,
        "entity_id": entity_id,
        "tenant_id": tenant_id,
    }).encode()

    req = urllib.request.Request(
        f"{PAPERCLIP_URL}/api/v1/budget/preflight",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=PREFLIGHT_TIMEOUT) as resp:
            data = json.loads(resp.read().decode())
            _record_success()
            decision = data.get("decision", "allow")
            if decision == "deny":
                reason = data.get("reason", "budget exceeded")
                print(f"[BudgetGate] DENIED: {tool_name} for {entity_id} — {reason}")
            return decision
    except urllib.error.URLError:
        _record_failure()
        print(f"[BudgetGate] Paperclip unreachable — allowing {tool_name} with warning")
        return "allow"
    except Exception as e:
        _record_failure()
        print(f"[BudgetGate] Preflight error: {e} — allowing {tool_name} with warning")
        return "allow"


def require_budget(tool_name: str, est_cost_usd: float, entity_id: str, tenant_id: str = "default") -> bool:
    """Convenience wrapper: returns True if allowed, raises RuntimeError if denied."""
    decision = preflight(tool_name, est_cost_usd, entity_id, tenant_id)
    if decision == "deny":
        raise RuntimeError(
            f"Budget gate denied '{tool_name}' for entity '{entity_id}' "
            f"(tenant: {tenant_id}). Check Paperclip dashboard."
        )
    return True


def register_budget_webhook(workflow_id: str, reason: str, checkpoint_id: str) -> None:
    """
    Handle Contract 3: Paperclip → CrewAI budget-exceeded webhook.
    Saves pause signal to state; crew checks this at next step_callback.
    """
    from governance.core import state_manager
    state_manager.save_entity(
        tenant_id="system",
        entity_id=workflow_id,
        key="budget_pause",
        value={
            "reason": reason,
            "checkpoint_id": checkpoint_id,
            "paused_at": time.time(),
        }
    )
    print(f"[BudgetGate] Pause registered for workflow {workflow_id}: {reason}")


def is_paused(workflow_id: str) -> bool:
    """Check if a workflow has been paused by a budget-exceeded webhook."""
    from governance.core import state_manager
    data = state_manager.get_entity("system", workflow_id)
    return "budget_pause" in data
