"""
Business Registry — manages multiple autonomous businesses in one governance panel.

Each business has:
  - A unique ID and human name
  - A tenant_id (namespaces all state, memory, and logs in SQLite)
  - A list of active teams (exec_team, sales, marketing, or custom)

All data persists in the governance SQLite DB via state_manager.
Thread-safe: registry mutations acquire _lock before read-modify-write.
"""
import time
import uuid
import threading
from typing import Optional

from governance.core import state_manager

_lock = threading.Lock()

# Stored as a single JSON blob in entity_memory
_REGISTRY_TENANT = "system"
_REGISTRY_ENTITY = "business_registry"
_REGISTRY_KEY = "businesses"

VALID_TEAM_TYPES = ["exec_team", "sales", "marketing"]
TEAM_LABELS = {
    "exec_team": "Executive Team",
    "sales": "Sales Team",
    "marketing": "Marketing Team",
}


# ── Internal persistence helpers ──────────────────────────────────────────────

def _load() -> dict:
    data = state_manager.get_entity_key(_REGISTRY_TENANT, _REGISTRY_ENTITY, _REGISTRY_KEY)
    return data if isinstance(data, dict) else {}


def _save(businesses: dict) -> None:
    state_manager.save_entity(_REGISTRY_TENANT, _REGISTRY_ENTITY, _REGISTRY_KEY, businesses)


# ── Public API ────────────────────────────────────────────────────────────────

def create_business(
    name: str,
    description: str = "",
    teams: Optional[list] = None,
) -> dict:
    """
    Create a new business.
    Returns the business dict with id, name, tenant_id, teams, created_at.
    """
    with _lock:
        businesses = _load()

        business_id = str(uuid.uuid4())[:8]

        # Derive a slug tenant_id from the name; ensure uniqueness
        base_slug = name.lower().replace(" ", "-")[:28]
        base_slug = "".join(c for c in base_slug if c.isalnum() or c == "-")
        tenant_id = base_slug or "business"
        existing = {b["tenant_id"] for b in businesses.values()}
        suffix = 1
        while tenant_id in existing:
            tenant_id = f"{base_slug}-{suffix}"
            suffix += 1

        initial_teams = teams or ["exec_team"]
        invalid = [t for t in initial_teams if t not in VALID_TEAM_TYPES]
        if invalid:
            raise ValueError(f"Invalid team types: {invalid}. Valid: {VALID_TEAM_TYPES}")

        business = {
            "id": business_id,
            "name": name,
            "description": description,
            "tenant_id": tenant_id,
            "teams": initial_teams,
            "created_at": time.time(),
        }
        businesses[business_id] = business
        _save(businesses)
        return business


def list_businesses() -> list:
    """Return all businesses sorted by creation time (newest first)."""
    with _lock:
        businesses = _load()
    return sorted(businesses.values(), key=lambda b: b.get("created_at", 0), reverse=True)


def get_business(business_id: str) -> Optional[dict]:
    with _lock:
        return _load().get(business_id)


def delete_business(business_id: str) -> bool:
    with _lock:
        businesses = _load()
        if business_id not in businesses:
            return False
        del businesses[business_id]
        _save(businesses)
    return True


def add_team(business_id: str, team_type: str) -> dict:
    """
    Add a team to an existing business.
    Raises ValueError for unknown team types, KeyError if business not found.
    """
    if team_type not in VALID_TEAM_TYPES:
        raise ValueError(f"Unknown team: '{team_type}'. Valid: {VALID_TEAM_TYPES}")
    with _lock:
        businesses = _load()
        if business_id not in businesses:
            raise KeyError(f"Business {business_id!r} not found")
        biz = businesses[business_id]
        if team_type not in biz["teams"]:
            biz["teams"].append(team_type)
        _save(businesses)
        return biz


def remove_team(business_id: str, team_type: str) -> dict:
    """Remove a team from a business. Silently no-ops if team not present."""
    with _lock:
        businesses = _load()
        if business_id not in businesses:
            raise KeyError(f"Business {business_id!r} not found")
        biz = businesses[business_id]
        biz["teams"] = [t for t in biz["teams"] if t != team_type]
        _save(businesses)
        return biz
