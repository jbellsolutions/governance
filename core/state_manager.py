"""
Tenant-Isolated State Manager.
SQLite with WAL mode — zero cold starts, full state always persisted.
All tables namespaced by tenant_id to isolate multi-tenant deployments.
"""
import os
import json
import time
import sqlite3
import threading
from typing import Any, Optional

_DEFAULT_DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "governance.db")
DB_PATH = os.environ.get("STATE_DB_PATH", _DEFAULT_DB)
_lock = threading.Lock()
_initialized = False


def _get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def _init_db():
    global _initialized
    if _initialized:
        return
    with _lock, _get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                tenant_id  TEXT NOT NULL,
                crew_id    TEXT NOT NULL,
                state_json TEXT NOT NULL,
                updated_at REAL NOT NULL,
                PRIMARY KEY (tenant_id, crew_id)
            );
            CREATE TABLE IF NOT EXISTS entity_memory (
                tenant_id  TEXT NOT NULL,
                entity_id  TEXT NOT NULL,
                key        TEXT NOT NULL,
                value_json TEXT NOT NULL,
                updated_at REAL NOT NULL,
                PRIMARY KEY (tenant_id, entity_id, key)
            );
            CREATE TABLE IF NOT EXISTS workflow_log (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id  TEXT NOT NULL,
                crew_id    TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload    TEXT,
                created_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_workflow_log_tenant
                ON workflow_log(tenant_id, crew_id, created_at);
        """)
        conn.commit()
    _initialized = True


# ── Checkpoint API ───────────────────────────────────────────────────────────

def save_checkpoint(tenant_id: str, crew_id: str, state: Any) -> None:
    _init_db()
    with _lock, _get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO checkpoints VALUES (?, ?, ?, ?)",
            (tenant_id, crew_id, json.dumps(state, default=str), time.time())
        )
        conn.commit()


def load_checkpoint(tenant_id: str, crew_id: str) -> Optional[dict]:
    _init_db()
    with _lock, _get_conn() as conn:
        row = conn.execute(
            "SELECT state_json FROM checkpoints WHERE tenant_id=? AND crew_id=?",
            (tenant_id, crew_id)
        ).fetchone()
    return json.loads(row[0]) if row else None


def delete_checkpoint(tenant_id: str, crew_id: str) -> None:
    _init_db()
    with _lock, _get_conn() as conn:
        conn.execute(
            "DELETE FROM checkpoints WHERE tenant_id=? AND crew_id=?",
            (tenant_id, crew_id)
        )
        conn.commit()


# ── Entity Memory API (Contract 4 support) ───────────────────────────────────

def save_entity(tenant_id: str, entity_id: str, key: str, value: Any) -> None:
    _init_db()
    with _lock, _get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO entity_memory VALUES (?, ?, ?, ?, ?)",
            (tenant_id, entity_id, key, json.dumps(value, default=str), time.time())
        )
        conn.commit()


def get_entity(tenant_id: str, entity_id: str) -> dict:
    _init_db()
    with _lock, _get_conn() as conn:
        rows = conn.execute(
            "SELECT key, value_json FROM entity_memory WHERE tenant_id=? AND entity_id=?",
            (tenant_id, entity_id)
        ).fetchall()
    return {row[0]: json.loads(row[1]) for row in rows}


def get_entity_key(tenant_id: str, entity_id: str, key: str) -> Any:
    _init_db()
    with _lock, _get_conn() as conn:
        row = conn.execute(
            "SELECT value_json FROM entity_memory WHERE tenant_id=? AND entity_id=? AND key=?",
            (tenant_id, entity_id, key)
        ).fetchone()
    return json.loads(row[0]) if row else None


def delete_entity(tenant_id: str, entity_id: str) -> None:
    _init_db()
    with _lock, _get_conn() as conn:
        conn.execute(
            "DELETE FROM entity_memory WHERE tenant_id=? AND entity_id=?",
            (tenant_id, entity_id)
        )
        conn.commit()


# ── Workflow Log API ─────────────────────────────────────────────────────────

def log_event(tenant_id: str, crew_id: str, event_type: str, payload: Any = None) -> None:
    _init_db()
    with _lock, _get_conn() as conn:
        conn.execute(
            "INSERT INTO workflow_log (tenant_id, crew_id, event_type, payload, created_at) VALUES (?,?,?,?,?)",
            (tenant_id, crew_id, event_type, json.dumps(payload, default=str) if payload else None, time.time())
        )
        conn.commit()


def get_workflow_log(tenant_id: str, crew_id: str, limit: int = 100) -> list:
    _init_db()
    with _lock, _get_conn() as conn:
        rows = conn.execute(
            "SELECT event_type, payload, created_at FROM workflow_log "
            "WHERE tenant_id=? AND crew_id=? ORDER BY created_at DESC LIMIT ?",
            (tenant_id, crew_id, limit)
        ).fetchall()
    return [{"event_type": r[0], "payload": json.loads(r[1]) if r[1] else None, "created_at": r[2]} for r in rows]


# ── Admin API ────────────────────────────────────────────────────────────────

def list_tenants() -> list:
    _init_db()
    with _lock, _get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT tenant_id FROM checkpoints"
        ).fetchall()
    return [r[0] for r in rows]


def get_tenant_summary(tenant_id: str) -> dict:
    _init_db()
    with _lock, _get_conn() as conn:
        crew_count = conn.execute(
            "SELECT COUNT(*) FROM checkpoints WHERE tenant_id=?", (tenant_id,)
        ).fetchone()[0]
        entity_count = conn.execute(
            "SELECT COUNT(DISTINCT entity_id) FROM entity_memory WHERE tenant_id=?", (tenant_id,)
        ).fetchone()[0]
        last_event = conn.execute(
            "SELECT created_at FROM workflow_log WHERE tenant_id=? ORDER BY created_at DESC LIMIT 1",
            (tenant_id,)
        ).fetchone()
    return {
        "tenant_id": tenant_id,
        "active_crews": crew_count,
        "entity_memories": entity_count,
        "last_activity": last_event[0] if last_event else None,
    }
