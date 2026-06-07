"""
Sales Team Crew — SDR, AE, CSM.
Sequential: SDR qualifies → AE demos/closes → CSM onboards.
"""
import os
from crewai import Agent, Task, Crew, Process

from governance.crews.base_crew import GovernanceCrew, make_llm


def _sales_llm():
    return make_llm("SALES_MODEL", "moonshotai/kimi-2")


def create_sales_crew(company_name: str = "SalesCo", tenant_id: str = None) -> GovernanceCrew:
    tenant_id = tenant_id or company_name.lower().replace(" ", "-")
    llm = _sales_llm()

    sdr = Agent(
        role="Sales Development Representative",
        goal="Generate 10+ qualified sales opportunities per week through targeted outreach",
        backstory=(
            f"You are the SDR at {company_name}. You prospect, research leads, "
            "write personalized outreach sequences, and qualify inbound leads. "
            "A qualified lead has: budget authority, real need, and timeline within 90 days. "
            "You hand qualified leads to the AE with full context."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    ae = Agent(
        role="Account Executive",
        goal="Convert qualified leads into paying customers with average deal size >$5K",
        backstory=(
            f"You are the AE at {company_name}. You run discovery calls, product demos, "
            "and close deals. You handle objections, negotiate pricing, and manage the "
            "sales cycle from first meeting to signed contract. "
            "You update the CRM after every interaction."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    csm = Agent(
        role="Customer Success Manager",
        goal="Drive 95%+ retention and expand ARR through proactive customer success",
        backstory=(
            f"You are the CSM at {company_name}. You onboard new customers, "
            "build success plans, track health scores, and prevent churn. "
            "You identify expansion opportunities and work with AE on upsells. "
            "You escalate at-risk accounts to the AE immediately."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    prospect_task = Task(
        description=(
            "Generate a list of 10 ideal customer prospects for this week. "
            "For each prospect include: company name, contact name/title, "
            "why they fit our ICP, personalized outreach angle, and next action."
        ),
        expected_output=(
            "Prospecting list with 10 entries, each with: company, contact, "
            "ICP fit score (1-10), outreach angle, next action."
        ),
        agent=sdr,
    )

    pipeline_task = Task(
        description=(
            "Review this week's pipeline. For each deal: assess stage, "
            "identify next step, flag any stalled deals (>14 days no activity), "
            "and recommend specific actions to advance or close."
        ),
        expected_output=(
            "Pipeline review with: deal list by stage, stalled deals flagged, "
            "recommended actions per deal, projected close value this month."
        ),
        agent=ae,
    )

    health_task = Task(
        description=(
            "Review customer health scores. Flag any accounts with declining usage, "
            "missed QBRs, or open support issues. For at-risk accounts, "
            "create a specific save plan with timeline and owner."
        ),
        expected_output=(
            "Health report with: accounts by health tier (green/yellow/red), "
            "at-risk accounts with save plans, expansion opportunities identified."
        ),
        agent=csm,
    )

    crew = Crew(
        agents=[sdr, ae, csm],
        tasks=[prospect_task, pipeline_task, health_task],
        process=Process.sequential,
        verbose=True,
        memory=False,
    )

    return GovernanceCrew(crew=crew, tenant_id=tenant_id, crew_id="sales_team", est_cost_per_run=0.15)
