"""
Governance Panel — FastAPI server for the web control panel.

Endpoints:
  GET  /                               — serves web/index.html
  GET  /stream/{business_id}           — SSE real-time event stream
  GET  /events                         — recent event history (REST)
  GET  /businesses                     — list all businesses
  POST /businesses                     — create business
  GET  /businesses/{id}                — get business details
  DELETE /businesses/{id}              — delete business
  POST /businesses/{id}/teams          — add team
  DELETE /businesses/{id}/teams/{type} — remove team
  POST /businesses/{id}/chat           — chat with CEO
  DELETE /businesses/{id}/chat         — reset CEO conversation
  GET  /health                         — health check
  GET  /status                         — system status
"""
import os
import asyncio
import json
import queue
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from governance import event_bus, business_registry
from governance.core import state_manager

app = FastAPI(
    title="Governance Panel",
    description="Real-time control panel for autonomous agent businesses",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# CEO cache — one CEOOrchestrator per business, created on first chat
_ceos: dict = {}


def _get_ceo(business_id: str):
    if business_id not in _ceos:
        biz = business_registry.get_business(business_id)
        if not biz:
            return None
        from governance.orchestrator import CEOOrchestrator
        _ceos[business_id] = CEOOrchestrator(
            business_id=biz["id"],
            business_name=biz["name"],
            tenant_id=biz["tenant_id"],
        )
    return _ceos[business_id]


# ── Request / Response Models ─────────────────────────────────────────────────

class BusinessCreate(BaseModel):
    name: str
    description: str = ""
    teams: list = ["exec_team"]


class TeamAdd(BaseModel):
    team_type: str


class ChatMessage(BaseModel):
    message: str


# ── SSE Stream ────────────────────────────────────────────────────────────────

@app.get("/stream/{business_id}")
async def event_stream(
    business_id: str,
    request: Request,
    since: float = 0.0,
):
    """
    Server-Sent Events — streams real-time agent activity to the panel.
    business_id="all" receives events from every business.
    Heartbeat comment sent every 15 s to keep the connection alive.
    """

    async def generate():
        q = event_bus.subscribe(since=since)
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    loop = asyncio.get_event_loop()
                    event = await loop.run_in_executor(None, _dequeue, q)
                    if event is None:
                        yield ": keepalive\n\n"
                        continue
                    if business_id == "all" or event.get("business_id") == business_id:
                        yield f"data: {json.dumps(event)}\n\n"
                except asyncio.CancelledError:
                    break
                except Exception:
                    break
        finally:
            event_bus.unsubscribe(q)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _dequeue(q: queue.Queue):
    try:
        return q.get(timeout=15)
    except queue.Empty:
        return None


# ── Business CRUD ─────────────────────────────────────────────────────────────

@app.get("/businesses")
def list_businesses():
    return {"businesses": business_registry.list_businesses()}


@app.post("/businesses", status_code=201)
def create_business(body: BusinessCreate):
    try:
        biz = business_registry.create_business(body.name, body.description, body.teams)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    event_bus.publish(
        "business_created", biz["id"],
        message=f"Business '{body.name}' created", level="success",
    )
    return biz


@app.get("/businesses/{business_id}")
def get_business(business_id: str):
    biz = business_registry.get_business(business_id)
    if not biz:
        raise HTTPException(status_code=404, detail="Business not found")
    return biz


@app.delete("/businesses/{business_id}", status_code=204)
def delete_business(business_id: str):
    if not business_registry.delete_business(business_id):
        raise HTTPException(status_code=404, detail="Business not found")
    _ceos.pop(business_id, None)


@app.post("/businesses/{business_id}/teams")
def add_team(business_id: str, body: TeamAdd):
    try:
        biz = business_registry.add_team(business_id, body.team_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    event_bus.publish(
        "team_added", business_id, team_id=body.team_type,
        message=f"Team '{body.team_type}' added to {biz['name']}", level="success",
    )
    return biz


@app.delete("/businesses/{business_id}/teams/{team_type}")
def remove_team(business_id: str, team_type: str):
    try:
        biz = business_registry.remove_team(business_id, team_type)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return biz


# ── CEO Chat ──────────────────────────────────────────────────────────────────

@app.post("/businesses/{business_id}/chat")
def chat(business_id: str, body: ChatMessage):
    """Talk to the CEO. Blocks until the CEO responds (teams may run async)."""
    ceo = _get_ceo(business_id)
    if not ceo:
        raise HTTPException(status_code=404, detail="Business not found")
    try:
        response = ceo.chat(body.message)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"CEO error: {exc}")
    return {"response": response, "business_id": business_id}


@app.delete("/businesses/{business_id}/chat", status_code=204)
def reset_chat(business_id: str):
    """Clear the CEO's conversation history for this business."""
    ceo = _get_ceo(business_id)
    if ceo:
        ceo.reset_conversation()
    _ceos.pop(business_id, None)


# ── Event History ─────────────────────────────────────────────────────────────

@app.get("/events")
def recent_events(business_id: Optional[str] = None, limit: int = 100):
    return {"events": event_bus.recent(limit=limit, business_id=business_id or None)}


# ── Status ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "governance-panel", "version": "1.0.0"}


@app.get("/status")
def system_status():
    businesses = business_registry.list_businesses()
    return {
        "businesses": len(businesses),
        "services": {
            "openrouter_key": bool(os.environ.get("OPENROUTER_API_KEY")),
            "slack_configured": bool(os.environ.get("SLACK_BOT_TOKEN")),
            "paperclip_url": os.environ.get("PAPERCLIP_URL", "http://localhost:3000"),
            "db_path": os.environ.get("STATE_DB_PATH", "(default local)"),
        },
    }


# ── Static Files (web UI) — must be registered last ──────────────────────────
_WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
if os.path.isdir(_WEB_DIR):
    app.mount("/", StaticFiles(directory=_WEB_DIR, html=True), name="static")
else:
    @app.get("/")
    def root():
        return HTMLResponse(
            "<h1>Governance Panel</h1>"
            "<p>Web UI not found. Run from the governance repo root "
            "so the <code>web/</code> directory is present.</p>"
            "<p>API docs: <a href='/docs'>/docs</a></p>"
        )
