"""Coordinator logic: conflict resolution, plan building, diffing and the human-approval gate."""
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple

from ..models import RequestRoutes, SupplyAllocation, Vehicle, VerifiedRequest

LOAD_H = 0.5            # loading / turnaround time added after each sortie
HELI_TRIGGER_H = 9.0    # helicopter is a last resort: only if best ground completion exceeds this
MAX_WAIT_H = 24.0       # sites that cannot be served inside this window are deferred to the next cycle


class ApprovalError(Exception):
    """Raised when someone tries to approve/dispatch without a pending plan."""


def fmt_eta(h: float) -> str:
    return f"{round(h * 60)} min" if h < 1 else f"{h:.1f} hours"


def assign_vehicles(requests: List[VerifiedRequest], allocations: List[SupplyAllocation],
                    fleet: List[Vehicle], routes: List[RequestRoutes],
                    excluded: Optional[Set[str]] = None) -> Tuple[List[dict], List[dict]]:
    """Greedy by priority. Each vehicle does sorties one after another; ETA includes queue time.

    A conflict is recorded when the fastest ground vehicle for a request was already claimed by a
    higher-priority request. Resolution: the higher priority keeps it; the other gets an alternate
    vehicle (boat via river, helicopter as last resort) or is queued behind it.
    """
    excluded = set(excluded or [])
    alloc = {a.request_id: a for a in allocations}
    vmap = {v.id: v for v in fleet}
    by_req = {r.request_id: [o for o in r.options if o.feasible and o.vehicle_id not in excluded] for r in routes}
    busy = {v.id: 0.0 for v in fleet}
    holder: Dict[str, str] = {}
    village = {r.id: r.village for r in requests}
    items: List[dict] = []
    conflicts: List[dict] = []

    for req in sorted(requests, key=lambda r: -r.score):
        opts = by_req.get(req.id, [])
        ground = [o for o in opts if o.mode != "air"]
        air = [o for o in opts if o.mode == "air"]
        comp = lambda o: busy[o.vehicle_id] + o.eta_h  # noqa: E731
        ideal = min(ground, key=lambda o: o.eta_h) if ground else None
        best_ground = min(ground, key=comp) if ground else None
        best_air = min(air, key=comp) if air else None

        chosen, note = None, ""
        if best_ground and not (req.urgency >= 4 and best_air and comp(best_ground) > HELI_TRIGGER_H
                                and comp(best_air) < comp(best_ground)):
            chosen = best_ground
        elif best_air:
            chosen = best_air
            note = ("Helicopter used as last resort: ground options too slow for a high-priority site."
                    if best_ground else "Helicopter used as last resort: no road/river route available.")

        a = alloc[req.id]
        item = {"request_id": req.id, "merged_ids": req.merged_ids, "village": req.village,
                "district": req.district, "state": req.state, "needs": req.needs, "people": req.people,
                "priority": req.priority, "urgency": req.urgency, "score": req.score,
                "supplies": {"food": a.food, "water": a.water, "medicines": a.medicines},
                "volunteers": a.volunteers, "shortages": a.shortages, "dispatched": False}
        if not chosen:
            item.update({"status": "unserved", "vehicle_id": None, "vehicle_type": None, "team": None,
                         "mode": None, "path": [], "eta_h": None, "eta_label": "n/a", "distance_km": None,
                         "alt": None, "notes": "No feasible route (all paths blocked or no vehicle available)."})
            items.append(item)
            continue

        wait = busy[chosen.vehicle_id]
        eta = comp(chosen)
        if eta > MAX_WAIT_H:
            item.update({"status": "deferred", "vehicle_id": None, "vehicle_type": None, "team": None,
                         "mode": None, "path": [], "eta_h": None, "eta_label": "deferred", "distance_km": None,
                         "alt": None, "notes": f"Deferred: no vehicle free within {MAX_WAIT_H:.0f} h "
                                               f"(earliest {fmt_eta(eta)} on {chosen.vehicle_id}). Re-plan when a vehicle returns."})
            items.append(item)
            continue
        busy[chosen.vehicle_id] = eta + chosen.eta_h + LOAD_H
        if ideal and ideal.vehicle_id in holder and (chosen.vehicle_id != ideal.vehicle_id or wait > 0):
            win = holder[ideal.vehicle_id]
            how = (f"queued behind {win} on {chosen.vehicle_id} (+{fmt_eta(wait)})"
                   if chosen.vehicle_id == ideal.vehicle_id
                   else f"reassigned to {chosen.vehicle_id} ({chosen.mode}, ETA {fmt_eta(eta)})")
            conflicts.append({"id": f"C{len(conflicts) + 1}", "resource": ideal.vehicle_id, "winner": win,
                              "loser": req.id, "winner_village": village[win], "loser_village": req.village,
                              "resolution": f"{village[win]} (higher priority) keeps {ideal.vehicle_id}; "
                                            f"{req.village} {how}. Volunteers split by priority."})
        holder.setdefault(chosen.vehicle_id, req.id)

        alts = [o for o in opts if o.vehicle_id != chosen.vehicle_id]
        alt = min(alts, key=comp) if alts else None
        item.update({"status": "planned", "vehicle_id": chosen.vehicle_id, "vehicle_type": chosen.vehicle_type,
                     "team": vmap[chosen.vehicle_id].team, "mode": chosen.mode, "path": chosen.path,
                     "eta_h": round(eta, 2), "eta_label": fmt_eta(eta), "distance_km": chosen.distance_km,
                     "alt": ({"vehicle_id": alt.vehicle_id, "mode": alt.mode, "path": alt.path,
                              "eta_h": round(comp(alt), 2)} if alt else None),
                     "notes": note})
        items.append(item)
    return items, conflicts


def build_plan(version: int, items: List[dict], conflicts: List[dict], allocations: List[SupplyAllocation],
               blocked: List[str], explanation: str = "") -> dict:
    shortages: Dict[str, int] = {}
    for a in allocations:
        for k, v in a.shortages.items():
            shortages[k] = shortages.get(k, 0) + v
    planned = [i for i in items if i["status"] == "planned"]
    deferred = [i for i in items if i["status"] == "deferred"]
    summary = (f"{len(planned)}/{len(items)} sites scheduled"
               + (f", {len(deferred)} deferred" if deferred else "")
               + f", {len(conflicts)} resource conflict(s) resolved"
               + (f", {len(blocked)} blocked route(s) avoided" if blocked else "")
               + (f", shortages: {', '.join(f'{k} {v}' for k, v in shortages.items())}" if shortages else "") + ".")
    return {"version": version, "status": "pending_approval", "created": datetime.now(timezone.utc).isoformat(),
            "items": items, "conflicts": conflicts, "shortages": shortages, "blocked": list(blocked),
            "summary": summary, "explanation": explanation or summary}


def diff_plans(old: Optional[dict], new: dict) -> List[dict]:
    """Before/after view per village (used after a road-blocked replan)."""
    if not old:
        return []
    prev = {i["request_id"]: i for i in old["items"]}
    out = []
    for n in new["items"]:
        o = prev.get(n["request_id"])
        if not o:
            continue
        key = lambda i: (i.get("vehicle_id"), i.get("mode"), i.get("eta_h"), tuple(i.get("path") or []))  # noqa: E731
        out.append({"request_id": n["request_id"], "village": n["village"], "changed": key(o) != key(n),
                    "before": {"vehicle": o["vehicle_id"], "mode": o["mode"], "eta": o["eta_label"], "path": o["path"]},
                    "after": {"vehicle": n["vehicle_id"], "mode": n["mode"], "eta": n["eta_label"], "path": n["path"]}})
    return out


def approve_plan(plan: Optional[dict]) -> dict:
    """THE approval gate: the only code path that sets dispatched=True."""
    if not plan:
        raise ApprovalError("No plan to approve.")
    if plan["status"] != "pending_approval":
        raise ApprovalError(f"Plan v{plan['version']} is '{plan['status']}', not pending approval.")
    plan["status"] = "approved"
    plan["approved_at"] = datetime.now(timezone.utc).isoformat()
    for it in plan["items"]:
        it["dispatched"] = it["status"] == "planned"
    return plan
