"""Sales Team — SDR, AE, CSM agents via Agency Swarm + OpenRouter."""
import os
from agency_swarm import Agent, Agency
from agency_swarm.tools import BaseTool
from pydantic import Field


class ProspectResearchTool(BaseTool):
    """Research a prospect company and find contact information."""
    company_name: str = Field(..., description="Company to research")
    target_role: str = Field(default="CEO", description="Target decision-maker role")

    def run(self) -> str:
        return (
            f"Prospect Research: {self.company_name}\n"
            f"Target Role: {self.target_role}\n"
            f"Industry: [To be enriched via Composio/Apollo]\n"
            f"Employee Count: [To be enriched]\n"
            f"LinkedIn: [To be enriched]\n"
            f"Status: Research queued — connect Composio Apollo for live data"
        )


class LogOutreachTool(BaseTool):
    """Log an outreach attempt to a prospect."""
    prospect: str = Field(..., description="Prospect name or company")
    channel: str = Field(..., description="Outreach channel: email, linkedin, phone")
    message_summary: str = Field(..., description="Brief summary of the message sent")
    touch_number: int = Field(..., description="Which touch in the sequence (1-5)")

    def run(self) -> str:
        if self.touch_number >= 5:
            return f"MAX TOUCHES REACHED for {self.prospect}. Marking inactive. Do not contact further."
        return (
            f"OUTREACH LOGGED:\n"
            f"Prospect: {self.prospect}\n"
            f"Channel: {self.channel}\n"
            f"Touch #{self.touch_number}\n"
            f"Message: {self.message_summary}\n"
            f"Next follow-up: {5 - self.touch_number} touches remaining"
        )


class UpdateCRMTool(BaseTool):
    """Update prospect status in CRM."""
    prospect: str = Field(..., description="Prospect name or company")
    status: str = Field(..., description="CRM status: prospecting, contacted, interested, demo_scheduled, closed_won, closed_lost, inactive")
    notes: str = Field(default="", description="Additional notes")

    def run(self) -> str:
        return (
            f"CRM UPDATED:\n"
            f"Prospect: {self.prospect}\n"
            f"Status: {self.status}\n"
            f"Notes: {self.notes}\n"
            f"[In production: Composio HubSpot/Salesforce sync]"
        )


class ScheduleMeetingTool(BaseTool):
    """Schedule a demo or meeting with a prospect."""
    prospect: str = Field(..., description="Prospect name")
    meeting_type: str = Field(..., description="Type: discovery, demo, proposal, close")
    preferred_times: str = Field(..., description="Proposed time slots")

    def run(self) -> str:
        return (
            f"MEETING REQUESTED:\n"
            f"Prospect: {self.prospect}\n"
            f"Type: {self.meeting_type}\n"
            f"Proposed times: {self.preferred_times}\n"
            f"[In production: Composio Google Calendar/Calendly integration]"
        )


def create_sales_crew(company_name: str = "SalesCo") -> Agency:
    """Create the sales team for autonomous outreach and closing."""

    sdr = Agent(
        name="SDR",
        description="Sales Development Rep — prospecting and outreach sequencing",
        instructions=f"""You are the SDR for {company_name}.

Your responsibilities:
- Research target companies and find decision-makers
- Execute multi-touch outreach sequences (max 5 touches per prospect)
- Qualify leads based on ICP criteria
- Hand off warm leads to AE when interest is confirmed

Outreach rules:
- Never send more than 5 touches to any single prospect
- Always personalize the first touch with company-specific insight
- Wait 3-5 days between touches
- If prospect says NOT interested: mark inactive, do not contact again

Qualification criteria (hand off to AE if ALL met):
- Company size: 10+ employees
- Budget signals present
- Decision-maker engaged
- Fit with our ICP""",
        tools=[ProspectResearchTool, LogOutreachTool, UpdateCRMTool],
        model=os.environ.get("SALES_MODEL", "moonshotai/kimi-2"),
        temperature=0.4,
    )

    ae = Agent(
        name="AE",
        description="Account Executive — demos, proposals, and closing",
        instructions=f"""You are the Account Executive for {company_name}.

Your responsibilities:
- Run discovery calls to understand prospect needs
- Deliver product demos tailored to their use case
- Create and send proposals
- Negotiate and close deals
- Hand closed customers to CSM for onboarding

Closing framework:
- Discovery first — understand pain before pitching
- Tailor demo to top 2 pains identified in discovery
- Follow up within 24 hours of every meeting
- Escalate deal size over $5000/month to CEO for approval""",
        tools=[UpdateCRMTool, ScheduleMeetingTool],
        model=os.environ.get("SALES_MODEL", "moonshotai/kimi-2"),
        temperature=0.4,
    )

    csm = Agent(
        name="CSM",
        description="Customer Success Manager — onboarding and retention",
        instructions=f"""You are the Customer Success Manager for {company_name}.

Your responsibilities:
- Onboard new customers within 48 hours of close
- Conduct 30/60/90 day check-ins
- Track customer health scores and usage
- Identify expansion opportunities and flag to AE
- Handle churn risk before it becomes churn

Success metrics:
- NPS target: >50
- Churn rate target: <5% monthly
- Time to first value: <7 days
- Expansion rate target: 20% of customers expand within 90 days""",
        tools=[UpdateCRMTool, ScheduleMeetingTool],
        model=os.environ.get("SALES_MODEL", "moonshotai/kimi-2"),
        temperature=0.4,
    )

    agency = Agency(
        agency_chart=[
            sdr,
            [sdr, ae],
            [ae, csm],
        ],
        shared_instructions=f"""Sales team of {company_name}:
- Always update CRM after every prospect interaction
- Handoffs must include full context: company, contact, pain points, history
- Budget requests require AE approval; over $200 requires CEO approval
- Flag any compliance or legal questions to human operator immediately""",
        temperature=0.4,
        max_prompt_tokens=25000,
    )

    return agency
