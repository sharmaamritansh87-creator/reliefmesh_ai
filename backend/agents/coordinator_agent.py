"""Coordinator Agent: orchestrates the pipeline, resolves conflicts, WAITS for human approval,
and exposes the uAgents Chat Protocol so it can be discovered and used from ASI:One.

NOTE: chat-protocol imports follow the Fetch.ai Innovation Lab docs (uagents_core.contrib.protocols.chat).
If your installed uagents version differs, adjust the import block below (see the hackpack).
"""
import uuid
from datetime import datetime, timezone

from uagents import Context, Protocol
from uagents_core.contrib.protocols.chat import (ChatAcknowledgement, ChatMessage, EndSessionContent,
                                                 StartSessionContent, TextContent, chat_protocol_spec)

from .. import pipeline as pl
from ..logic.coordination import ApprovalError
from ..models import RawBatch, RawReport, RoutedBatch, dump
from ..state import DISCLAIMER, get_state
from .common import address_of, make_agent

agent = make_agent("coordinator")
chat_proto = Protocol(spec=chat_protocol_spec)
HELP = ("ReliefMesh AI (North-East India, SIMULATED data). Try: 'report flooding in Majuli, 150 people need food' | "
        "'show current plan' | 'road to Dhemaji blocked' | 'approve plan' | 'reset'.")


def _reply(text: str, end: bool = False) -> ChatMessage:
    content = [TextContent(type="text", text=text)]
    if end:
        content.append(EndSessionContent(type="end-session"))
    return ChatMessage(timestamp=datetime.now(timezone.utc), msg_id=uuid.uuid4(), content=content)


def _plan_text() -> str:
    s = get_state()
    if not s.plan:
        return "No plan yet. Send a report first."
    p = s.plan
    lines = [f"Plan v{p['version']} [{p['status']}] - {p['summary']}"]
    for i in p["items"]:
        lines.append(f"- {i['village']} ({i['priority']}): " + (
            f"{i['vehicle_id']} via {i['mode']}, ETA {i['eta_label']}, volunteers {i['volunteers']}"
            if i["status"] == "planned" else i["status"]))
    lines.append("Reply 'approve plan' to release dispatch. " + DISCLAIMER)
    return "\n".join(lines)


def _find_village(text: str):
    s = get_state()
    t = text.lower()
    aliases = {"garo": "West Garo Hills", "siang": "East Siang"}
    for n in s.cfg["ne_graph"]["nodes"]:
        if n["kind"] == "village" and n["id"].lower() in t:
            return n
    for k, v in aliases.items():
        if k in t:
            return next(n for n in s.cfg["ne_graph"]["nodes"] if n["id"] == v)
    return None


async def _handle(ctx: Context, sender: str, text: str) -> str:
    s = get_state()
    t = text.lower().strip()
    if not t or t in ("help", "hi", "hello"):
        return HELP
    if t.startswith("reset"):
        s.reset()
        return "State reset."
    if "approve" in t:
        try:
            s.approve()
            return "Plan approved by human operator. Dispatch orders released.\n" + _plan_text()
        except ApprovalError as e:
            return f"Cannot approve: {e}"
    if any(k in t for k in ("show", "current plan", "status", "plan?")):
        return _plan_text()
    node = _find_village(text)
    if "block" in t:
        if not node:
            return "Which village's road is blocked? e.g. 'road to Dhemaji blocked'."
        if not s.plan:
            pl.load_seed_reports(s)
            pl.run_all(s)
        pl.block_road(s, {"village": node["id"]})
        return f"Road to {node['id']} marked blocked. Agents recomputed.\n" + _plan_text()
    if node:
        pl.add_report(s, {"text": text, "village": node["id"], "district": node["id"], "state": node["state"],
                          "lat": node["lat"], "lon": node["lon"]})
        run_id = str(uuid.uuid4())[:8]
        s.pending_chat[run_id] = sender
        await ctx.send(address_of("intake"), RawBatch(run_id=run_id, reports=[RawReport(**r) for r in s.raw_reports]))
        return "Report received. Intake -> Verification -> Resource -> Routing agents are working; I will send the plan."
    return HELP


@chat_proto.on_message(ChatMessage)
async def on_chat(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(sender, ChatAcknowledgement(timestamp=datetime.now(timezone.utc), acknowledged_msg_id=msg.msg_id))
    for c in msg.content:
        if isinstance(c, StartSessionContent):
            await ctx.send(sender, _reply(HELP))
        elif isinstance(c, TextContent):
            await ctx.send(sender, _reply(await _handle(ctx, sender, c.text)))


@chat_proto.on_message(ChatAcknowledgement)
async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    ctx.logger.info(f"ack from {sender} for {msg.acknowledged_msg_id}")


@agent.on_message(model=RoutedBatch)
async def on_routed(ctx: Context, sender: str, msg: RoutedBatch):
    """Final hop: resolve conflicts, build the plan, then WAIT for approval (never auto-dispatch)."""
    s = get_state()
    with s.lock:
        s.verified = [dump(r) for r in msg.requests]
        s.allocations = [dump(a) for a in msg.allocations]
        s.fleet = [dump(v) for v in msg.fleet]
        s.routes = [dump(r) for r in msg.routes]
        pl.stage_coordinate(s)
    ctx.logger.info(f"[coordinator] plan v{s.plan['version']} ready, awaiting human approval")
    target = s.pending_chat.pop(msg.run_id, None)
    if target:
        await ctx.send(target, _reply(_plan_text()))


agent.include(chat_proto, publish_manifest=True)

if __name__ == "__main__":
    agent.run()
