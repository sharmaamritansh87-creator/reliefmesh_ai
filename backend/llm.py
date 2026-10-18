"""Optional LLM helpers (ASI:One or any OpenAI-compatible API). Everything falls back to rules."""
import json
import os
import urllib.request
from typing import Optional


def enabled() -> bool:
    return bool(os.getenv("LLM_API_KEY"))


def _chat(system: str, user: str, max_tokens: int = 300) -> Optional[str]:
    if not enabled():
        return None
    base = os.getenv("LLM_BASE_URL", "https://api.asi1.ai/v1").rstrip("/")
    body = json.dumps({"model": os.getenv("LLM_MODEL", "asi1-mini"), "max_tokens": max_tokens,
                       "messages": [{"role": "system", "content": system},
                                    {"role": "user", "content": user}]}).encode()
    req = urllib.request.Request(f"{base}/chat/completions", data=body, headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {os.getenv('LLM_API_KEY')}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def llm_parse_report(text: str) -> Optional[dict]:
    """Return {needs, people, urgency} or None."""
    out = _chat("Extract a disaster report. Reply ONLY with JSON: "
                '{"needs":[subset of food,water,medical,evacuation,rescue,shelter],'
                '"people":int,"urgency":1-5}. The text may be English, Hindi or Assamese in Latin script.', text)
    if not out:
        return None
    try:
        d = json.loads(out[out.index("{"): out.rindex("}") + 1])
        valid = {"food", "water", "medical", "evacuation", "rescue", "shelter"}
        needs = [n for n in d.get("needs", []) if n in valid]
        if not needs:
            return None
        return {"needs": needs, "people": max(1, int(d.get("people", 10))),
                "urgency": min(5, max(1, int(d.get("urgency", 3))))}
    except Exception:
        return None


def llm_explain(summary: str) -> Optional[str]:
    return _chat("You are a disaster-relief coordinator. In 2 plain sentences explain this plan to a "
                 "district officer. Mention that human approval is required.", summary, 150)
