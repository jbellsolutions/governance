"""
Autonomous Agent Governance System
Entry point — launch council deliberation, business crews, or servers

Usage:
  python main.py --council              # Run 5-round expert deliberation
  python main.py --business exec_team  # Launch executive crew (interactive)
  python main.py --business sales      # Launch sales crew
  python main.py --business marketing  # Launch marketing crew
  python main.py --serve               # Start full governance API server (:8080)
  python main.py --specialists         # Start OpenSwarm specialist layer (:8080)
  python main.py --slack               # Start Slack bridge only (:3001)
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


def cmd_council():
    """Run the 5-round Expert Council deliberation."""
    from governance.council.expert_council_flow import run_council
    result = run_council()
    return result


def cmd_business(biz_type: str, company_name: str = None, tenant_id: str = None):
    """Launch a CrewAI-based governance crew."""
    name = company_name or f"{biz_type.replace('_', ' ').title()}Co"
    tid = tenant_id or name.lower().replace(" ", "-")

    if biz_type == "exec_team":
        from governance.crews.executive_crew import create_executive_crew
        gov_crew = create_executive_crew(name, tenant_id=tid)
        print(f"\nExecutive Team launched — {name} (tenant: {tid})")
        print("Agents: CEO, CMO, CTO, CFO")
        print("Running weekly review cycle...\n")
        result = gov_crew.kickoff()
        return gov_crew, result

    elif biz_type == "sales":
        from governance.crews.sales_crew import create_sales_crew
        gov_crew = create_sales_crew(name, tenant_id=tid)
        print(f"\nSales Team launched — {name} (tenant: {tid})")
        print("Agents: SDR, AE, CSM")
        print("Running pipeline review...\n")
        result = gov_crew.kickoff()
        return gov_crew, result

    elif biz_type == "marketing":
        from governance.crews.marketing_crew import create_marketing_crew
        gov_crew = create_marketing_crew(name, tenant_id=tid)
        print(f"\nMarketing Team launched — {name} (tenant: {tid})")
        print("Agents: Content, SEO, PaidAds")
        print("Running content & performance review...\n")
        result = gov_crew.kickoff()
        return gov_crew, result

    else:
        print(f"Unknown business type: {biz_type}")
        print("Options: exec_team, sales, marketing")
        sys.exit(1)


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

    @app.post("/council/run")
    def run_council():
        from governance.council.expert_council_flow import run_council as _run
        result = _run()
        return {"status": "complete", "rounds": 5, "verdict": result.get("verdict")}

    @app.post("/business/{biz_type}/kickoff")
    def kickoff_crew(biz_type: str, company_name: str = "AutoCo", tenant_id: str = None):
        gov_crew, result = cmd_business(biz_type, company_name, tenant_id)
        return {
            "status": "complete",
            "type": biz_type,
            "company": company_name,
            "result_preview": str(result)[:500] if result else None,
        }

    @app.post("/business/{biz_type}/resume")
    def resume_crew(biz_type: str, company_name: str, tenant_id: str = None):
        tid = tenant_id or company_name.lower().replace(" ", "-")
        crew_id_map = {
            "exec_team": "executive_team",
            "sales": "sales_team",
            "marketing": "marketing_team",
        }
        crew_id = crew_id_map.get(biz_type, biz_type)
        gov_crew, _ = cmd_business(biz_type, company_name, tid)
        result = gov_crew.resume()
        return {"status": "resumed", "crew_id": crew_id, "result_preview": str(result)[:500]}

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
    """Start the OpenSwarm specialist layer."""
    import uvicorn
    from governance.specialists.app import app
    print(f"\nOpenSwarm Specialist Layer: http://0.0.0.0:{port}")
    print(f"API docs:                    http://localhost:{port}/docs")
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
        import crewai
        print(f"CrewAI version: {crewai.__version__}")
    except Exception:
        print("CrewAI: NOT INSTALLED")

    try:
        import agency_swarm
        print(f"Agency Swarm: installed")
    except Exception:
        print("Agency Swarm: not installed")


def main():
    parser = argparse.ArgumentParser(description="Autonomous Agent Governance System")
    parser.add_argument("--council",      action="store_true",  help="Run 5-round expert council")
    parser.add_argument("--business",     type=str,             help="Crew type: exec_team, sales, marketing")
    parser.add_argument("--company",      type=str, default=None, help="Company name for the crew")
    parser.add_argument("--tenant",       type=str, default=None, help="Tenant ID (defaults to company name)")
    parser.add_argument("--serve",        action="store_true",  help="Start governance control plane API")
    parser.add_argument("--specialists",  action="store_true",  help="Start OpenSwarm specialist layer")
    parser.add_argument("--slack",        action="store_true",  help="Start Slack bridge only")
    parser.add_argument("--status",       action="store_true",  help="System health check")
    parser.add_argument("--port",         type=int, default=8000, help="Port for API server")

    args = parser.parse_args()

    if not any([args.council, args.business, args.serve, args.specialists, args.slack, args.status]):
        parser.print_help()
        print("\nQuick start:")
        print("  python main.py --status                        # health check")
        print("  python main.py --council                       # 5-round expert deliberation")
        print("  python main.py --business exec_team            # launch executive crew")
        print("  python main.py --specialists                   # start specialist layer (:8080)")
        print("  python main.py --serve                         # governance control plane (:8000)")
        return

    if args.status:
        cmd_status()
    elif args.council:
        cmd_council()
    elif args.business:
        gov_crew, result = cmd_business(args.business, args.company, args.tenant)
        if result:
            print("\n=== Crew Output ===")
            print(str(result)[:2000])
    elif args.serve:
        cmd_serve(args.port)
    elif args.specialists:
        cmd_specialists(args.port or 8080)
    elif args.slack:
        cmd_slack()


if __name__ == "__main__":
    main()
