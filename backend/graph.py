"""Road / river / air network for the region, built from data/ne_graph.json (NetworkX)."""
import json
import math
import os
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

import networkx as nx

ROOT = Path(__file__).resolve().parents[1]


def data_dir() -> Path:
    """Config folder. Point RELIEF_DATA_DIR at another folder to switch region."""
    return Path(os.getenv("RELIEF_DATA_DIR", ROOT / "data"))


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def load_config(folder: Optional[str] = None) -> dict:
    d = Path(folder) if folder else data_dir()
    cfg = {}
    for name in ("reports", "inventory", "teams", "ne_graph"):
        with open(d / f"{name}.json", encoding="utf-8") as f:
            cfg[name] = json.load(f)
    return cfg


def edge_id(a: str, b: str, mode: str) -> str:
    x, y = sorted([a, b])
    return f"{x}|{y}|{mode}"


def build_edges(graph_cfg: dict) -> List[dict]:
    """Expand config into edge dicts; air edges are generated from base camps (helipads)."""
    nodes = {n["id"]: n for n in graph_cfg["nodes"]}
    speeds = graph_cfg["speeds_kmph"]
    edges: Dict[str, dict] = {}

    def add(a: str, b: str, mode: str, dist: float) -> None:
        eid = edge_id(a, b, mode)
        if eid not in edges:
            edges[eid] = {"id": eid, "a": a, "b": b, "mode": mode,
                          "distance_km": round(dist, 1), "time_h": round(dist / speeds[mode], 2)}

    for e in graph_cfg["edges"]:
        add(e["a"], e["b"], e["mode"], e["distance_km"])
    for hub in graph_cfg.get("air_hubs", []):
        h = nodes[hub]
        for n in nodes.values():
            if n["id"] != hub:
                add(hub, n["id"], "air", haversine(h["lat"], h["lon"], n["lat"], n["lon"]))
    return list(edges.values())


def resolve_block(edges: List[dict], spec: dict) -> List[str]:
    """Turn {"village": X} | {"from": A, "to": B} | {"edge": id} into edge ids (road by default)."""
    mode = spec.get("mode", "road")
    if spec.get("edge"):
        return [spec["edge"]] if any(e["id"] == spec["edge"] for e in edges) else []
    if spec.get("village"):
        v = spec["village"].strip().lower()
        return [e["id"] for e in edges if e["mode"] == mode and v in (e["a"].lower(), e["b"].lower())]
    if spec.get("from") and spec.get("to"):
        pair = {spec["from"].strip().lower(), spec["to"].strip().lower()}
        return [e["id"] for e in edges if e["mode"] == mode and {e["a"].lower(), e["b"].lower()} == pair]
    return []


def find_route(edges: Iterable[dict], blocked: Set[str], src: str, dst: str,
               modes: Iterable[str]) -> Optional[dict]:
    """Fastest path using only allowed modes and unblocked edges. None if unreachable."""
    if src == dst:
        return {"path": [src], "time_h": 0.0, "distance_km": 0.0}
    modes = set(modes)
    g = nx.Graph()
    for e in edges:
        if e["mode"] in modes and e["id"] not in blocked:
            cur = g.get_edge_data(e["a"], e["b"])
            if cur is None or e["time_h"] < cur["time_h"]:
                g.add_edge(e["a"], e["b"], time_h=e["time_h"], distance_km=e["distance_km"])
    if src not in g or dst not in g:
        return None
    try:
        path = nx.shortest_path(g, src, dst, weight="time_h")
    except nx.NetworkXNoPath:
        return None
    legs = list(zip(path, path[1:]))
    return {"path": path,
            "time_h": round(sum(g[u][v]["time_h"] for u, v in legs), 2),
            "distance_km": round(sum(g[u][v]["distance_km"] for u, v in legs), 1)}
