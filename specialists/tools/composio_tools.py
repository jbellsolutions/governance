"""
Composio tool wrappers for specialist agents.
Each specialist type gets the right app set from Composio's 10,000+ integrations.
Rate-limited: 10 concurrent Composio actions per tenant (configurable).
"""
import os
import time
import threading
from typing import Optional

COMPOSIO_API_KEY = os.environ.get("COMPOSIO_API_KEY", "")

# Per-tenant concurrency limiter
_semaphores: dict = {}
_sema_lock = threading.Lock()
MAX_CONCURRENT = int(os.environ.get("COMPOSIO_MAX_CONCURRENT", "10"))


def _get_semaphore(tenant_id: str) -> threading.Semaphore:
    with _sema_lock:
        if tenant_id not in _semaphores:
            _semaphores[tenant_id] = threading.Semaphore(MAX_CONCURRENT)
        return _semaphores[tenant_id]


SPECIALIST_APPS = {
    "slack":    ["SLACK"],
    "email":    ["GMAIL"],
    "calendar": ["GOOGLECALENDAR"],
    "crm":      ["HUBSPOT"],
    "research": [],  # uses built-in web search, no Composio needed
    "code":     ["GITHUB"],
}

SPECIALIST_ACTIONS = {
    "slack":    ["SLACK_SENDS_A_MESSAGE_TO_A_SLACK_CHANNEL", "SLACK_LIST_CHANNELS"],
    "email":    ["GMAIL_SEND_EMAIL", "GMAIL_FETCH_EMAILS"],
    "calendar": ["GOOGLECALENDAR_CREATE_EVENT", "GOOGLECALENDAR_LIST_EVENTS"],
    "crm":      ["HUBSPOT_CREATE_CONTACT", "HUBSPOT_LIST_CONTACTS"],
    "code":     ["GITHUB_CREATE_AN_ISSUE", "GITHUB_LIST_REPOS"],
}


def get_specialist_tools(specialist_type: str, tenant_id: str = "default") -> list:
    """
    Get Composio tools for a specialist type.
    Returns empty list (no tools) if Composio not configured.
    Falls back to empty list gracefully — agents can still reason without tools.
    """
    if not COMPOSIO_API_KEY:
        print(f"[Composio] COMPOSIO_API_KEY not set — {specialist_type} specialist running without tools")
        return []

    if specialist_type == "research":
        return _get_research_tools()

    try:
        from composio_openai import ComposioToolSet, App, Action

        sema = _get_semaphore(tenant_id)

        class RateLimitedToolSet(ComposioToolSet):
            def execute_action(self, *args, **kwargs):
                acquired = sema.acquire(timeout=30)
                if not acquired:
                    raise RuntimeError(f"Composio rate limit: {MAX_CONCURRENT} concurrent actions exceeded")
                try:
                    return super().execute_action(*args, **kwargs)
                finally:
                    sema.release()

        toolset = RateLimitedToolSet(api_key=COMPOSIO_API_KEY)

        # Prefer specific actions over full app access for smaller tool surface
        actions_list = SPECIALIST_ACTIONS.get(specialist_type, [])
        if actions_list:
            valid_actions = [getattr(Action, a) for a in actions_list if hasattr(Action, a)]
            if valid_actions:
                return toolset.get_tools(actions=valid_actions)

        apps_list = SPECIALIST_APPS.get(specialist_type, [])
        if apps_list:
            valid_apps = [getattr(App, a) for a in apps_list if hasattr(App, a)]
            if valid_apps:
                return toolset.get_tools(apps=valid_apps)

        return []

    except ImportError:
        print("[Composio] composio-openai not installed. Run: pip install composio-openai")
        return []
    except Exception as e:
        print(f"[Composio] Failed to load tools for {specialist_type}: {e}")
        return []


def _get_research_tools() -> list:
    """Research tools — web search without Composio dependency."""
    try:
        from crewai_tools import SerperDevTool, WebsiteSearchTool
        tools = []
        if os.environ.get("SERPER_API_KEY"):
            tools.append(SerperDevTool())
        tools.append(WebsiteSearchTool())
        return tools
    except ImportError:
        return []


def connect_app(app_name: str) -> None:
    """Initiate Composio OAuth for an app. Run interactively."""
    if not COMPOSIO_API_KEY:
        print("Set COMPOSIO_API_KEY first")
        return
    try:
        from composio_openai import ComposioToolSet, App
        toolset = ComposioToolSet(api_key=COMPOSIO_API_KEY)
        app_enum = getattr(App, app_name.upper(), None)
        if not app_enum:
            print(f"Unknown app: {app_name}. Check: composio apps list")
            return
        print(f"Run: composio add {app_name.lower()}")
    except ImportError:
        print("Install: pip install composio-openai")


if __name__ == "__main__":
    print(f"Composio configured: {'yes' if COMPOSIO_API_KEY else 'NO'}")
    print("Specialist app mappings:")
    for stype, apps in SPECIALIST_APPS.items():
        print(f"  {stype:12s}: {apps}")
