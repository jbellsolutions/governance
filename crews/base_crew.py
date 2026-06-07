"""
GovernanceCrew — base wrapper for all CrewAI crews in this system.
Wires budget pre-flight, audit streaming, checkpoint/resume, and Slack alerts.
"""
import os
import time
from typing import Any, Optional

from crewai import LLM

from governance.core import budget_gate, audit_stream, state_manager


def make_llm(env_key: str, default_model: str) -> LLM:
    """Build an OpenRouter-backed LLM for use in CrewAI agents."""
    return LLM(
        model=os.environ.get(env_key, default_model),
        base_url=os.environ.get("OPENAI_BASE_URL", "https://openrouter.ai/api/v1"),
        api_key=os.environ.get("OPENROUTER_API_KEY", os.environ.get("OPENAI_API_KEY", "")),
    )


class GovernanceCrew:
    """
    Wraps a CrewAI Crew with:
      - Budget pre-flight via Paperclip (Contract 1)
      - Step audit stream to Paperclip (Contract 2)
      - SQLite checkpoint/resume — zero cold starts (Contract 3 support)
      - Slack alerts on budget denial or failure
    """

    def __init__(
        self,
        crew,
        tenant_id: str,
        crew_id: str,
        est_cost_per_run: float = 0.10,
        business_id: str = None,
    ):
        self.crew = crew
        self.tenant_id = tenant_id
        self.crew_id = crew_id
        self.est_cost_per_run = est_cost_per_run
        self.business_id = business_id or tenant_id

        # Wire callbacks — audit stream + real-time event bus
        self.crew.step_callback = self._make_step_callback()
        self.crew.task_callback = audit_stream.make_task_callback(tenant_id)

    def _make_step_callback(self):
        base = audit_stream.make_step_callback(self.tenant_id, self.crew_id)
        business_id = self.business_id
        crew_id = self.crew_id

        def wrapped(step_output):
            base(step_output)
            try:
                from governance.event_bus import publish
                if hasattr(step_output, "tool"):
                    agent_name = getattr(step_output, "log", crew_id)[:60]
                    msg = f"Tool call: {step_output.tool} — {str(getattr(step_output, 'tool_input', ''))[:120]}"
                elif hasattr(step_output, "return_values"):
                    agent_name = crew_id
                    msg = f"Finished: {str(step_output.return_values)[:150]}"
                else:
                    agent_name = crew_id
                    msg = str(step_output)[:150]
                publish("agent_step", business_id, team_id=crew_id,
                        agent_name=agent_name, message=msg, level="info")
            except Exception:
                pass

        return wrapped

    def kickoff(self, inputs: Optional[dict] = None) -> Any:
        """
        Run the crew with full governance:
          preflight → check pause → restore checkpoint → execute → checkpoint
        """
        inputs = inputs or {}

        # Contract 3: check if paused by a budget-exceeded webhook
        if budget_gate.is_paused(self.crew_id):
            msg = f"[GovernanceCrew] {self.crew_id} is paused by budget webhook. Resume via Slack or REST."
            print(msg)
            self._slack_alert(msg, "warning")
            return {"status": "paused", "crew_id": self.crew_id}

        # Contract 1: budget pre-flight
        decision = budget_gate.preflight(
            tool_name=f"crew:{self.crew_id}",
            est_cost_usd=self.est_cost_per_run,
            entity_id=self.crew_id,
            tenant_id=self.tenant_id,
        )
        if decision == "deny":
            msg = f"[GovernanceCrew] Budget gate denied {self.crew_id} for tenant {self.tenant_id}"
            print(msg)
            self._slack_alert(msg, "error")
            return {"status": "denied", "crew_id": self.crew_id, "reason": "budget_exceeded"}

        # Restore checkpoint context if available
        checkpoint = state_manager.load_checkpoint(self.tenant_id, self.crew_id)
        if checkpoint and checkpoint.get("status") != "completed":
            print(f"[GovernanceCrew] Resuming {self.crew_id} from checkpoint (tenant: {self.tenant_id})")
            inputs.setdefault("_prior_state", checkpoint)

        state_manager.log_event(self.tenant_id, self.crew_id, "kickoff_start", {"inputs_keys": list(inputs.keys())})

        try:
            result = self.crew.kickoff(inputs=inputs)
            state_manager.save_checkpoint(self.tenant_id, self.crew_id, {
                "status": "completed",
                "last_result_preview": str(result)[:500],
                "completed_at": time.time(),
            })
            state_manager.log_event(self.tenant_id, self.crew_id, "kickoff_complete")
            return result

        except Exception as e:
            # Persist failure state so resume can retry from here
            state_manager.save_checkpoint(self.tenant_id, self.crew_id, {
                "status": "failed",
                "error": str(e),
                "failed_at": time.time(),
                "inputs": {k: str(v)[:200] for k, v in inputs.items()},
            })
            state_manager.log_event(self.tenant_id, self.crew_id, "kickoff_error", {"error": str(e)})
            self._slack_alert(f"Crew {self.crew_id} failed: {e}", "error")
            raise

    def _slack_alert(self, message: str, level: str = "info") -> None:
        try:
            from governance.integrations.slack_bridge import notify_agent_activity
            notify_agent_activity(self.tenant_id, self.crew_id, message, level)
        except Exception:
            pass

    def resume(self) -> Any:
        """Explicitly resume a paused or failed crew from its last checkpoint."""
        # Clear budget pause if set
        state_manager.delete_entity("system", self.crew_id)
        checkpoint = state_manager.load_checkpoint(self.tenant_id, self.crew_id) or {}
        saved_inputs = checkpoint.get("inputs", {})
        return self.kickoff(inputs=saved_inputs)
