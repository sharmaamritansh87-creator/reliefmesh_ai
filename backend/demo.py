"""Scripted 8-step demo: alert -> reports -> verification -> resources -> routing -> conflict -> road blocked -> approve."""
from . import pipeline as p
from .state import ReliefState

STEPS = [
    ("alert", "Flood alert issued for the Brahmaputra basin; reports will start arriving"),
    ("reports", "10 emergency reports arrive (English / Hinglish / Assamese-Latin)"),
    ("verify", "Intake parses reports; Verification merges duplicates and flags conflicts"),
    ("resources", "Resource Agent matches limited supplies and volunteers by priority"),
    ("routing", "Routing Agent computes road / river / air options"),
    ("conflict", "Coordinator resolves vehicle conflicts and asks for human approval"),
    ("road_blocked", "Road to Dhemaji is blocked; agents recompute the plan"),
    ("approve", "Human operator approves the final plan; dispatch is released"),
]


def start(s: ReliefState) -> dict:
    s.reset()
    return step(s)


def step(s: ReliefState) -> dict:
    with s.lock:
        idx = s.demo_step + 1
        if idx >= len(STEPS):
            return {"index": len(STEPS) - 1, "key": "done", "title": "Demo complete", "done": True}
        key, title = STEPS[idx]
        if key == "alert":
            s.alert = "Flood alert: Brahmaputra above danger level across upper Assam."
            s.log("System", "CoordinatorAgent", "FloodAlert", s.alert)
        elif key == "reports":
            p.load_seed_reports(s)
        elif key == "verify":
            p.stage_intake(s)
            p.stage_verify(s)
        elif key == "resources":
            p.stage_resources(s)
        elif key == "routing":
            p.stage_routing(s)
        elif key == "conflict":
            p.stage_coordinate(s)
        elif key == "road_blocked":
            p.block_road(s, {"village": "Dhemaji"})
        elif key == "approve":
            s.approve()
        s.demo_step = idx
        s.version += 1
        s.save()
        return {"index": idx, "key": key, "title": title, "done": idx == len(STEPS) - 1}
