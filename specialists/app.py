"""
OpenSwarm Specialist Layer — FastAPI server on :8080.
Provides Contract 4 (entity memory bridge) and Contract 5 (specialist delegation).
CrewAI calls this when it needs a specialist action or Composio integration.

Endpoints:
  GET  /health
  GET  /entity/{entity_id}/memory       — Contract 4: context bridge
  POST /delegate                        — Contract 5: specialist handoff
  POST /webhook/budget-exceeded         — Contract 3: Paperclip pause webhook
"""
import os
import time
import uuid
import asyncio
from typing import Optional, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from governance.core import state_manager, budget_gate
from governance.integrations.slack_bridge import notify_agent_activity

app = FastAPI(
    title="OpenSwarm Specialist Layer",
    description="Agency Swarm specialist agents with Composio integrations",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-progress delegation tracking
_delegations: dict = {}


# ── Request / Response Models ─────────────────────────────────────────────────

class DelegateRequest(BaseModel):
    task_spec: str
    specialist_type: str  # slack, email, calendar, crm, research, code
    metadata: dict = {}
    context_snapshot: dict = {}
    callback_url: Optional[str] = None
    tenant_id: str = "default"
    entity_id: str = "default"


class DelegateResponse(BaseModel):
    delegation_id: str
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None


class BudgetWebhookPayload(BaseModel):
    workflow_id: str
    reason: str
    checkpoint_id: str
    tenant_id: str = "default"


# ── Specialist Registry ───────────────────────────────────────────────────────

SPECIALIST_INSTRUCTIONS = {
    "slack": "You are a Slack specialist. Use Composio Slack tools to send messages, read channels, and manage notifications. Always confirm before sending to external channels.",
    "email": "You are an email specialist. Use Composio Gmail tools to draft, send, read, and organize emails. Follow professional email standards.",
    "calendar": "You are a calendar specialist. Use Composio Google Calendar tools to check availability, create events, and manage schedules.",
    "crm": "You are a CRM specialist. Use Composio HubSpot tools to manage contacts, deals, and activities. Keep all records current.",
    "research": "You are a research specialist. Search the web, synthesize findings, and produce structured research briefs.",
    "code": "You are a code specialist. Write, review, and debug code. Produce clean, well-tested implementations.",
}


def _run_specialist(
    delegation_id: str,
    specialist_type: str,
    task_spec: str,
    context_snapshot: dict,
    tenant_id: str,
    entity_id: str,
) -> str:
    """Run a specialist agent synchronously via Agency Swarm."""

    # Budget pre-flight for Composio actions
    allowed = budget_gate.preflight(
        tool_name=f"specialist:{specialist_type}",
        est_cost_usd=0.05,
        entity_id=entity_id,
        tenant_id=tenant_id,
    )
    if allowed == "deny":
        return f"[DENIED] Budget gate blocked {specialist_type} action for {entity_id}"

    try:
        from agency_swarm import Agent
        from agency_swarm.tools import BaseTool
        from governance.specialists.tools.composio_tools import get_specialist_tools

        tools = get_specialist_tools(specialist_type)
        instructions = SPECIALIST_INSTRUCTIONS.get(specialist_type, "You are a general assistant.")

        # Include context snapshot in the task
        context_str = ""
        if context_snapshot:
            import json
            context_str = f"\n\nContext:\n{json.dumps(context_snapshot, indent=2, default=str)[:2000]}"

        agent = Agent(
            name=f"{specialist_type.title()}Specialist",
            description=f"Specialist agent for {specialist_type} tasks",
            instructions=instructions + context_str,
            tools=tools,
            model=os.environ.get("SPECIALIST_MODEL", os.environ.get("EXPERT_MODEL", "deepseek/deepseek-chat-v4")),
            temperature=0.2,
        )

        # Run with Agency Swarm's direct completion
        result = agent.get_completion(task_spec)

        # Save result to entity memory (Contract 4)
        state_manager.save_entity(tenant_id, entity_id, f"specialist_{specialist_type}_last", {
            "task": task_spec[:200],
            "result": str(result)[:1000],
            "completed_at": time.time(),
        })

        notify_agent_activity(tenant_id, f"{specialist_type.title()}Specialist", f"Completed: {task_spec[:100]}", "success")
        return str(result)

    except Exception as e:
        error_msg = f"[SpecialistError] {specialist_type}: {e}"
        notify_agent_activity(tenant_id, f"{specialist_type.title()}Specialist", error_msg, "error")
        return error_msg


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "openswarm-specialist-layer", "version": "1.0.0"}


@app.get("/entity/{entity_id}/memory")
def get_entity_memory(entity_id: str, tenant_id: str = "default"):
    """
    Contract 4: Context Bridge — CrewAI queries entity memory before Composio actions.
    Returns all stored entity context for the given entity_id.
    """
    data = state_manager.get_entity(tenant_id, entity_id)
    return {
        "entity_id": entity_id,
        "tenant_id": tenant_id,
        "context": data,
        "retrieved_at": time.time(),
    }


@app.post("/delegate", response_model=DelegateResponse)
async def delegate_to_specialist(req: DelegateRequest, background_tasks: BackgroundTasks):
    """
    Contract 5: Specialist Handoff — CrewAI delegates to OpenSwarm specialist.
    Runs synchronously (for simplicity); callback_url gets result when done.
    """
    delegation_id = str(uuid.uuid4())[:8]
    _delegations[delegation_id] = {"status": "running", "started_at": time.time()}

    if req.specialist_type not in SPECIALIST_INSTRUCTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown specialist type: {req.specialist_type}. "
                   f"Valid types: {list(SPECIALIST_INSTRUCTIONS.keys())}"
        )

    # Run synchronously in background thread
    def run_and_store():
        result = _run_specialist(
            delegation_id=delegation_id,
            specialist_type=req.specialist_type,
            task_spec=req.task_spec,
            context_snapshot=req.context_snapshot,
            tenant_id=req.tenant_id,
            entity_id=req.entity_id,
        )
        _delegations[delegation_id] = {
            "status": "complete",
            "result": result,
            "completed_at": time.time(),
        }
        # Fire callback if provided
        if req.callback_url:
            import urllib.request, json
            try:
                payload = json.dumps({"delegation_id": delegation_id, "result": result}).encode()
                r = urllib.request.Request(req.callback_url, data=payload,
                    headers={"Content-Type": "application/json"}, method="POST")
                urllib.request.urlopen(r, timeout=5)
            except Exception:
                pass

    import threading
    thread = threading.Thread(target=run_and_store, daemon=True)
    thread.start()
    thread.join(timeout=120)  # Wait up to 2 min

    delegation = _delegations.get(delegation_id, {})
    return DelegateResponse(
        delegation_id=delegation_id,
        status=delegation.get("status", "timeout"),
        result=delegation.get("result"),
        error=delegation.get("error"),
    )


@app.get("/delegate/{delegation_id}")
def get_delegation_status(delegation_id: str):
    """Check status of a delegation request."""
    delegation = _delegations.get(delegation_id)
    if not delegation:
        raise HTTPException(status_code=404, detail="Delegation not found")
    return {"delegation_id": delegation_id, **delegation}


@app.post("/webhook/budget-exceeded")
def budget_exceeded_webhook(payload: BudgetWebhookPayload):
    """
    Contract 3: Paperclip → CrewAI pause signal.
    Registers a pause marker that GovernanceCrew checks before next kickoff.
    """
    budget_gate.register_budget_webhook(
        workflow_id=payload.workflow_id,
        reason=payload.reason,
        checkpoint_id=payload.checkpoint_id,
    )
    notify_agent_activity(
        payload.tenant_id,
        "BudgetGate",
        f"Workflow {payload.workflow_id} paused: {payload.reason}",
        "warning",
    )
    return {"status": "paused", "workflow_id": payload.workflow_id}


@app.post("/webhook/budget-resume")
def budget_resume_webhook(workflow_id: str, tenant_id: str = "default"):
    """Resume a workflow that was paused by a budget-exceeded event."""
    state_manager.delete_entity("system", workflow_id)
    notify_agent_activity(tenant_id, "BudgetGate", f"Workflow {workflow_id} resumed", "success")
    return {"status": "resumed", "workflow_id": workflow_id}


@app.get("/tenants")
def list_tenants():
    return {"tenants": state_manager.list_tenants()}


@app.get("/tenants/{tenant_id}/summary")
def tenant_summary(tenant_id: str):
    return state_manager.get_tenant_summary(tenant_id)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("SPECIALIST_PORT", 8080))
    print(f"OpenSwarm Specialist Layer on :{port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
