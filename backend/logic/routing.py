"""Routing logic: per request, the fastest feasible route for every vehicle (blocked edges respected)."""
from typing import List, Set

from ..graph import find_route
from ..models import RequestRoutes, RouteOption, Vehicle, VerifiedRequest


def route_options(requests: List[VerifiedRequest], fleet: List[Vehicle], edges: List[dict],
                  blocked: Set[str]) -> List[RequestRoutes]:
    result = []
    for req in requests:
        opts = []
        for v in fleet:
            r = find_route(edges, blocked, v.station, req.village, v.modes)
            if r:
                opts.append(RouteOption(vehicle_id=v.id, vehicle_type=v.type, mode=v.modes[0], path=r["path"],
                                        eta_h=r["time_h"], distance_km=r["distance_km"], feasible=True))
            else:
                opts.append(RouteOption(vehicle_id=v.id, vehicle_type=v.type, mode=v.modes[0], path=[],
                                        eta_h=0.0, distance_km=0.0, feasible=False))
        result.append(RequestRoutes(request_id=req.id, options=opts))
    return result
