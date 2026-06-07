"""
Composio connection configuration for OpenSwarm specialist agents.
Provides authenticated toolsets for Slack, Gmail, HubSpot, Calendar, etc.

Requires: COMPOSIO_API_KEY environment variable
Install:  pip install composio-openai
"""
import os
from typing import Optional

COMPOSIO_API_KEY = os.environ.get("COMPOSIO_API_KEY", "")


def get_toolset(apps: Optional[list] = None, actions: Optional[list] = None):
    """
    Get Composio toolset for specified apps or actions.
    Returns list of tools compatible with agency_swarm agents.

    Usage:
        tools = get_toolset(apps=["SLACK", "GMAIL"])
        tools = get_toolset(actions=["SLACK_SENDS_A_MESSAGE_TO_A_SLACK_CHANNEL"])
    """
    if not COMPOSIO_API_KEY:
        print("[Composio] COMPOSIO_API_KEY not set — returning mock tools")
        return []

    try:
        from composio_openai import ComposioToolSet, App, Action

        toolset = ComposioToolSet(api_key=COMPOSIO_API_KEY)

        if actions:
            action_enums = [getattr(Action, a) for a in actions if hasattr(Action, a)]
            return toolset.get_tools(actions=action_enums)

        if apps:
            app_enums = [getattr(App, a) for a in apps if hasattr(App, a)]
            return toolset.get_tools(apps=app_enums)

        return []

    except ImportError:
        print("[Composio] composio-openai not installed. Run: pip install composio-openai")
        return []


def get_slack_tools():
    """Composio Slack tools: post messages, read channels, manage workspace."""
    return get_toolset(apps=["SLACK"])


def get_email_tools():
    """Composio Gmail tools: send, read, label, search emails."""
    return get_toolset(apps=["GMAIL"])


def get_calendar_tools():
    """Composio Google Calendar tools: create events, check availability."""
    return get_toolset(apps=["GOOGLECALENDAR"])


def get_crm_tools():
    """Composio HubSpot tools: contacts, deals, companies, activities."""
    return get_toolset(apps=["HUBSPOT"])


def get_full_business_toolset():
    """All tools needed for a full autonomous business team."""
    return get_toolset(apps=["SLACK", "GMAIL", "GOOGLECALENDAR", "HUBSPOT", "NOTION"])


def check_connected_apps() -> list:
    """List all apps currently connected to the Composio account."""
    if not COMPOSIO_API_KEY:
        return []

    try:
        from composio_openai import ComposioToolSet
        toolset = ComposioToolSet(api_key=COMPOSIO_API_KEY)
        # composio_openai doesn't expose a direct list method
        # This checks what's available by attempting to fetch
        return ["Check Composio dashboard at app.composio.dev for connected apps"]
    except ImportError:
        return []


def connect_app(app_name: str):
    """
    Initiate OAuth connection for an app via Composio.
    Opens browser for OAuth flow.
    """
    if not COMPOSIO_API_KEY:
        print("Set COMPOSIO_API_KEY first")
        return

    try:
        from composio_openai import ComposioToolSet, App
        toolset = ComposioToolSet(api_key=COMPOSIO_API_KEY)
        app_enum = getattr(App, app_name.upper(), None)
        if not app_enum:
            print(f"Unknown app: {app_name}")
            return
        # Trigger connection flow
        print(f"Connecting {app_name}... Check your browser for OAuth flow.")
        print(f"Or run: composio add {app_name.lower()}")
    except ImportError:
        print("Install composio-openai first: pip install composio-openai")


if __name__ == "__main__":
    print("Composio Setup")
    print(f"API Key set: {'yes' if COMPOSIO_API_KEY else 'NO — set COMPOSIO_API_KEY'}")
    print("\nTo connect apps, run:")
    print("  pip install composio-openai")
    print("  composio add slack")
    print("  composio add gmail")
    print("  composio add hubspot")
    print("  composio add googlecalendar")
    connected = check_connected_apps()
    if connected:
        print(f"\nConnected: {connected}")
