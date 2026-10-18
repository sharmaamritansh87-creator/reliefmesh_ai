"""Intake logic: free-text report -> structured need / headcount / urgency."""
import re
from typing import List

from ..llm import llm_parse_report
from ..models import ParsedReport, RawReport

NEED_ORDER = ["rescue", "evacuation", "medical", "food", "water", "shelter"]
NEED_KEYWORDS = {
    "rescue": ["rescue", "stranded", "stuck", "trapped", "bachao", "uddhar"],
    "evacuation": ["evacuat*", "elderly", "relocate", "nikalna", "shift*"],
    "medical": ["medic*", "medicine*", "doctor", "injur*", "dawai", "davai", "ghayal", "hospital"],
    "food": ["food", "khana", "khaana", "bhat", "ration*", "rice", "hunger", "bhook"],
    "water": ["water", "paani", "pani", "jol", "jal"],
    "shelter": ["shelter", "tent*", "aashray", "ashray", "roof"],
}
URGENT_WORDS = ["urgent", "emergency", "asap", "immediately", "turant", "jaldi", "sos", "tatkal", "please help"]
SEVERITY_PHRASES = ["no food left", "stranded", "injured", "trapped", "collapsed", "bridge damaged",
                    "not accessible", "washed away"]
HINDI_MARKERS = ["hai", "hain", "mein", "me", "log", "chahiye", "nahi", "paani", "khana", "baadh", "aur", "ko"]
ASSAMESE_MARKERS = ["nai", "lagise", "manuh", "bhat", "jol", "bonya", "kotha"]


def _pattern(k: str) -> str:
    return r"\b" + (re.escape(k[:-1]) if k.endswith("*") else re.escape(k) + r"\b")


def detect_language(text: str) -> str:
    words = set(re.findall(r"[a-z]+", text.lower()))
    if len(words & set(ASSAMESE_MARKERS)) >= 2:
        return "as-latn"
    if len(words & set(HINDI_MARKERS)) >= 2:
        return "hi-latn"
    return "en"


def extract_needs(text: str) -> List[str]:
    t = text.lower()
    found = [n for n in NEED_ORDER if any(re.search(_pattern(k), t) for k in NEED_KEYWORDS[n])]
    # "no food left" must not count as a water need etc. -- keywords are per need, so nothing extra to do
    return found


def extract_people(text: str) -> int:
    t = text.lower()
    for pat in (r"(\d{1,5})\s*\+?\s*(?:people|persons|log|logon|families|family|manuh|residents|villagers|injured)",
                r"(?:around|about|approx|lagbhag)\s*(\d{1,5})", r"(\d{1,5})"):
        m = re.search(pat, t)
        if m:
            return int(m.group(1))
    return 10


def estimate_urgency(text: str, needs: List[str], people: int) -> int:
    t = text.lower()
    u = 2
    u += any(w in t for w in URGENT_WORDS)
    u += any(p in t for p in SEVERITY_PHRASES)
    u += bool(needs) and needs[0] in ("rescue", "medical", "evacuation")
    u += people >= 150
    return int(min(5, max(1, u)))


def parse_report(raw: RawReport) -> ParsedReport:
    needs = extract_needs(raw.text)
    people = extract_people(raw.text)
    urgency = estimate_urgency(raw.text, needs, people)
    parser = "rules"
    llm = llm_parse_report(raw.text)
    if llm:
        needs, people, urgency, parser = llm["needs"], llm["people"], llm["urgency"], "llm"
    return ParsedReport(id=raw.id, text=raw.text, village=raw.village, district=raw.district, state=raw.state,
                        lat=raw.lat, lon=raw.lon, timestamp=raw.timestamp, needs=needs, people=people,
                        urgency=urgency, language=detect_language(raw.text), parser=parser)


def parse_batch(reports: List[RawReport]) -> List[ParsedReport]:
    return [parse_report(r) for r in reports]
