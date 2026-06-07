"""
Audit Event Stream — Contract 2 of 5.
Streams CrewAI step events to Paperclip's immutable audit log.
Fire-and-forget: never blocks agent execution.
"""
import os
import json
import time
import hashlib
import threading
import urllib.request
from typing import Any

PAPERCLIP_URL = os.environ.get("PAPERCLIP_URL", "http://localhost:3000")

# Local fallback log when Paperclip is unavailable
_DEFAULT_LOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "audit.jsonl")
_LOCAL_LOG = os.environ.get("AUDIT_LOG_PATH", _DEFAULT_LOG)


def _hash_state(state: Any) -> str:
    try:
        serialized = json.dumps(state, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]
    except Exception:
        return "hash-error"


def _write_local(event: dict) -> None:
    try:
        os.makedirs(os.path.dirname(_LOCAL_LOG), exist_ok=True)
        with open(_LOCAL_LOG, "a") as f:
            f.write(json.dumps(event) + "\n")
    except Exception:
        pass


def emit_event(
    step_id: str,
    agent_id: str,
    tool_calls: list,
    entity_state: Any = None,
    tenant_id: str = "default",
) -> None:
    """
    Emit a step event to Paperclip audit log.
    Non-blocking: dispatched to background thread immediately.
    Falls back to local JSONL file if Paperclip is unreachable.
    """
    event = {
        "step_id": step_id,
        "agent_id": str(agent_id),
        "tool_calls": tool_calls[:10],  # cap at 10 to stay within limits
        "entity_state_hash": _hash_state(entity_state) if entity_state else "",
        "timestamp": time.time(),
        "tenant_id": tenant_id,
    }

    def _send():
        try:
            payload = json.dumps(event, default=str).encode()
            req = urllib.request.Request(
                f"{PAPERCLIP_URL}/api/v1/audit/event",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=3):
                pass
        except Exception:
            _write_local(event)

    threading.Thread(target=_send, daemon=True).start()


def make_step_callback(tenant_id: str = "default", crew_id: str = "crew"):
    """
    Returns a CrewAI-compatible step_callback.
    Attach to Crew(step_callback=make_step_callback(tenant_id)).
    """
    counter = [0]

    def _callback(step_output):
        counter[0] += 1
        step_id = f"{tenant_id}:{crew_id}:step-{counter[0]}"

        # Normalize CrewAI's step output across versions
        if hasattr(step_output, "return_values"):
            # AgentFinish
            tool_calls = [{"type": "finish", "output": str(step_output.return_values)[:500]}]
            agent_id = getattr(step_output, "log", "agent")[:100]
        elif hasattr(step_output, "tool"):
            # AgentAction
            tool_calls = [{
                "tool": step_output.tool,
                "input": str(getattr(step_output, "tool_input", ""))[:300],
            }]
            agent_id = getattr(step_output, "log", "agent")[:100]
        elif isinstance(step_output, dict):
            tool_calls = step_output.get("tool_calls", [{"raw": str(step_output)[:300]}])
            agent_id = step_output.get("agent_id", "unknown")
        else:
            tool_calls = [{"raw": str(step_output)[:300]}]
            agent_id = "unknown"

        emit_event(step_id, agent_id, tool_calls, tenant_id=tenant_id)

    return _callback


def make_task_callback(tenant_id: str = "default"):
    """Returns a CrewAI-compatible task_callback for task-level audit events."""
    def _callback(task_output):
        step_id = f"{tenant_id}:task:{getattr(task_output, 'description', 'unknown')[:50]}"
        output = getattr(task_output, "raw", str(task_output))
        emit_event(
            step_id=step_id,
            agent_id=getattr(task_output, "agent", "task"),
            tool_calls=[{"type": "task_complete", "output": str(output)[:500]}],
            tenant_id=tenant_id,
        )
    return _callback
