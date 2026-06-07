"""
Marketing Team Crew — Content, SEO, PaidAds.
Sequential: Content creates → SEO optimizes → PaidAds amplifies.
"""
import os
from crewai import Agent, Task, Crew, Process

from governance.crews.base_crew import GovernanceCrew, make_llm


def _marketing_llm():
    return make_llm("MARKETING_MODEL", "moonshotai/kimi-2")


def create_marketing_crew(company_name: str = "MarketingCo", tenant_id: str = None) -> GovernanceCrew:
    tenant_id = tenant_id or company_name.lower().replace(" ", "-")
    llm = _marketing_llm()

    content_agent = Agent(
        role="Content Strategist and Writer",
        goal="Produce high-quality content that drives organic traffic and converts visitors to leads",
        backstory=(
            f"You are the content lead at {company_name}. You create blog posts, "
            "social media content, email newsletters, and case studies. "
            "You write for the ICP, match brand voice, and optimize every piece "
            "for both human readers and search engines."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    seo_agent = Agent(
        role="SEO Specialist",
        goal="Grow organic search traffic 20% MoM through technical SEO and keyword strategy",
        backstory=(
            f"You are the SEO lead at {company_name}. You do keyword research, "
            "on-page optimization, technical SEO audits, and backlink analysis. "
            "You prioritize high-intent, low-competition keywords and ensure every "
            "piece of content is properly structured for search."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    paid_ads_agent = Agent(
        role="Paid Acquisition Specialist",
        goal="Generate qualified leads at or below target CAC through paid channels",
        backstory=(
            f"You are the paid ads lead at {company_name}. You manage Google Ads, "
            "LinkedIn, and Meta campaigns. You write ad copy, define audiences, "
            "optimize bids, and track ROAS. You pause campaigns that exceed CAC targets "
            "and reallocate budget to top performers."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    content_task = Task(
        description=(
            "Plan this week's content calendar. Produce: "
            "1 long-form blog post outline (topic + H2 structure + target keyword), "
            "3 LinkedIn post drafts, "
            "1 email newsletter subject line + preview text. "
            "All content must tie to current company priorities."
        ),
        expected_output=(
            "Content calendar with: blog outline (topic, H2s, target keyword), "
            "3 LinkedIn drafts, email subject + preview. "
            "All content ready for review and publishing."
        ),
        agent=content_agent,
    )

    seo_task = Task(
        description=(
            "Run this week's SEO review. Identify: "
            "top 5 keyword opportunities (volume, difficulty, intent), "
            "any technical issues to fix (crawl errors, slow pages, missing metas), "
            "and optimization recommendations for the blog post from Content team."
        ),
        expected_output=(
            "SEO brief with: 5 keyword opportunities with volume/difficulty, "
            "technical issues list with priority, "
            "specific optimization checklist for this week's blog post."
        ),
        agent=seo_agent,
    )

    paid_task = Task(
        description=(
            "Review paid channel performance. For each active campaign: "
            "report spend, leads generated, CPL, and ROAS. "
            "Recommend budget shifts between channels based on performance. "
            "Flag any campaigns exceeding target CAC for immediate review."
        ),
        expected_output=(
            "Paid channel report with: per-campaign metrics (spend/leads/CPL/ROAS), "
            "budget shift recommendations, "
            "campaigns flagged for pause or scaling."
        ),
        agent=paid_ads_agent,
    )

    crew = Crew(
        agents=[content_agent, seo_agent, paid_ads_agent],
        tasks=[content_task, seo_task, paid_task],
        process=Process.sequential,
        verbose=True,
        memory=False,
    )

    return GovernanceCrew(crew=crew, tenant_id=tenant_id, crew_id="marketing_team", est_cost_per_run=0.15)
