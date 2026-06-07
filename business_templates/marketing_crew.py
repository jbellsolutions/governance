"""Marketing Team — Content, SEO, Paid Ads agents via Agency Swarm + OpenRouter."""
import os
from agency_swarm import Agent, Agency
from agency_swarm.tools import BaseTool
from pydantic import Field


class WriteContentTool(BaseTool):
    """Write a piece of content for a specified channel and audience."""
    content_type: str = Field(..., description="Type: blog_post, social_post, email, ad_copy")
    topic: str = Field(..., description="Content topic or angle")
    target_audience: str = Field(..., description="Who this is written for")
    word_count: int = Field(default=500, description="Target word count")

    def run(self) -> str:
        return (
            f"CONTENT BRIEF CREATED:\n"
            f"Type: {self.content_type}\n"
            f"Topic: {self.topic}\n"
            f"Audience: {self.target_audience}\n"
            f"Word count: {self.word_count}\n"
            f"[Content agent will draft using configured LLM]\n"
            f"Status: Draft queued"
        )


class KeywordResearchTool(BaseTool):
    """Research keywords for SEO content planning."""
    seed_topic: str = Field(..., description="Main topic to research keywords for")
    intent: str = Field(default="informational", description="Search intent: informational, commercial, transactional")

    def run(self) -> str:
        return (
            f"KEYWORD RESEARCH: {self.seed_topic}\n"
            f"Intent: {self.intent}\n"
            f"[In production: Ahrefs/SEMrush via Composio]\n"
            f"Sample opportunities:\n"
            f"  - '{self.seed_topic} guide' — high volume, low competition\n"
            f"  - 'best {self.seed_topic} tools' — commercial intent\n"
            f"  - '{self.seed_topic} vs alternatives' — comparison\n"
            f"Status: Connect Composio SEO tool for live data"
        )


class SchedulePostTool(BaseTool):
    """Schedule a social media or content post."""
    platform: str = Field(..., description="Platform: twitter, linkedin, instagram, blog")
    content_summary: str = Field(..., description="Brief description of what's being posted")
    scheduled_time: str = Field(..., description="When to post (ISO format or relative: 'tomorrow 9am')")

    def run(self) -> str:
        return (
            f"POST SCHEDULED:\n"
            f"Platform: {self.platform}\n"
            f"Content: {self.content_summary}\n"
            f"Time: {self.scheduled_time}\n"
            f"[In production: Buffer/Hootsuite via Composio]"
        )


class TrackCampaignTool(BaseTool):
    """Track campaign performance metrics."""
    campaign_name: str = Field(..., description="Name of the campaign to track")

    def run(self) -> str:
        return (
            f"CAMPAIGN METRICS: {self.campaign_name}\n"
            f"Impressions: [Live data via Composio]\n"
            f"Clicks: [Live data]\n"
            f"CTR: [Live data]\n"
            f"Conversions: [Live data]\n"
            f"CPA: [Live data]\n"
            f"Status: Connect Composio Google Ads / Meta Ads for live metrics"
        )


def create_marketing_crew(company_name: str = "MarketingCo") -> Agency:
    """Create the marketing team for autonomous content and campaign execution."""

    content_agent = Agent(
        name="ContentAgent",
        description="Content creator — blog posts, social media, email copy",
        instructions=f"""You are the Content Agent for {company_name}.

Your responsibilities:
- Write blog posts, social media content, and email sequences
- Maintain consistent brand voice across all channels
- Optimize content for SEO based on keyword research from SEO Agent
- Schedule content for publishing via Buffer/Hootsuite

Content standards:
- Every piece must have a clear CTA
- Blog posts: minimum 1000 words, SEO-optimized
- Social posts: platform-specific length and tone
- Email: subject line A/B variants always provided

Production schedule: 3 blog posts/week, 15 social posts/week, 2 email campaigns/month""",
        tools=[WriteContentTool, SchedulePostTool],
        model=os.environ.get("MARKETING_MODEL", "moonshotai/kimi-2"),
        temperature=0.7,
    )

    seo_agent = Agent(
        name="SEOAgent",
        description="SEO specialist — keyword research and on-page optimization",
        instructions=f"""You are the SEO Agent for {company_name}.

Your responsibilities:
- Research and prioritize keywords by volume and competition
- Audit existing content for SEO improvements
- Provide keyword briefs to Content Agent
- Track rankings and organic traffic growth
- Identify link-building opportunities

SEO framework:
- Focus on bottom-of-funnel keywords first (commercial intent)
- Target 10 primary keywords per month
- Monthly ranking reports to CMO
- Alert CMO if ranking drops >10 positions on any top keyword""",
        tools=[KeywordResearchTool, WriteContentTool],
        model=os.environ.get("MARKETING_MODEL", "moonshotai/kimi-2"),
        temperature=0.3,
    )

    paid_ads_agent = Agent(
        name="PaidAdsAgent",
        description="Paid ads manager — Google Ads, Meta Ads campaign management",
        instructions=f"""You are the Paid Ads Manager for {company_name}.

Your responsibilities:
- Create and optimize Google Ads and Meta Ads campaigns
- Monitor CPA and ROAS daily
- Pause underperforming ad sets automatically (CPA > 2x target)
- Scale budgets on winning campaigns (ROAS > 3x)
- Report weekly to CMO on campaign performance

Budget controls:
- Daily spend cap per campaign: set by CMO
- Auto-pause trigger: CPA > 2x target CPA for 3+ days
- Auto-scale trigger: ROAS > 3x for 5+ days
- Never exceed monthly budget without CMO approval""",
        tools=[TrackCampaignTool, WriteContentTool],
        model=os.environ.get("MARKETING_MODEL", "moonshotai/kimi-2"),
        temperature=0.3,
    )

    agency = Agency(
        agency_chart=[
            content_agent,
            [seo_agent, content_agent],
            [content_agent, paid_ads_agent],
        ],
        shared_instructions=f"""Marketing team of {company_name}:
- All content must pass brand voice check before publishing
- Budget requests over $100 require CMO approval
- Track every campaign with UTM parameters
- Weekly report to CMO every Monday at 9am""",
        temperature=0.5,
        max_prompt_tokens=25000,
    )

    return agency
