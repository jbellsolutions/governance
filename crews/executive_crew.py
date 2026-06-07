"""
Executive Team Crew — CEO, CMO, CTO, CFO.
Hierarchical process: CEO delegates to other executives.
All spend >$500 escalates to human via Slack.
"""
import os
from crewai import Agent, Task, Crew, Process

from governance.crews.base_crew import GovernanceCrew, make_llm


def _exec_llm():
    return make_llm("EXEC_MODEL", "anthropic/claude-sonnet-4-6")


def create_executive_crew(company_name: str = "ExecCo", tenant_id: str = None) -> GovernanceCrew:
    tenant_id = tenant_id or company_name.lower().replace(" ", "-")
    llm = _exec_llm()

    ceo = Agent(
        role="Chief Executive Officer",
        goal=f"Drive {company_name} to product-market fit, sustainable revenue, and operational excellence",
        backstory=(
            f"You are the CEO of {company_name}, a fully autonomous AI-run business. "
            "You set quarterly strategy and OKRs, approve budget requests over $500, "
            "review company KPIs, and make final calls on product direction. "
            "You delegate execution to CMO, CTO, and CFO. "
            "Any spend over $1,000 triggers an immediate human escalation via Slack."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=True,
        max_iter=5,
    )

    cmo = Agent(
        role="Chief Marketing Officer",
        goal="Build brand awareness, generate qualified leads, and hit CAC targets",
        backstory=(
            f"You are the CMO of {company_name}. You define marketing strategy, "
            "target personas, and campaign plans (handed to Marketing Crew for execution). "
            "You track CAC, conversion rates, and brand metrics. "
            "Campaigns over $200 need CEO approval. You report weekly to the CEO."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    cto = Agent(
        role="Chief Technology Officer",
        goal="Build reliable, scalable technical architecture with minimal operational cost",
        backstory=(
            f"You are the CTO of {company_name}. You define the technical stack, "
            "evaluate new tools, ensure system reliability and security, and manage "
            "infrastructure costs. Security concerns escalate immediately to CEO. "
            "All infrastructure spend is reported to CFO."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    cfo = Agent(
        role="Chief Financial Officer",
        goal="Maintain financial discipline: track all spend, prevent budget overruns, project runway",
        backstory=(
            f"You are the CFO of {company_name}. You monitor all agent budgets, "
            "alert CEO when any agent hits 80% utilization, auto-pause at 100%, "
            "approve/deny budget requests, and produce weekly P&L for CEO review. "
            "Your burn rate projections cover 30/60/90 days at all times."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    # Tasks define what the crew does each run
    strategy_review = Task(
        description=(
            f"Review current state of {company_name}. Check KPIs, budget utilization, "
            "and top 3 priorities. Produce a one-page strategic brief with: "
            "current status, top priorities this week, and any escalations needed."
        ),
        expected_output=(
            "Strategic brief with: status summary, top 3 priorities, budget status, "
            "any human escalations flagged with reason and urgency."
        ),
        agent=ceo,
    )

    marketing_plan = Task(
        description=(
            f"Based on CEO's strategic brief, define this week's marketing priorities for {company_name}. "
            "Specify: target segment, channel mix, budget requested (<$200 auto-approved), "
            "and expected outcome metric."
        ),
        expected_output=(
            "Marketing plan with: target segment, channels, budget breakdown, "
            "success metrics, and timeline."
        ),
        agent=cmo,
    )

    tech_review = Task(
        description=(
            f"Review {company_name}'s technical infrastructure. Identify: any reliability risks, "
            "cost optimization opportunities, and upcoming technical decisions. "
            "Report infrastructure cost forecast to CFO."
        ),
        expected_output=(
            "Tech review with: reliability risk level (green/yellow/red), "
            "cost forecast, top 3 technical decisions pending."
        ),
        agent=cto,
    )

    financial_review = Task(
        description=(
            f"Produce financial summary for {company_name}: current burn rate, "
            "budget utilization per agent, runway projection. "
            "Flag any agents above 80% budget utilization for CEO review."
        ),
        expected_output=(
            "Financial summary with: burn rate, runway (days), per-agent utilization, "
            "budget alerts list."
        ),
        agent=cfo,
    )

    crew = Crew(
        agents=[ceo, cmo, cto, cfo],
        tasks=[strategy_review, marketing_plan, tech_review, financial_review],
        process=Process.sequential,  # CEO brief → then parallel functional reviews
        verbose=True,
        memory=False,  # using our own state_manager
        planning=False,
    )

    return GovernanceCrew(crew=crew, tenant_id=tenant_id, crew_id="executive_team", est_cost_per_run=0.25)
