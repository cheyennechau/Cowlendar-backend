from datetime import datetime, timedelta
from typing import Dict, Any
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from sqlmodel import select

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

def build_calendar(tokens: dict):
    creds = Credentials.from_authorized_user_info(tokens, SCOPES)
    return build("calendar", "v3", credentials=creds)

def today_window():
    # Use timezone-aware datetime to match local calendar view
    now = datetime.now().astimezone()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1, seconds=-1)
    return start, end

def get_today_events(tokens: dict):
    cal = build_calendar(tokens)
    start, end = today_window()
    res = cal.events().list(
        calendarId="primary",
        singleEvents=True,
        orderBy="startTime",
        timeMin=start.isoformat(),  # Already has timezone, don't add 'Z'
        timeMax=end.isoformat(),    # Already has timezone, don't add 'Z'
    ).execute()
    items = res.get("items", [])
    events = []
    for e in items:
        start_ts = e.get("start", {}).get("dateTime")
        end_ts = e.get("end", {}).get("dateTime")
        if not (start_ts and end_ts): # skip all-day for MVP
            continue
        events.append({
            "id": e["id"],
            "title": e.get("summary", "(no title)"),
            "start": start_ts,
            "end": end_ts
        })

    print(f"Fetched {len(events)} events from Google Calendar:")
    for e in events:
        print(" -", e["title"], e["start"], "→", e["end"])

    return events

def who_am_i(tokens: dict) -> str:
    """
    Returns the user's email (the primary calendar ID) using the Calendar API.
    """
    cal = build_calendar(tokens)
    me = cal.calendars().get(calendarId="primary").execute()
    return me.get("id") or me.get("summary") or ""

def get_past_events_today(tokens: dict):
    """
    Returns all timed events from today that have already ended.
    These are the events the user should be asked about.
    """
    cal = build_calendar(tokens)
    now = datetime.now().astimezone()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    res = cal.events().list(
        calendarId="primary",
        singleEvents=True,
        orderBy="startTime",
        timeMin=start.isoformat(),
        timeMax=end.isoformat(),
    ).execute()

    def parse(ts: str) -> datetime:
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return datetime.fromisoformat(ts).astimezone(now.tzinfo)

    past_events = []
    for e in res.get("items", []):
        sdt = e.get("start", {}).get("dateTime")
        edt = e.get("end", {}).get("dateTime")
        if not (sdt and edt):  # skip all-day
            continue

        ev_end = parse(edt)
        if ev_end <= now:  # event has ended
            past_events.append({
                "id": e["id"],
                "title": e.get("summary", "(no title)"),
                "start": sdt,
                "end": edt,
            })

    return past_events

def percent_done_completed_only(tokens: Dict[str, Any]) -> int:
    """
    % of today's scheduled (timed) event duration that has fully completed.
    - Skips all-day events (no 'dateTime').
    - Ignores partial/ongoing events.
    - Uses local timezone day window.
    """
    cal = build_calendar(tokens)
    now = datetime.now().astimezone()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    res = cal.events().list(
        calendarId="primary",
        singleEvents=True,
        orderBy="startTime",
        timeMin=start.isoformat(), # tz-aware RFC3339
        timeMax=end.isoformat(),
    ).execute()

    def parse(ts: str) -> datetime:
        # handle trailing 'Z' and offsets
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return datetime.fromisoformat(ts).astimezone(now.tzinfo)

    total_secs = 0.0
    done_secs = 0.0

    for e in res.get("items", []):
        sdt = e.get("start", {}).get("dateTime")
        edt = e.get("end", {}).get("dateTime")
        if not (sdt and edt): # skip all-day
            continue

        ev_start = parse(sdt)
        ev_end   = parse(edt)
        if ev_end <= ev_start:
            continue # malformed

        dur = (ev_end - ev_start).total_seconds()
        total_secs += dur

        if ev_end <= now:
            # count only fully finished events
            done_secs += dur

    if total_secs <= 0:
        return 0
    pct = int(round(100 * done_secs / total_secs))
    return max(0, min(100, pct))

def percent_done_from_user_input(user_id: int, tokens: dict, session) -> int:
    """
    Calculate completion % based on user's manual yes/no responses.
    Returns percentage of past events that user marked as completed.
    """
    from datetime import date
    from .model import EventCompletion
    
    # Get all past events from calendar
    past_events = get_past_events_today(tokens)
    
    if not past_events:
        return 0
    
    total_count = len(past_events)
    completed_count = 0
    
    # Check how many the user marked as completed
    today = date.today()
    for event in past_events:
        completion = session.exec(
            select(EventCompletion).where(
                EventCompletion.user_id == user_id,
                EventCompletion.event_id == event["id"],
                EventCompletion.day == today
            )
        ).first()
        
        if completion and completion.completed:
            completed_count += 1
    
    pct = int(round(100 * completed_count / total_count))
    return max(0, min(100, pct))
