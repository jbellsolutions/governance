"""
CEO Orchestrator — single conversational entry point for each business.

The user talks to the CEO; the CEO delegates to teams that run autonomously.
Real-time events flow to the panel via event_bus.
Conversation history persists across sessions (zero cold start).
"""
import os
import json
import threading
from typing import Optional

from openai import OpenAI

from governance.event_bus import publish
from governance.core import state_manager

_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_team",
            "description": (
                "Delegate an objective to one of your teams. The team runs autonomously "
                "in the background — you will see their progress in the panel. "
                "Use this when the objective requires execution, not just advice."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "team": {
                        "type": "string",
                        "enum": ["exec_team", "sales", "marketing"],
                        "description": (
                            "exec_team: strategic planning, exec reviews, financial oversight. "
                            "sales: pipeline management, outreach, customer success. "
                            "marketing: content, SEO, paid advertising."
                        ),
                    },
                    "objective": {
                        "type": "string",
                        "description": "Clear, specific objective for the team to accomplish.",
                    },
                },
                "required": ["team", "objective"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_status",
            "description": "Get current business status: active crews, recent activity, entity memory.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


class CEOOrchestrator:
    """
    Conversational CEO for one business.
    Persists conversation history; delegates to teams via tool calls.
    Thread-safe: each request acquires _lock before modifying history.
    """

    def __init__(self, business_id: str, business_name: str, tenant_id: str):
        self.business_id = business_id
        self.business_name = business_name
        self.tenant_id = tenant_id
        self._lock = threading.Lock()
        self._history: list[dict] = []
        self._model = os.environ.get("EXEC_MODEL", "anthropic/claude-sonnet-4-6")
        self._client = OpenAI(
            api_key=os.environ.get("OPENROUTER_API_KEY", os.environ.get("OPENAI_API_KEY", "")),
            base_url=os.environ.get("OPENAI_BASE_URL", "https://openrouter.ai/api/v1"),
        )
        self._system_prompt = (
            f"You are the CEO of {business_name}, an AI-run autonomous business. "
            "You are the single point of contact for the business owner — they talk to you, "
            "and you coordinate everything. "
            "\n\nYour teams:"
            "\n• Executive Team (exec_team) — strategic planning, exec reviews, budget oversight"
            "\n• Sales Team (sales) — pipeline management, outreach, customer success"
            "\n• Marketing Team (marketing) — content creation, SEO, paid advertising"
            "\n\nWhen you delegate to a team, they run autonomously. "
            "The owner can watch live in the panel. "
            "Give crisp, decisive responses. "
            "Use run_team when execution is needed, not just strategy."
        )

    # ── History persistence ───────────────────────────────────────────────────

    def _load_history(self) -> None:
        checkpoint = state_manager.load_checkpoint(
            self.tenant_id, f"ceo_conversation:{self.business_id}"
        )
        if checkpoint and isinstance(checkpoint.get("history"), list):
            self._history = checkpoint["history"]

    def _save_history(self) -> None:
        state_manager.save_checkpoint(
            self.tenant_id,
            f"ceo_conversation:{self.business_id}",
            {"history": self._history[-60:]},
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def chat(self, message: str) -> str:
        """
        Send a message to the CEO. Returns the CEO's response.
        May trigger background team runs as a side-effect.
        """
        with self._lock:
            self._load_history()

            publish(
                "user_message",
                self.business_id,
                agent_name="CEO",
                message=f"You: {message[:200]}",
                level="info",
            )

            self._history.append({"role": "user", "content": message})

            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    *self._history,
                ],
                tools=_TOOLS,
                tool_choice="auto",
            )

            msg = response.choices[0].message

            if msg.tool_calls:
                # Serialize message for history (drop None fields)
                msg_dict = {"role": "assistant", "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in msg.tool_calls
                ]}
                if msg.content:
                    msg_dict["content"] = msg.content
                self._history.append(msg_dict)

                tool_results = []
                for tc in msg.tool_calls:
                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        args = {}

                    if tc.function.name == "run_team":
                        result = self._spawn_team(args.get("team", ""), args.get("objective", ""))
                    elif tc.function.name == "get_status":
                        result = json.dumps(self._get_status(), indent=2)
                    else:
                        result = f"Unknown tool: {tc.function.name}"

                    tool_results.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": str(result),
                    })

                self._history.extend(tool_results)

                follow_up = self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": self._system_prompt},
                        *self._history,
                    ],
                )
                final = follow_up.choices[0].message.content or ""
                self._history.append({"role": "assistant", "content": final})
            else:
                final = msg.content or ""
                self._history.append({"role": "assistant", "content": final})

            publish(
                "ceo_response",
                self.business_id,
                agent_name="CEO",
                message=final[:300],
                level="info",
            )

            self._save_history()
            return final

    def reset_conversation(self) -> None:
        """Clear conversation history."""
        with self._lock:
            self._history = []
            state_manager.delete_checkpoint(
                self.tenant_id, f"ceo_conversation:{self.business_id}"
            )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _spawn_team(self, team_type: str, objective: str) -> str:
        """Launch a GovernanceCrew in a background thread."""
        valid = {"exec_team", "sales", "marketing"}
        if team_type not in valid:
            return f"Unknown team '{team_type}'. Valid: {sorted(valid)}"

        publish(
            "team_start",
            self.business_id,
            team_id=team_type,
            agent_name="CEO",
            message=f"Delegating to {team_type}: {objective[:200]}",
            level="info",
        )

        # Team execution now lives in Paperclip (heartbeat agents + routines), not in
        # an in-process CrewAI crew. This legacy standalone panel can record the
        # delegation intent and chat, but the teams actually run inside Paperclip.
        state_manager.save_entity(self.tenant_id, self.business_id, f"team_{team_type}_last", {
            "objective": objective,
            "note": "Delegated. Teams run in Paperclip — see the Paperclip board.",
        })
        publish(
            "team_complete",
            self.business_id,
            team_id=team_type,
            agent_name=team_type.upper(),
            message="Delegation recorded. Teams run in Paperclip (board).",
            level="info",
        )
        return (
            f"Recorded a delegation to {team_type}: '{objective[:100]}'. "
            "In the Paperclip-native setup, the team runs as heartbeat agents in the "
            "Paperclip board — open it to watch them work."
        )

    def _get_status(self) -> dict:
        summary = state_manager.get_tenant_summary(self.tenant_id)
        recent = state_manager.get_workflow_log(self.tenant_id, "executive_team", limit=5)
        teams_memory = state_manager.get_entity(self.tenant_id, self.business_id)
        return {
            "business": self.business_name,
            "tenant_id": self.tenant_id,
            "summary": summary,
            "recent_logs": recent,
            "teams_last_results": {
                k: v for k, v in teams_memory.items() if k.startswith("team_")
            },
        }
