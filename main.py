"""
Autonomous Agent Governance System
Entry point — Paperclip-native. This repo provides the Integrations sidecar and
business company packages; Paperclip itself is the panel / orchestration plane.

Usage:
  python main.py --specialists         # Start the Integrations sidecar (:8080)  ← primary
  python main.py --slack               # Start Slack bridge only (:3001)
  python main.py --status              # System health check
  python main.py --panel               # Legacy standalone panel (:8000) — optional
  python main.py --serve               # Legacy governance API (:8000) — optional
"""
import os
import sys
import argparse
from dotenv import load_dotenv

load_dotenv()

# OpenRouter setup — must happen before any LLM import
if "OPENROUTER_API_KEY" in os.environ:
    os.environ["OPENAI_API_KEY"] = os.environ["OPENROUTER_API_KEY"]
os.environ.setdefault("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")


def cmd_panel(port: int = 8000):
    """Start the governance web panel — the primary interface."""
    import uvicorn
    from governance.panel import app
    print(f"\nGovernance Panel: http://0.0.0.0:{port}")
    print(f"  Web UI:   http://localhost:{port}/")
    print(f"  API docs: http://localhost:{port}/docs")
    print(f"\nOpen http://localhost:{port} in your browser to manage businesses.")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


def cmd_serve(port: int = 8000):
    """Start the FastAPI governance control plane."""
    import uvicorn
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    app = FastAPI(
        title="Governance Control Plane",
        description="Paperclip + CrewAI + OpenSwarm governance API",
        version="1.0.0",
    )
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    @app.get("/health")
    def health():
        return {"status": "ok", "version": "1.0.0"}

    @app.get("/status")
    def system_status():
        from governance.core import state_manager
        return {
            "services": {
                "openrouter_key": bool(os.environ.get("OPENROUTER_API_KEY")),
                "slack_token": bool(os.environ.get("SLACK_BOT_TOKEN")),
                "composio_key": bool(os.environ.get("COMPOSIO_API_KEY")),
                "paperclip_url": os.environ.get("PAPERCLIP_URL", "http://localhost:3000"),
                "state_db": os.environ.get("STATE_DB_PATH", "/data/governance.db"),
            },
            "tenants": state_manager.list_tenants(),
        }

    @app.get("/tenants/{tenant_id}/logs")
    def get_logs(tenant_id: str, crew_id: str = "executive_team", limit: int = 50):
        from governance.core import state_manager
        return state_manager.get_workflow_log(tenant_id, crew_id, limit)

    @app.post("/webhook/budget-exceeded")
    def budget_exceeded(workflow_id: str, reason: str, checkpoint_id: str = ""):
        from governance.core.budget_gate import register_budget_webhook
        register_budget_webhook(workflow_id, reason, checkpoint_id)
        return {"status": "paused", "workflow_id": workflow_id}

    # Start Slack bridge in background if configured
    if os.environ.get("SLACK_BOT_TOKEN"):
        from governance.integrations.slack_bridge import start_slack_server
        start_slack_server(port=3001)
        print("Slack bridge started on :3001")

    print(f"\nGovernance Control Plane: http://0.0.0.0:{port}")
    print(f"API docs:                  http://localhost:{port}/docs")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


def cmd_specialists(port: int = 8080):
    """Start the Integrations sidecar (OpenSwarm/Composio specialist tools)."""
    import uvicorn
    from governance.specialists.app import app
    print(f"\nIntegrations Sidecar: http://0.0.0.0:{port}")
    print(f"  Agents' real tools (research/email/calendar/crm via Composio)")
    print(f"  API docs: http://localhost:{port}/docs")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


def cmd_slack():
    """Start Slack bridge in foreground (for testing)."""
    import time
    from governance.integrations.slack_bridge import start_slack_server, notify_agent_activity
    server = start_slack_server(3001)
    print("Slack bridge on :3001")
    print("  POST /slack/commands  — slash commands")
    print("  POST /slack/actions   — interactive button actions")

    if os.environ.get("SLACK_BOT_TOKEN"):
        ok = notify_agent_activity("System", "GovernanceSystem", "Slack bridge started", "success")
        print(f"Test notification: {'sent' if ok else 'failed (check SLACK_BOT_TOKEN)'}")

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("\nSlack bridge stopped.")
        server.shutdown()


def cmd_status():
    """Print system health."""
    from governance.core import state_manager
    print("\n=== Governance System Status ===")
    checks = {
        "OPENROUTER_API_KEY": bool(os.environ.get("OPENROUTER_API_KEY")),
        "SLACK_BOT_TOKEN":    bool(os.environ.get("SLACK_BOT_TOKEN")),
        "COMPOSIO_API_KEY":   bool(os.environ.get("COMPOSIO_API_KEY")),
        "PAPERCLIP_URL":      os.environ.get("PAPERCLIP_URL", "http://localhost:3000"),
        "STATE_DB_PATH":      os.environ.get("STATE_DB_PATH", "(local ./data/governance.db)"),
    }
    for k, v in checks.items():
        status = "✓" if v else "✗"
        print(f"  {status} {k}: {v}")

    tenants = state_manager.list_tenants()
    print(f"\nActive tenants: {tenants or '(none yet)'}")

    try:
        import agency_swarm
        print(f"Agency Swarm (Integrations sidecar): installed")
    except Exception:
        print("Agency Swarm: not installed")


def main():
    parser = argparse.ArgumentParser(description="Governance — Paperclip-native Integrations sidecar + tooling")
    parser.add_argument("--specialists",  action="store_true",  help="Start the Integrations sidecar (:8080)")
    parser.add_argument("--slack",        action="store_true",  help="Start Slack bridge only (:3001)")
    parser.add_argument("--status",       action="store_true",  help="System health check")
    parser.add_argument("--panel",        action="store_true",  help="Legacy standalone panel (:8000) — optional")
    parser.add_argument("--serve",        action="store_true",  help="Legacy governance API (:8000) — optional")
    parser.add_argument("--port",         type=int, default=8000, help="Port for API server")

    args = parser.parse_args()

    if not any([args.panel, args.serve, args.specialists, args.slack, args.status]):
        parser.print_help()
        print("\nQuick start:")
        print("  python main.py --specialists                   # Integrations sidecar — the agents' tools (:8080)")
        print("  python main.py --status                        # health check")
        print("\nThe panel, companies, agents, and budgets live in Paperclip:")
        print("  npx -y paperclipai@latest onboard --yes        # start the Paperclip board")
        print("  Then import paperclip/companies/lead-gen-agency (see README).")
        return

    if args.status:
        cmd_status()
    elif args.specialists:
        cmd_specialists(args.port or 8080)
    elif args.slack:
        cmd_slack()
    elif args.panel:
        cmd_panel(args.port)
    elif args.serve:
        cmd_serve(args.port)


if __name__ == "__main__":
    main()
