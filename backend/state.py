"""Shared in-memory state (thread-safe) with JSON persistence."""
import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from .graph import build_edges, data_dir, load_config
from .logic.coordination import ApprovalError, approve_plan

BANNER = "SIMULATED DEMO DATA - NOT A REAL EMERGENCY"
DISCLAIMER = "Decision-support only. Human approval is required before any real-world dispatch."


class ReliefState:
    def __init__(self, folder: Optional[str] = None, persist: bool = False):
        self.lock = threading.RLock()
        self.cfg = load_config(folder)
        self.edges = build_edges(self.cfg["ne_graph"])
        self.persist = persist
        self.reset()

    def reset(self) -> None:
        with self.lock:
            self.raw_reports: List[dict] = []
            self.parsed: List[dict] = []
            self.verified: List[dict] = []
            self.report_status: dict = {}
            self.merge_log: List[str] = []
            self.allocations: List[dict] = []
            self.inventory_left: dict = {}
            self.fleet: List[dict] = []
            self.routes: List[dict] = []
            self.blocked: List[str] = []
            self.blocked_events: List[str] = []
            self.plan: Optional[dict] = None
            self.previous_plan: Optional[dict] = None
            self.diff: List[dict] = []
            self.conflicts: List[dict] = []
            self.agent_log: List[dict] = []
            self.stage = "idle"
            self.demo_step = -1
            self.alert: Optional[str] = None
            self.pending_chat: dict = {}
            self.version = 0
            self.save()

    # -- logging -------------------------------------------------------------------
    def log(self, src: str, dst: str, msg_type: str, summary: str) -> None:
        with self.lock:
            self.agent_log.append({"n": self.version + 1, "ts": datetime.now(timezone.utc).strftime("%H:%M:%S"),
                                   "from": src, "to": dst, "type": msg_type, "summary": summary})
            self.agent_log = self.agent_log[-200:]
            self.version += 1

    # -- approval ------------------------------------------------------------------
    def approve(self) -> dict:
        with self.lock:
            plan = approve_plan(self.plan)  # raises ApprovalError
            self.log("Operator", "CoordinatorAgent", "ApprovePlan", f"Plan v{plan['version']} approved by human")
            self.log("CoordinatorAgent", "Field Teams", "Dispatch",
                     f"{sum(1 for i in plan['items'] if i['dispatched'])} dispatch orders released")
            self.stage = "approved"
            self.save()
            return plan

    # -- views ---------------------------------------------------------------------
    def snapshot(self) -> dict:
        with self.lock:
            return {"banner": BANNER, "disclaimer": DISCLAIMER, "version": self.version, "stage": self.stage,
                    "demo_step": self.demo_step, "alert": self.alert, "raw_reports": self.raw_reports,
                    "parsed": self.parsed, "verified": self.verified, "report_status": self.report_status,
                    "merge_log": self.merge_log, "allocations": self.allocations,
                    "inventory_total": {"food_packets": self.cfg["inventory"]["supplies"]["food_packets"],
                                        "medicines": self.cfg["inventory"]["supplies"]["medicines"],
                                        "water_bottles": self.cfg["inventory"]["supplies"]["water_bottles"],
                                        "volunteers": self.cfg["inventory"]["volunteers"],
                                        "boats": sum(v["type"] == "boat" for v in self.cfg["inventory"]["vehicles"]),
                                        "trucks": sum(v["type"] == "truck" for v in self.cfg["inventory"]["vehicles"]),
                                        "helicopters": sum(v["type"] == "helicopter" for v in self.cfg["inventory"]["vehicles"])},
                    "inventory_left": self.inventory_left, "fleet": self.fleet, "teams": self.cfg["teams"],
                    "blocked": self.blocked, "blocked_events": self.blocked_events, "plan": self.plan,
                    "diff": self.diff, "conflicts": self.conflicts,
                    "agent_log": self.agent_log[-60:]}

    def save(self) -> None:
        if not self.persist:
            return
        try:
            p = Path(data_dir()) / "runtime_state.json"
            p.write_text(json.dumps(self.snapshot(), indent=2), encoding="utf-8")
        except OSError:
            pass


STATE: Optional[ReliefState] = None


def get_state() -> ReliefState:
    global STATE
    if STATE is None:
        STATE = ReliefState(persist=True)
    return STATE
