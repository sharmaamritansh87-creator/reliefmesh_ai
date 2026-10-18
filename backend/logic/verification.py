"""Verification logic: dedupe, merge, flag conflicts, score confidence."""
from typing import Dict, List, Tuple

from ..models import ParsedReport, VerifiedRequest
from ..scoring import (confidence_score, headcount_ratio, is_duplicate, parse_ts,
                       priority_label, priority_score)

CONFLICT_RATIO = 0.7  # min/max headcount below this => conflicting reports
MIN_CONFIDENCE = 0.4


def verify(parsed: List[ParsedReport]) -> Tuple[List[VerifiedRequest], Dict[str, str], List[str]]:
    """Returns (verified requests by priority, per-report status, human-readable merge log)."""
    ordered = sorted(parsed, key=lambda r: parse_ts(r.timestamp))
    clusters: List[List[ParsedReport]] = []
    for r in ordered:
        for c in clusters:
            if any(is_duplicate(r, m) for m in c):
                c.append(r)
                break
        else:
            clusters.append([r])

    out: List[VerifiedRequest] = []
    status: Dict[str, str] = {}
    log: List[str] = []
    for c in clusters:
        primary = c[0]
        needs = list(dict.fromkeys(n for r in c for n in r.needs))
        counts = [r.people for r in c]
        people = max(counts)
        ratio = headcount_ratio(counts) if len(c) > 1 else 1.0
        urgency = max(r.urgency for r in c)
        conf = confidence_score(len(c), ratio, bool(needs), len(primary.text))
        notes: List[str] = []
        if len(c) == 1:
            st = "valid"
            status[primary.id] = "valid"
        else:
            st = "merged" if ratio >= CONFLICT_RATIO else "conflict"
            status[primary.id] = "valid" if st == "merged" else "conflict"
            for r in c[1:]:
                status[r.id] = "duplicate" if st == "merged" else "conflict"
            ids = ", ".join(r.id for r in c)
            vals = " vs ".join(str(x) for x in counts)
            if st == "merged":
                notes.append(f"Duplicate reports {ids} merged (headcounts {vals}; using {people}).")
                log.append(f"{ids} -> merged into {primary.id} ({primary.village})")
            else:
                notes.append(f"Conflicting headcounts {vals} in {ids}; using the higher figure, human check advised.")
                log.append(f"{ids} -> CONFLICT at {primary.village} ({vals})")
        if not needs:
            notes.append("No clear need detected.")
        if conf < MIN_CONFIDENCE:
            for r in c:
                status[r.id] = "rejected"
            log.append(f"{primary.id} rejected (confidence {conf})")
            continue
        out.append(VerifiedRequest(
            id=primary.id, merged_ids=[r.id for r in c], village=primary.village, district=primary.district,
            state=primary.state, lat=primary.lat, lon=primary.lon, timestamp=primary.timestamp, needs=needs,
            people=people, urgency=urgency, confidence=conf, status=st, notes=notes,
            priority=priority_label(urgency), score=priority_score(urgency, people, conf)))
    out.sort(key=lambda x: -x.score)
    return out, status, log
