from anthropic import Anthropic
from datetime import datetime

def decide_mood_and_message(api_key: str, events, history_percent: list[int]):
    client = Anthropic(api_key=api_key)
    now = datetime.now().isoformat(timespec="minutes")

    prompt = f"""
You are the Cow's Brain in a productivity game.
Given today's events and history of completion percentages, output:
- mood: "great" (>=80%), "okay" (50–79%), or "low" (<50%)
- short encouraging message (max 120 chars), cute cow tone.
Do not include extra words. Return strict JSON with keys: mood, message.
Now: {now}
Events today: {len(events)} items.
"""

    # simple % calculation here; Claude crafts message + confirms mood category
    done = sum(1 for e in events if e.get("_done", False))
    percent = round(100 * done / len(events)) if events else 0

    system = "You return only valid minified JSON."
    user = prompt + f"\nComputed percent_done={percent}.\nHistory={history_percent[-7:]}"
    msg = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=200,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    # naive parse
    import json
    data = json.loads(msg.content[0].text)
    return data["mood"], data["message"], percent
