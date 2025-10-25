from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

def build_calendar(tokens: dict):
    creds = Credentials.from_authorized_user_info(tokens, SCOPES)
    return build("calendar", "v3", credentials=creds)

def today_window():
    start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1, seconds=-1)
    return start, end

def get_today_events(tokens: dict):
    cal = build_calendar(tokens)
    start, end = today_window()
    res = cal.events().list(
        calendarId="primary",
        singleEvents=True,
        orderBy="startTime",
        timeMin=start.isoformat() + "Z",
        timeMax=end.isoformat() + "Z",
    ).execute()
    items = res.get("items", [])
    events = []
    for e in items:
        start_ts = e.get("start", {}).get("dateTime")
        end_ts = e.get("end", {}).get("dateTime")
        if not (start_ts and end_ts):  # skip all-day for MVP
            continue
        events.append({
            "id": e["id"],
            "title": e.get("summary", "(no title)"),
            "start": start_ts,
            "end": end_ts
        })
    return events
