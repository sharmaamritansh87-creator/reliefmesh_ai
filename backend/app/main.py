"""FastAPI dashboard API: REST + SSE. Nothing is dispatched without POST /plan/approve."""
import asyncio
import json
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .. import demo, pipeline as pl
from ..logic.coordination import ApprovalError
from ..state import get_state

app = FastAPI(title="ReliefMesh AI", description="Multi-agent disaster response (SIMULATED DATA)")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class ReportIn(BaseModel):
    text: str
    village: str
    district: Optional[str] = None
    state: str = "Assam"
    lat: float
    lon: float
    timestamp: Optional[str] = None


class BlockIn(BaseModel):
    village: Optional[str] = None
    edge: Optional[str] = None
    from_: Optional[str] = Field(None, alias="from")
    to: Optional[str] = None
    mode: str = "road"


class ChangesIn(BaseModel):
    note: str = ""
    exclude_vehicles: List[str] = []


@app.get("/health")
def health():
    return {"ok": True, "region": get_state().cfg["ne_graph"]["region"]}


@app.get("/state")
def state():
    return get_state().snapshot()


@app.get("/graph")
def graph():
    s = get_state()
    return {"region": s.cfg["ne_graph"]["region"], "center": s.cfg["ne_graph"].get("map_center", [26.6, 93.0]),
            "nodes": s.cfg["ne_graph"]["nodes"], "edges": [e for e in s.edges if e["mode"] != "air"]}


@app.get("/agents/log")
def agent_log(limit: int = 100):
    return get_state().agent_log[-limit:]


@app.post("/reports")
def post_report(r: ReportIn):
    s = get_state()
    d = r.dict()
    d["district"] = d["district"] or d["village"]
    if not d["timestamp"]:
        d.pop("timestamp")
    pl.add_report(s, d)
    pl.run_all(s)
    return {"ok": True, "plan_version": s.plan["version"], "status": s.plan["status"]}


@app.post("/reports/seed")
def seed_reports():
    s = get_state()
    pl.load_seed_reports(s)
    pl.run_all(s)
    return {"ok": True, "reports": len(s.raw_reports)}


@app.post("/events/road-blocked")
def road_blocked(b: BlockIn):
    s = get_state()
    if not s.plan:
        raise HTTPException(409, "No plan yet; submit reports first.")
    try:
        edges = pl.block_road(s, {"village": b.village, "edge": b.edge, "from": b.from_, "to": b.to, "mode": b.mode})
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True, "blocked_edges": edges, "plan_version": s.plan["version"], "status": s.plan["status"]}


@app.post("/plan/approve")
def approve():
    try:
        plan = get_state().approve()
    except ApprovalError as e:
        raise HTTPException(409, str(e))
    return {"ok": True, "status": plan["status"], "dispatched": sum(i["dispatched"] for i in plan["items"])}


@app.post("/plan/request-changes")
def request_changes(c: ChangesIn):
    try:
        pl.request_changes(get_state(), c.note, c.exclude_vehicles)
    except ValueError as e:
        raise HTTPException(409, str(e))
    return {"ok": True, "plan_version": get_state().plan["version"], "status": get_state().plan["status"]}


@app.post("/demo/start")
def demo_start():
    return demo.start(get_state())


@app.post("/demo/step")
def demo_step():
    return demo.step(get_state())


@app.post("/demo/reset")
def demo_reset():
    get_state().reset()
    return {"ok": True}


@app.get("/stream")
async def stream():
    """Server-sent events: pushes a snapshot whenever state changes."""
    async def gen():
        last = -1
        while True:
            s = get_state()
            if s.version != last:
                last = s.version
                yield f"data: {json.dumps(s.snapshot())}\n\n"
            await asyncio.sleep(0.8)
    return StreamingResponse(gen(), media_type="text/event-stream")
