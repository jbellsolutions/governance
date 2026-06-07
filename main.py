"""
Autonomous Agent Governance System
Entry point — launch council deliberation or business teams

Usage:
  python main.py --council              # Run 5-round expert deliberation
  python main.py --business exec_team  # Launch executive crew
  python main.py --business sales      # Launch sales crew
  python main.py --business marketing  # Launch marketing crew
  python main.py --serve               # Start FastAPI governance server
  python main.py --slack               # Start Slack bridge only
"""
import os
import sys
import argparse
from dotenv import load_dotenv

load_dotenv()

# OpenRouter setup
if "OPENROUTER_API_KEY" in os.environ:
    os.environ["OPENAI_API_KEY"] = os.environ["OPENROUTER_API_KEY"]
os.environ.setdefault("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")


def cmd_council():
    """Run the 5-round Expert Council deliberation."""
    from governance.council.expert_council_flow import run_council
    result = run_council()
    return result


def cmd_business(biz_type: str, company_name: str = None):
    """Launch a business crew."""
    name = company_name or f"{biz_type.title()}Co"

    if biz_type == "exec_team":
        from governance.business_templates.executive_crew import create_executive_crew
        agency = create_executive_crew(name)
        print(f"\nExecutive Team launched for {name}")
        print("Agents: CEO, CMO, CTO, CFO")
        return agency

    elif biz_type == "sales":
        from governance.business_templates.sales_crew import create_sales_crew
        agency = create_sales_crew(name)
        print(f"\nSales Team launched for {name}")
        print("Agents: SDR, AE, CSM")
        return agency

    elif biz_type == "marketing":
        from governance.business_templates.marketing_crew import create_marketing_crew
        agency = create_marketing_crew(name)
        print(f"\nMarketing Team launched for {name}")
        print("Agents: Content, SEO, PaidAds")
        return agency

    else:
        print(f"Unknown business type: {biz_type}")
        print("Options: exec_team, sales, marketing")
        sys.exit(1)


def cmd_serve(port: int = 8080):
    """Start the FastAPI governance API server."""
    import uvicorn
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    app = FastAPI(
        title="Autonomous Agent Governance API",
        description="Control plane for Paperclip + CrewAI + OpenSwarm governance",
        version="1.0.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health():
        return {"status": "ok", "version": "1.0.0"}

    @app.post("/council/run")
    def run_council_endpoint():
        """Trigger 5-round expert council deliberation."""
        from governance.council.expert_council_flow import run_council
        result = run_council()
        return {
            "status": "complete",
            "rounds": 5,
            "verdict": result.get("verdict"),
            "output_path": result.get("output_path"),
        }

    @app.post("/business/{biz_type}/launch")
    def launch_business(biz_type: str, company_name: str = "AutoCo"):
        """Launch a business crew."""
        agency = cmd_business(biz_type, company_name)
        return {
            "status": "launched",
            "type": biz_type,
            "company": company_name,
        }

    @app.get("/status")
    def status():
        """System status check."""
        checks = {
            "openrouter_key": bool(os.environ.get("OPENROUTER_API_KEY")),
            "slack_token": bool(os.environ.get("SLACK_BOT_TOKEN")),
            "composio_key": bool(os.environ.get("COMPOSIO_API_KEY")),
            "paperclip_url": os.environ.get("PAPERCLIP_URL", "http://localhost:3000"),
        }
        return {"services": checks}

    # Also start Slack bridge in background if token available
    if os.environ.get("SLACK_BOT_TOKEN"):
        from governance.integrations.slack_bridge import start_slack_server
        start_slack_server(port=3001)

    print(f"\nGovernance API running on http://0.0.0.0:{port}")
    print(f"Docs: http://localhost:{port}/docs")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


def cmd_slack():
    """Start Slack bridge in foreground (for testing)."""
    import time
    from governance.integrations.slack_bridge import start_slack_server, notify_agent_activity
    server = start_slack_server(3001)
    print("Slack bridge running on :3001")
    print("Endpoints:")
    print("  POST /slack/commands  — slash commands")
    print("  POST /slack/actions   — interactive button actions")

    if os.environ.get("SLACK_BOT_TOKEN"):
        ok = notify_agent_activity("TestCo", "GovernanceSystem", "Slack bridge started", "success")
        print(f"Test message sent: {'ok' if ok else 'failed (check SLACK_BOT_TOKEN)'}")

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("\nSlack bridge stopped")
        server.shutdown()


def main():
    parser = argparse.ArgumentParser(description="Autonomous Agent Governance System")
    parser.add_argument("--council", action="store_true", help="Run 5-round expert council")
    parser.add_argument("--business", type=str, help="Launch business crew: exec_team, sales, marketing")
    parser.add_argument("--company", type=str, default=None, help="Company name for business crew")
    parser.add_argument("--serve", action="store_true", help="Start FastAPI governance server")
    parser.add_argument("--port", type=int, default=8080, help="Port for server")
    parser.add_argument("--slack", action="store_true", help="Start Slack bridge only")

    args = parser.parse_args()

    if not any([args.council, args.business, args.serve, args.slack]):
        parser.print_help()
        print("\nQuick start:")
        print("  python main.py --council              # Run the 5-round expert deliberation")
        print("  python main.py --business exec_team   # Launch executive AI team")
        print("  python main.py --serve                # Start full governance API")
        return

    if args.council:
        cmd_council()
    elif args.business:
        agency = cmd_business(args.business, args.company)
        # Interactive mode after launch
        print("\nAgency ready. Type a message to talk to the team (Ctrl+C to quit):")
        try:
            while True:
                message = input("\nYou: ").strip()
                if not message:
                    continue
                response = agency.get_completion(message)
                print(f"\nAgent: {response}")
        except KeyboardInterrupt:
            print("\nSession ended.")
    elif args.serve:
        cmd_serve(args.port)
    elif args.slack:
        cmd_slack()


if __name__ == "__main__":
    main()
