"""Typed messages exchanged between ReliefMesh agents (uAgents Models)."""
from typing import Dict, List

try:  # uAgents Model is a pydantic BaseModel
    from uagents import Model
except ImportError:  # allows running the logic/tests without uagents installed
    from pydantic import BaseModel as Model


class RawReport(Model):
    id: str
    text: str
    village: str
    district: str
    state: str = "Assam"
    lat: float
    lon: float
    timestamp: str


class ParsedReport(Model):
    id: str
    text: str
    village: str
    district: str
    state: str
    lat: float
    lon: float
    timestamp: str
    needs: List[str]
    people: int
    urgency: int
    language: str
    parser: str


class RawBatch(Model):
    run_id: str
    reports: List[RawReport]


class ParsedBatch(Model):
    run_id: str
    reports: List[ParsedReport]


class VerifiedRequest(Model):
    id: str
    merged_ids: List[str]
    village: str
    district: str
    state: str
    lat: float
    lon: float
    timestamp: str
    needs: List[str]
    people: int
    urgency: int
    confidence: float
    status: str  # valid | merged | conflict
    notes: List[str]
    priority: str  # high | medium | low
    score: float


class VerifiedBatch(Model):
    run_id: str
    requests: List[VerifiedRequest]
    report_status: Dict[str, str]
    merge_log: List[str]


class SupplyAllocation(Model):
    request_id: str
    food: int = 0
    water: int = 0
    medicines: int = 0
    volunteers: int = 0
    shortages: Dict[str, int] = {}


class Vehicle(Model):
    id: str
    type: str
    station: str
    team: str
    modes: List[str]


class AllocationBatch(Model):
    run_id: str
    requests: List[VerifiedRequest]
    allocations: List[SupplyAllocation]
    fleet: List[Vehicle]
    blocked: List[str] = []


class RouteOption(Model):
    vehicle_id: str
    vehicle_type: str
    mode: str
    path: List[str]
    eta_h: float
    distance_km: float
    feasible: bool


class RequestRoutes(Model):
    request_id: str
    options: List[RouteOption]


class RoutedBatch(Model):
    run_id: str
    requests: List[VerifiedRequest]
    allocations: List[SupplyAllocation]
    fleet: List[Vehicle]
    routes: List[RequestRoutes]
    blocked: List[str] = []


def dump(m) -> dict:
    """Model -> plain dict (pydantic v1 and v2 safe)."""
    return m.model_dump() if hasattr(m, "model_dump") else m.dict()
