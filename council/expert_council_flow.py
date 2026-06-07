"""
5-Round Expert Council Deliberation
Paperclip vs CrewAI vs OpenSwarm — which platform wins which role?

Requires: OPENROUTER_API_KEY, OPENAI_BASE_URL=https://openrouter.ai/api/v1
"""
import os
import sys
import json
import time
from datetime import datetime
from typing import Optional

# OpenRouter setup — must happen before any agency_swarm imports
os.environ.setdefault("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
if "OPENROUTER_API_KEY" in os.environ:
    os.environ["OPENAI_API_KEY"] = os.environ["OPENROUTER_API_KEY"]

from agency_swarm import Agency, set_openai_client
from openai import OpenAI

# Point agency_swarm at OpenRouter
client = OpenAI(
    api_key=os.environ.get("OPENROUTER_API_KEY", os.environ.get("OPENAI_API_KEY")),
    base_url="https://openrouter.ai/api/v1",
)
set_openai_client(client)

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from governance.council.agents.paperclip_expert import create_paperclip_expert
from governance.council.agents.crewai_expert import create_crewai_expert
from governance.council.agents.openswarm_expert import create_openswarm_expert
from governance.council.agents.council_moderator import create_council_moderator


ROUND_PROMPTS = {
    1: {
        "title": "Core Strengths",
        "paperclip": (
            "Round 1 — Core Strengths. You are PaperclipExpert. "
            "State Paperclip's top 3 capabilities with specific technical evidence. "
            "Be concrete — cite feature names, code patterns, or metrics. "
            "Max 300 words."
        ),
        "crewai": (
            "Round 1 — Core Strengths. You are CrewAIExpert. "
            "State CrewAI's top 3 capabilities with specific technical evidence. "
            "Be concrete — cite feature names, decorators, or production metrics. "
            "Max 300 words."
        ),
        "openswarm": (
            "Round 1 — Core Strengths. You are OpenSwarmExpert. "
            "State OpenSwarm's top 3 capabilities with specific technical evidence. "
            "Be concrete — cite Composio apps, routing patterns, or integration counts. "
            "Max 300 words."
        ),
    },
    2: {
        "title": "Honest Weaknesses",
        "paperclip": (
            "Round 2 — Honest Weaknesses. Critically analyze Paperclip's three biggest "
            "limitations for running autonomous AI businesses. Be brutally honest — "
            "what does Paperclip genuinely fail at that CrewAI and OpenSwarm handle better? "
            "Max 300 words."
        ),
        "crewai": (
            "Round 2 — Honest Weaknesses. Critically analyze CrewAI's three biggest "
            "limitations for running autonomous AI businesses. Be brutally honest — "
            "what does CrewAI genuinely fail at that Paperclip and OpenSwarm handle better? "
            "Max 300 words."
        ),
        "openswarm": (
            "Round 2 — Honest Weaknesses. Critically analyze OpenSwarm's three biggest "
            "limitations for running autonomous AI businesses. Be brutally honest — "
            "what does OpenSwarm genuinely fail at that Paperclip and CrewAI handle better? "
            "Max 300 words."
        ),
    },
    3: {
        "title": "Cross-Examination",
        "paperclip": (
            "Round 3 — Cross-Examination. You are PaperclipExpert. "
            "Challenge this specific claim by OpenSwarmExpert: "
            "'Composio's 10,000 integrations make OpenSwarm the best platform for autonomous business ops.' "
            "What does Paperclip offer that makes integration breadth secondary to governance control? "
            "Max 300 words."
        ),
        "crewai": (
            "Round 3 — Cross-Examination. You are CrewAIExpert. "
            "Challenge this specific claim by PaperclipExpert: "
            "'Paperclip's dashboard is the most important feature for running autonomous AI businesses.' "
            "Argue why orchestration depth and memory are more critical than UI dashboards. "
            "Max 300 words."
        ),
        "openswarm": (
            "Round 3 — Cross-Examination. You are OpenSwarmExpert. "
            "Challenge this specific claim by CrewAIExpert: "
            "'CrewAI Flows with @persist and hierarchical process is sufficient for any autonomous business workflow.' "
            "Argue why explicit specialist routing and 10,000 integrations cannot be replicated by CrewAI alone. "
            "Max 300 words."
        ),
    },
    4: {
        "title": "Integration Potential",
        "paperclip": (
            "Round 4 — Integration Potential. You are PaperclipExpert. "
            "Describe specifically how Paperclip best integrates with CrewAI and OpenSwarm "
            "in a unified governance architecture. What webhooks, APIs, or events does Paperclip "
            "expose that the other two systems should consume? Be technically precise. "
            "Max 300 words."
        ),
        "crewai": (
            "Round 4 — Integration Potential. You are CrewAIExpert. "
            "Describe specifically how CrewAI best integrates with Paperclip and OpenSwarm "
            "in a unified governance architecture. What callbacks, events, and state should "
            "CrewAI share with the other two systems? Be technically precise. "
            "Max 300 words."
        ),
        "openswarm": (
            "Round 4 — Integration Potential. You are OpenSwarmExpert. "
            "Describe specifically how OpenSwarm best integrates with Paperclip and CrewAI "
            "in a unified governance architecture. What FastAPI endpoints, Composio actions, "
            "and agent handoffs should OpenSwarm expose to the other two systems? Be technically precise. "
            "Max 300 words."
        ),
    },
    5: {
        "title": "Final Verdict",
        "moderator": (
            "Round 5 — Final Verdict. You have witnessed 4 rounds of expert deliberation. "
            "Now synthesize everything into the definitive governance architecture verdict. "
            "\n\nYour analysis must cover:\n"
            "1. Which claims from each expert survived cross-examination\n"
            "2. Which claims were successfully refuted\n"
            "3. The optimal role for each platform in a unified system\n"
            "4. Specific technical integration points between the three\n"
            "5. Score each platform on all 9 dimensions (1-10)\n"
            "\nEnd with the complete JSON verdict block as specified in your instructions. "
            "This verdict will drive the actual implementation."
        ),
    },
}


def call_agent_directly(agent, prompt: str) -> str:
    """Call an agent using the OpenRouter client directly (bypasses agency routing)."""
    messages = [
        {
            "role": "system",
            "content": agent.instructions if isinstance(agent.instructions, str) else str(agent.instructions),
        },
        {"role": "user", "content": prompt},
    ]
    resp = client.chat.completions.create(
        model=agent.model,
        messages=messages,
        temperature=agent.temperature if hasattr(agent, "temperature") else 0.4,
        max_tokens=1000,
    )
    return resp.choices[0].message.content


def run_round(round_num: int, experts: dict, transcript: list) -> dict:
    """Run a single deliberation round. Returns dict of {agent_name: response}."""
    config = ROUND_PROMPTS[round_num]
    title = config["title"]
    print(f"\n{'='*60}")
    print(f"  ROUND {round_num}: {title.upper()}")
    print(f"{'='*60}\n")

    round_responses = {}

    if round_num == 5:
        # Moderator synthesizes all previous rounds
        context = "\n\n".join([
            f"=== {e['round']} | {e['agent']} ===\n{e['response']}"
            for e in transcript
        ])
        full_prompt = (
            f"Here is the complete transcript from Rounds 1-4:\n\n{context}\n\n"
            + config["moderator"]
        )
        print("Moderator synthesizing all rounds...")
        response = call_agent_directly(experts["moderator"], full_prompt)
        round_responses["moderator"] = response
        print(f"\n[MODERATOR VERDICT]\n{response}\n")
    else:
        for agent_key in ["paperclip", "crewai", "openswarm"]:
            if agent_key not in config:
                continue
            agent = experts[agent_key]
            prompt = config[agent_key]

            # Include previous rounds as context
            if transcript:
                prev_context = "\n\n".join([
                    f"=== {e['round']} | {e['agent']} ===\n{e['response']}"
                    for e in transcript[-9:]  # Last 3 rounds × 3 agents
                ])
                prompt = f"Previous deliberation context:\n{prev_context}\n\n---\n\n{prompt}"

            agent_name = agent.name
            print(f"[{agent_name}] arguing...")
            response = call_agent_directly(agent, prompt)
            round_responses[agent_key] = response
            print(f"\n[{agent_name.upper()}]\n{response}\n")
            time.sleep(0.5)  # Brief pause between calls

    return round_responses


def extract_verdict(round5_response: str) -> Optional[dict]:
    """Extract JSON verdict from moderator's Round 5 response."""
    import re
    json_match = re.search(r"```json\s*(.*?)\s*```", round5_response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding raw JSON object
    json_match = re.search(r"\{[^{}]*\"verdict_version\"[^{}]*\}", round5_response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def save_transcript(transcript: list, verdict: Optional[dict]) -> str:
    """Save full deliberation transcript to file."""
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = {
        "timestamp": timestamp,
        "rounds_completed": len(set(e["round"] for e in transcript)),
        "transcript": transcript,
        "verdict": verdict,
    }

    path = os.path.join(output_dir, f"council_verdict_{timestamp}.json")
    with open(path, "w") as f:
        json.dump(output, f, indent=2)

    return path


def run_council() -> dict:
    """Run the full 5-round Expert Council deliberation."""
    print("\n" + "="*60)
    print("  AUTONOMOUS AGENT GOVERNANCE EXPERT COUNCIL")
    print("  5-Round Platform Deliberation")
    print("  Paperclip vs CrewAI vs OpenSwarm")
    print("="*60)

    # Initialize experts
    print("\nInitializing expert agents...")
    experts = {
        "paperclip": create_paperclip_expert(),
        "crewai": create_crewai_expert(),
        "openswarm": create_openswarm_expert(),
        "moderator": create_council_moderator(),
    }
    print(f"  PaperclipExpert   → {experts['paperclip'].model}")
    print(f"  CrewAIExpert      → {experts['crewai'].model}")
    print(f"  OpenSwarmExpert   → {experts['openswarm'].model}")
    print(f"  CouncilModerator  → {experts['moderator'].model}")

    transcript = []
    verdict = None

    for round_num in range(1, 6):
        round_responses = run_round(round_num, experts, transcript)

        title = ROUND_PROMPTS[round_num]["title"]
        for agent_key, response in round_responses.items():
            agent_name = experts[agent_key].name
            transcript.append({
                "round": f"Round {round_num} — {title}",
                "agent": agent_name,
                "agent_key": agent_key,
                "response": response,
            })

        if round_num == 5:
            verdict = extract_verdict(round_responses.get("moderator", ""))

    # Save and report
    output_path = save_transcript(transcript, verdict)
    print(f"\n{'='*60}")
    print(f"  COUNCIL COMPLETE — 5 rounds finished")
    print(f"  Transcript saved: {output_path}")
    if verdict:
        print(f"\n  PLATFORM ROLES:")
        for platform, role in verdict.get("platform_roles", {}).items():
            print(f"    {platform.upper():12} → {role}")
    print(f"{'='*60}\n")

    return {"transcript": transcript, "verdict": verdict, "output_path": output_path}


if __name__ == "__main__":
    result = run_council()
    if result["verdict"]:
        print("\nFINAL SCORES:")
        for platform, scores in result["verdict"].get("scores", {}).items():
            total = sum(scores.values())
            print(f"  {platform.upper():12} total={total}/90")
