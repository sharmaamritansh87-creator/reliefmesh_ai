"""Resource logic: allocate consumables and volunteers by priority; surface shortages."""
import math
from typing import Dict, List, Tuple

from ..models import SupplyAllocation, Vehicle, VerifiedRequest


def fleet_from_inventory(inv: dict) -> List[Vehicle]:
    return [Vehicle(**v) for v in inv["vehicles"]]


def allocate(requests: List[VerifiedRequest], inv: dict) -> Tuple[List[SupplyAllocation], Dict[str, int]]:
    left = {"food_packets": inv["supplies"]["food_packets"], "medicines": inv["supplies"]["medicines"],
            "water_bottles": inv["supplies"]["water_bottles"], "volunteers": inv["volunteers"]}
    ratio = inv["ratios"]
    out: List[SupplyAllocation] = []
    for req in sorted(requests, key=lambda r: -r.score):
        want = {
            "food": math.ceil(req.people * ratio["food_per_person"]) if "food" in req.needs else 0,
            "water": math.ceil(req.people * ratio["water_per_person"]) if "water" in req.needs else 0,
            "medicines": math.ceil(req.people * ratio["medicines_per_person"]) if "medical" in req.needs else 0,
            "volunteers": min(ratio["max_volunteers_per_site"],
                              max(1, math.ceil(req.people / ratio["people_per_volunteer"]))),
        }
        pool = {"food": "food_packets", "water": "water_bottles", "medicines": "medicines", "volunteers": "volunteers"}
        give, short = {}, {}
        for k, w in want.items():
            g = min(w, left[pool[k]])
            left[pool[k]] -= g
            give[k] = g
            if w - g > 0:
                short[k] = w - g
        out.append(SupplyAllocation(request_id=req.id, shortages=short, **give))
    return out, left
