"""Synchronous orchestration of the agent stages. Each stage mirrors one uAgent hop and logs it.

The same pure logic is wrapped by the real uAgents in backend/agents/*, which exchange the typed
Models over the Bureau / Agentverse. The dashboard API uses this module so it never blocks on the network.
"""
import uuid
from typing import Iterable, Optional

from .graph import resolve_block
from .llm import llm_explain
from .logic.coordination import assign_vehicles, build_plan, diff_plans
from .logic.intake import parse_batch
from .logic.resources import allocate, fleet_from_inventory
from .logic.routing import route_options
from .logic.verification import verify
from .models import (ParsedReport, RawReport, RequestRoutes, SupplyAllocation, Vehicle, VerifiedRequest, dump)
from .state import ReliefState


def stage_intake(s: ReliefState) -> None:
    with s.lock:
        raws = [RawReport(**r) for r in s.raw_reports]
        s.log("Coordinator", "IntakeAgent", "RawBatch", f"{len(raws)} raw reports")
        parsed = parse_batch(raws)
        s.parsed = [dump(p) for p in parsed]
        s.log("IntakeAgent", "VerificationAgent", "ParsedBatch",
              f"{len(parsed)} reports parsed ({', '.join(sorted({p.parser for p in parsed})) or 'none'})")
        s.stage = "intake"


def stage_verify(s: ReliefState) -> None:
    with s.lock:
        reqs, status, log = verify([ParsedReport(**p) for p in s.parsed])
        s.verified = [dump(r) for r in reqs]
        s.report_status, s.merge_log = status, log
        dup = sum(v == "duplicate" for v in status.values())
        conf = sum(r.status == "conflict" for r in reqs)
        s.log("VerificationAgent", "ResourceAgent", "VerifiedBatch",
              f"{len(reqs)} unique requests, {dup} duplicate(s) merged, {conf} conflict(s) flagged")
        s.stage = "verified"


def stage_resources(s: ReliefState) -> None:
    with s.lock:
        reqs = [VerifiedRequest(**r) for r in s.verified]
        allocs, left = allocate(reqs, s.cfg["inventory"])
        s.allocations = [dump(a) for a in allocs]
        s.inventory_left = left
        s.fleet = [dump(v) for v in fleet_from_inventory(s.cfg["inventory"])]
        short = sum(1 for a in allocs if a.shortages)
        s.log("ResourceAgent", "RoutingAgent", "AllocationBatch",
              f"supplies matched; {short} request(s) with shortages; fleet={len(s.fleet)} vehicles")
        s.stage = "resources"


def stage_routing(s: ReliefState) -> None:
    with s.lock:
        reqs = [VerifiedRequest(**r) for r in s.verified]
        fleet = [Vehicle(**v) for v in s.fleet]
        routes = route_options(reqs, fleet, s.edges, set(s.blocked))
        s.routes = [dump(r) for r in routes]
        ok = sum(o.feasible for r in routes for o in r.options)
        s.log("RoutingAgent", "CoordinatorAgent", "RoutedBatch",
              f"{ok} feasible vehicle routes computed; {len(s.blocked)} blocked edge(s) avoided")
        s.stage = "routed"


def stage_coordinate(s: ReliefState, excluded: Optional[Iterable[str]] = None) -> None:
    with s.lock:
        reqs = [VerifiedRequest(**r) for r in s.verified]
        allocs = [SupplyAllocation(**a) for a in s.allocations]
        fleet = [Vehicle(**v) for v in s.fleet]
        routes = [RequestRoutes(**r) for r in s.routes]
        items, conflicts = assign_vehicles(reqs, allocs, fleet, routes, set(excluded or []))
        prev = s.plan
        version = (prev["version"] + 1) if prev else 1
        plan = build_plan(version, items, conflicts, allocs, s.blocked)
        plan["explanation"] = llm_explain(plan["summary"]) or plan["summary"]
        s.previous_plan, s.plan = prev, plan
        s.diff = diff_plans(prev, plan)
        s.conflicts = conflicts
        for c in conflicts:
            s.log("CoordinatorAgent", "CoordinatorAgent", "ConflictResolved", f"{c['resource']}: {c['resolution']}")
        s.log("CoordinatorAgent", "Operator", "ApprovalRequest", f"Plan v{version} awaiting human approval")
        s.stage = "plan_pending"
        s.save()


def run_all(s: ReliefState, excluded: Optional[Iterable[str]] = None) -> None:
    stage_intake(s)
    stage_verify(s)
    stage_resources(s)
    stage_routing(s)
    stage_coordinate(s, excluded)


def load_seed_reports(s: ReliefState) -> None:
    with s.lock:
        s.raw_reports = [dict(r) for r in s.cfg["reports"]]
        s.log("Citizens/Field", "CoordinatorAgent", "RawReports", f"{len(s.raw_reports)} incoming reports")


def add_report(s: ReliefState, raw: dict) -> None:
    with s.lock:
        raw = dict(raw)
        raw.setdefault("id", f"R{len(s.raw_reports) + 1}")
        raw.setdefault("state", "Assam")
        raw.setdefault("timestamp", "2026-10-18T11:00:00")
        s.raw_reports.append(raw)
        s.log("Citizens/Field", "CoordinatorAgent", "RawReport", f"{raw['id']}: {raw['text'][:60]}")


def block_road(s: ReliefState, spec: dict) -> list:
    """Road-blocked event: Coordinator asks Routing to recompute, then rebuilds the plan (needs re-approval)."""
    with s.lock:
        ids = resolve_block(s.edges, spec)
        if not ids:
            raise ValueError("No matching road edges for that blocked-route request.")
        new = [i for i in ids if i not in s.blocked]
        s.blocked.extend(new)
        label = spec.get("village") or spec.get("edge") or f"{spec.get('from')}-{spec.get('to')}"
        s.blocked_events.append(f"Road to {label} blocked ({len(new)} edge(s))")
        s.log("Operator", "CoordinatorAgent", "BlockEvent", f"Road blocked: {label}")
        s.log("CoordinatorAgent", "RoutingAgent", "AllocationBatch", "recompute routes with blocked edges")
        stage_routing(s)
        stage_coordinate(s)
        return new


def request_changes(s: ReliefState, note: str = "", exclude: Optional[Iterable[str]] = None) -> None:
    with s.lock:
        if not s.plan:
            raise ValueError("No plan to change.")
        s.log("Operator", "CoordinatorAgent", "RequestChanges", note or "changes requested")
        stage_coordinate(s, exclude)
