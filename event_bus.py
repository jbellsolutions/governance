"""
In-process event bus — broadcasts agent activity to all SSE panel clients.
Thread-safe: agents run in threads, panel serves async clients.
"""
import json
import time
import queue
import threading
from typing import Optional

_subscribers: list[queue.Queue] = []
_lock = threading.Lock()
_history: list[dict] = []  # last 500 events for reconnecting clients
_HISTORY_LIMIT = 500


def publish(
    event_type: str,
    business_id: str,
    team_id: str = "",
    agent_name: str = "",
    message: str = "",
    data: Optional[dict] = None,
    level: str = "info",  # info | success | warning | error
) -> None:
    """Broadcast an event to all connected panel clients."""
    event = {
        "type": event_type,
        "business_id": business_id,
        "team_id": team_id,
        "agent_name": agent_name,
        "message": message,
        "data": data or {},
        "level": level,
        "ts": time.time(),
    }
    with _lock:
        _history.append(event)
        if len(_history) > _HISTORY_LIMIT:
            _history.pop(0)
        for q in _subscribers[:]:
            try:
                q.put_nowait(event)
            except queue.Full:
                pass  # slow client — drop event rather than block


def subscribe(since: float = 0.0) -> queue.Queue:
    """Subscribe to events. Backfills events since `since` timestamp."""
    q: queue.Queue = queue.Queue(maxsize=200)
    with _lock:
        for ev in _history:
            if ev["ts"] > since:
                try:
                    q.put_nowait(ev)
                except queue.Full:
                    break
        _subscribers.append(q)
    return q


def unsubscribe(q: queue.Queue) -> None:
    with _lock:
        try:
            _subscribers.remove(q)
        except ValueError:
            pass


def recent(limit: int = 100, business_id: Optional[str] = None) -> list:
    with _lock:
        events = _history[-limit:]
    if business_id:
        events = [e for e in events if e["business_id"] == business_id]
    return events
