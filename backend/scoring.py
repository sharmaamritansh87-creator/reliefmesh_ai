"""Duplicate detection, confidence and priority scoring."""
from datetime import datetime
from difflib import SequenceMatcher

from .graph import haversine


def parse_ts(s: str) -> datetime:
    try:
        return datetime.fromisoformat(s)
    except (TypeError, ValueError):
        return datetime(2026, 1, 1)


def name_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def is_duplicate(a, b, radius_km: float = 3.0, window_min: float = 120.0) -> bool:
    """Same place (fuzzy name OR within radius) + overlapping need + inside the time window."""
    same_place = (name_similarity(a.village, b.village) >= 0.85
                  or haversine(a.lat, a.lon, b.lat, b.lon) <= radius_km)
    if not same_place:
        return False
    minutes = abs((parse_ts(a.timestamp) - parse_ts(b.timestamp)).total_seconds()) / 60
    return minutes <= window_min and bool(set(a.needs) & set(b.needs))


def headcount_ratio(counts) -> float:
    counts = [c for c in counts if c > 0]
    return (min(counts) / max(counts)) if counts else 1.0


def confidence_score(n_reports: int, ratio: float, has_needs: bool, text_len: int) -> float:
    score = 0.55 + min(0.2, 0.1 * (n_reports - 1))
    if text_len >= 20:
        score += 0.1
    if not has_needs:
        score -= 0.3
    if ratio < 0.7:
        score -= 0.2
    return round(max(0.0, min(1.0, score)), 2)


def priority_label(urgency: int) -> str:
    return "high" if urgency >= 4 else "medium" if urgency == 3 else "low"


def priority_score(urgency: int, people: int, confidence: float) -> float:
    """Urgency dominates; headcount and confidence break ties."""
    return round(urgency * 100 + min(people, 1000) / 10 + confidence * 5, 2)
