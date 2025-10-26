from __future__ import annotations
from anthropic import Anthropic, NotFoundError
from datetime import datetime
from typing import Iterable, Tuple
import json, os, re

DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620")

def _percent_done(events: Iterable[dict]) -> int:
    total = 0
    done = 0
    for e in events:
        total += 1
        if e.get("_done", False):
            done += 1
    return round(100 * done / total) if total else 0

def _fallback_message(pct: int) -> Tuple[str, str]:
    if pct >= 80:
        return "great", "Udderly amazing momentum! 🐮✨"
    if pct >= 50:
        return "okay", "Keep grazing—you're over halfway! 🐄"
    return "low", "Small sips add up. One task now! 🥛"

def _parse_json(text: str) -> dict | None:
    # Try strict first
    try:
        return json.loads(text)
    except Exception:
        pass
    # Then try to extract the first {...} block
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None

def decide_mood_and_message(
    api_key: str,
    events: Iterable[dict],
    history_percent: list[int],
    model: str = DEFAULT_MODEL,
) -> Tuple[str, str, int]:
    """
    Returns (mood, message, percent_done).
    mood ∈ {"great","okay","low"}; message ≤ 120 chars.
    """
    percent = _percent_done(events)

    # Offline/failed-key fallback
    if not api_key:
        mood, msg = _fallback_message(percent)
        return mood, msg, percent

    client = Anthropic(api_key=api_key)

    system = (
        'Return ONLY compact JSON like {"mood":"great|okay|low","message":"<<=120 chars>"}'
    )
    user = (
        "You are a cheerful cow productivity coach.\n"
        f"Today percent_done: {percent}.\n"
        f"Recent history (old→new): {history_percent[-7:]}\n"
        "Rules:\n"
        '- Mood: "great" (>=80), "okay" (50–79), "low" (<50).\n'
        "- Message: upbeat, cow-themed, <=120 chars, no quotes escaping issues.\n"
        "Output JSON only."
    )

    try:
        resp = client.messages.create(
            model=model,
            max_tokens=150,
            temperature=0.3,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        raw = resp.content[0].text if resp.content else "{}"
        data = _parse_json(raw) or {}
        mood = (data.get("mood") or "").strip().lower()
        msg = (data.get("message") or "").strip()

        if mood not in {"great", "okay", "low"}:
            mood, msg = _fallback_message(percent)

        if len(msg) > 120:
            msg = msg[:117] + "..."

        return mood, msg or _fallback_message(percent)[1], percent

    except NotFoundError:
        # model name not available to this key → try a known-good fallback once
        if model != "claude-3-haiku-20240307":
            return decide_mood_and_message(api_key, events, history_percent, "claude-3-haiku-20240307")
        mood, msg = _fallback_message(percent)
        return mood, msg, percent
    except Exception as e:
        # Any network/JSON error → graceful fallback
        print("Claude error:", repr(e))
        mood, msg = _fallback_message(percent)
        return mood, msg, percent