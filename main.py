"""
Autonomous Agent Governance System
Entry point — Paperclip-native. This repo provides the Integrations sidecar and
business company packages; Paperclip itself is the panel / orchestration plane.

Usage:
  python main.py --specialists         # Start the Integrations sidecar (:8080)  ← primary
  python main.py --archivist           # Backup sync: Paperclip -> Obsidian + Notion
  python main.py --slack-relay         # Slack <-> Paperclip relay (talk to your CEO)
  python main.py --status              # System health check
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


def cmd_specialists(port: int = 8080):
    """Start the Integrations sidecar (OpenSwarm/Composio specialist tools)."""
    import uvicorn
    from governance.specialists.app import app
    print(f"\nIntegrations Sidecar: http://0.0.0.0:{port}")
    print(f"  Agents' real tools (research/email/calendar/crm via Composio)")
    print(f"  API docs: http://localhost:{port}/docs")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


def cmd_archivist():
    """Run the Paperclip → Obsidian/Notion backup sync (long-lived)."""
    from governance.backup.paperclip_sync import main as sync_main
    sync_main()


def cmd_slack_relay():
    """Run the Slack <-> Paperclip relay (talk to your CEO from Slack)."""
    from governance.integrations.slack_paperclip import main as relay_main
    relay_main()


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

    # Backup sinks
    from governance.backup import archivist
    cfg = archivist.configured()
    print("\nBackup sinks:")
    print(f"  {'✓' if cfg['obsidian'] else '✗'} Obsidian (OBSIDIAN_VAULT_PATH)")
    print(f"  {'✓' if cfg['notion_api'] or cfg['notion_via_sidecar'] else '✗'} Notion "
          f"({'direct API' if cfg['notion_api'] else 'via sidecar' if cfg['notion_via_sidecar'] else 'unconfigured'})")


def main():
    parser = argparse.ArgumentParser(description="Governance — Paperclip-native Integrations sidecar + tooling")
    parser.add_argument("--specialists",  action="store_true",  help="Start the Integrations sidecar (:8080)")
    parser.add_argument("--archivist",    action="store_true",  help="Backup sync: Paperclip → Obsidian + Notion")
    parser.add_argument("--slack-relay",  dest="slack_relay", action="store_true", help="Slack <-> Paperclip relay (talk to your CEO)")
    parser.add_argument("--status",       action="store_true",  help="System health check")
    parser.add_argument("--port",         type=int, default=8000, help="Port for API server")

    args = parser.parse_args()

    if not any([args.specialists, args.archivist, args.slack_relay, args.status]):
        parser.print_help()
        print("\nQuick start:")
        print("  python main.py --specialists                   # Integrations sidecar — the agents' tools (:8080)")
        print("  python main.py --archivist                     # back up every action to Obsidian + Notion")
        print("  python main.py --slack-relay                   # talk to your CEO from Slack")
        print("  python main.py --status                        # health check")
        print("\nThe panel, companies, agents, and budgets live in Paperclip:")
        print("  npx -y paperclipai@latest onboard --yes        # start the Paperclip board")
        print("  Then import paperclip/companies/lead-gen-agency (see README).")
        return

    if args.status:
        cmd_status()
    elif args.specialists:
        cmd_specialists(args.port or 8080)
    elif args.archivist:
        cmd_archivist()
    elif args.slack_relay:
        cmd_slack_relay()


if __name__ == "__main__":
    main()
