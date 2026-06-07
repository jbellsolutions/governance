"""Executive Team — CEO, CMO, CTO, CFO agents via Agency Swarm + OpenRouter."""
import os
from agency_swarm import Agent, Agency
from agency_swarm.tools import BaseTool
from pydantic import Field


class ReviewKPIsTool(BaseTool):
    """Review current KPIs and company metrics."""
    company_name: str = Field(..., description="Name of the company to review")

    def run(self) -> str:
        # In production: query Paperclip API for actual metrics
        return (
            f"KPI Report for {self.company_name}:\n"
            f"- Revenue MTD: $0 (early stage)\n"
            f"- Agent tasks completed: 0\n"
            f"- Budget utilization: 0%\n"
            f"- Active projects: 0\n"
            f"Status: Initialized, awaiting first cycle"
        )


class ApproveBudgetTool(BaseTool):
    """Approve or reject a budget request."""
    requester: str = Field(..., description="Agent or team requesting budget")
    amount_usd: float = Field(..., description="Amount requested in USD")
    purpose: str = Field(..., description="What the budget will be used for")

    def run(self) -> str:
        if self.amount_usd > 1000:
            return f"ESCALATED: ${self.amount_usd} request from {self.requester} requires human approval. Reason: exceeds $1000 auto-approve threshold."
        return f"APPROVED: ${self.amount_usd} for {self.requester} — Purpose: {self.purpose}"


class SetStrategyTool(BaseTool):
    """Document a strategic decision or company directive."""
    decision: str = Field(..., description="The strategic decision being made")
    rationale: str = Field(..., description="Why this decision was made")
    owner: str = Field(..., description="Which agent/team owns execution")

    def run(self) -> str:
        return (
            f"STRATEGY RECORDED:\n"
            f"Decision: {self.decision}\n"
            f"Rationale: {self.rationale}\n"
            f"Owner: {self.owner}\n"
            f"Status: Active"
        )


def create_executive_crew(company_name: str = "ExecCo") -> Agency:
    """Create the executive team crew for autonomous business operations."""

    ceo = Agent(
        name="CEO",
        description="Chief Executive Officer — sets strategy, approves major decisions, reviews KPIs",
        instructions=f"""You are the CEO of {company_name}, an autonomous AI business.

Your responsibilities:
- Set quarterly strategy and OKRs
- Approve budget requests over $500
- Review company KPIs weekly
- Coordinate CMO, CTO, and CFO
- Make final calls on product direction

Decision framework:
- Under $500: auto-approve if aligned with strategy
- $500-$1000: review rationale, approve if justified
- Over $1000: escalate to human operator via Slack

Always communicate decisions with clear rationale.
When reviewing KPIs, provide specific recommendations for improvement.""",
        tools=[ReviewKPIsTool, ApproveBudgetTool, SetStrategyTool],
        model=os.environ.get("EXEC_MODEL", "anthropic/claude-sonnet-4-6"),
        temperature=0.3,
    )

    cmo = Agent(
        name="CMO",
        description="Chief Marketing Officer — owns marketing strategy, campaigns, and brand",
        instructions=f"""You are the CMO of {company_name}.

Your responsibilities:
- Define marketing strategy and target personas
- Plan and approve campaigns (handed to Marketing Crew for execution)
- Track CAC, conversion rates, and brand metrics
- Report marketing performance to CEO weekly

When proposing campaigns:
- State target audience, channel, budget, and expected CAC
- Always get CEO approval for campaigns over $200
- Measure results and report back""",
        tools=[ApproveBudgetTool],
        model=os.environ.get("EXEC_MODEL", "anthropic/claude-sonnet-4-6"),
        temperature=0.4,
    )

    cto = Agent(
        name="CTO",
        description="Chief Technology Officer — owns technical architecture and engineering",
        instructions=f"""You are the CTO of {company_name}.

Your responsibilities:
- Define technical architecture and stack decisions
- Evaluate and approve new tools/integrations
- Ensure system reliability and security
- Manage technical debt and infrastructure costs

When making technical decisions:
- Always consider cost implications (report to CFO)
- Document architecture decisions with rationale
- Escalate security concerns immediately to CEO""",
        tools=[ApproveBudgetTool, SetStrategyTool],
        model=os.environ.get("EXEC_MODEL", "anthropic/claude-sonnet-4-6"),
        temperature=0.3,
    )

    cfo = Agent(
        name="CFO",
        description="Chief Financial Officer — owns budgets, cost tracking, and financial controls",
        instructions=f"""You are the CFO of {company_name}.

Your responsibilities:
- Monitor all agent budgets and spending
- Alert CEO when any budget hits 80% utilization
- Approve or deny budget requests from other executives
- Produce weekly P&L summary for CEO review

Financial controls:
- Auto-pause any agent that hits 100% budget utilization
- Flag unusual spending patterns to CEO immediately
- Maintain burn rate projections for next 30/60/90 days""",
        tools=[ReviewKPIsTool, ApproveBudgetTool],
        model=os.environ.get("EXEC_MODEL", "anthropic/claude-sonnet-4-6"),
        temperature=0.2,
    )

    agency = Agency(
        agency_chart=[
            ceo,
            [ceo, cmo],
            [ceo, cto],
            [ceo, cfo],
        ],
        shared_instructions=f"""All executives of {company_name}:
- Communicate decisions with clear rationale
- Use structured format: DECISION | RATIONALE | OWNER | TIMELINE
- Escalate anything requiring >$1000 spend to human via Slack
- Log all major decisions for audit trail""",
        temperature=0.3,
        max_prompt_tokens=25000,
    )

    return agency
