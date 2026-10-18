"""Core behaviour tests: dedupe, conflict resolution, rerouting on a blocked edge, approval gate."""
import pytest

from backend import pipeline as p
from backend.logic.coordination import ApprovalError
from backend.state import ReliefState


@pytest.fixture()
def s():
    st = ReliefState(persist=False)
    p.load_seed_reports(st)
    p.run_all(st)
    return st


def item(st, village):
    return next(i for i in st.plan["items"] if i["village"] == village)


def test_dedupe_merges_r1_r2(s):
    req = next(r for r in s.verified if r["id"] == "R1")
    assert req["merged_ids"] == ["R1", "R2"]
    assert req["status"] == "merged" and req["people"] == 200
    assert set(req["needs"]) == {"food", "water"}
    assert s.report_status["R2"] == "duplicate"


def test_conflicting_headcounts_flagged(s):
    req = next(r for r in s.verified if r["id"] == "R7")
    assert req["status"] == "conflict" and req["people"] == 300
    assert s.report_status["R10"] == "conflict"
    assert req["confidence"] < 0.8


def test_ten_reports_become_eight_unique_requests(s):
    assert len(s.raw_reports) == 10 and len(s.verified) == 8


def test_truck_conflict_resolved_by_priority(s):
    assert s.conflicts, "expected at least one resource conflict"
    c = next(c for c in s.conflicts if c["resource"] == "Truck-1")
    winner = next(i for i in s.plan["items"] if i["request_id"] == c["winner"])
    loser = next(i for i in s.plan["items"] if i["request_id"] == c["loser"])
    assert winner["vehicle_id"] == "Truck-1"
    assert winner["score"] > loser["score"]
    assert loser["vehicle_id"] != "Truck-1"


def test_majuli_needs_river_or_air(s):
    assert item(s, "Majuli")["mode"] in ("river", "air")  # island: no road


def test_reroute_when_road_blocked(s):
    before = item(s, "Dhemaji")
    assert before["vehicle_type"] == "truck"
    blocked = p.block_road(s, {"village": "Dhemaji"})
    assert blocked
    after = item(s, "Dhemaji")
    assert after["vehicle_type"] != "truck" and after["mode"] in ("river", "air")
    used = {tuple(sorted(e)) for e in zip(after["path"], after["path"][1:])}
    for eid in s.blocked:
        a, b, mode = eid.split("|")
        if after["mode"] == mode:
            assert tuple(sorted((a, b))) not in used
    assert next(d for d in s.diff if d["village"] == "Dhemaji")["changed"]


def test_unreachable_when_every_route_blocked(s):
    p.block_road(s, {"village": "Cachar"})
    assert item(s, "Cachar")["vehicle_type"] in ("helicopter", None)


def test_approval_gate_blocks_dispatch(s):
    assert s.plan["status"] == "pending_approval"
    assert not any(i["dispatched"] for i in s.plan["items"])
    s.approve()
    assert s.plan["status"] == "approved"
    assert any(i["dispatched"] for i in s.plan["items"])
    with pytest.raises(ApprovalError):
        s.approve()  # cannot approve twice


def test_replan_requires_reapproval(s):
    s.approve()
    p.block_road(s, {"village": "Dhemaji"})
    assert s.plan["status"] == "pending_approval"
    assert not any(i["dispatched"] for i in s.plan["items"])


def test_cannot_approve_without_plan():
    st = ReliefState(persist=False)
    with pytest.raises(ApprovalError):
        st.approve()


def test_request_changes_excludes_vehicle(s):
    p.request_changes(s, "no helicopter", exclude=["Heli-1"])
    assert all(i["vehicle_id"] != "Heli-1" for i in s.plan["items"])


def test_shortages_reported(s):
    assert s.plan["shortages"].get("water", 0) > 0
