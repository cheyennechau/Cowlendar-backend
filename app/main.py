from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, Session, select
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from google_auth_oauthlib.flow import Flow
from .brain_mcp import decide_mood_with_mcp
from datetime import date

from .model import User, DaySummary
from .scheduler import start_scheduler
from .settings import settings, engine
from .calendar_client import who_am_i, percent_done_completed_only
from .notion_client import (
    list_databases as notion_list_databases,
    query_database as notion_query_database,
    get_page as notion_get_page,
    append_blocks as notion_append_blocks,
)

# create app
app = FastAPI(title="Moo Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# lifestyle
@app.on_event("startup")
def on_start():
    SQLModel.metadata.create_all(engine)
    start_scheduler()

# routes
@app.get("/auth/whoami")
def auth_whoami():
    with Session(engine) as s:
        user = s.exec(select(User)).first()
        if not user or not user.google_tokens:
            return {"authed": False, "email": None}
        email = who_am_i(user.google_tokens)
        return {"authed": True, "email": email}

@app.get("/debug/calendar")
def debug_calendar():
    """Debug endpoint - shows raw calendar data like test_calendar.py"""
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from datetime import datetime, timedelta
    
    with Session(engine) as s:
        user = s.exec(select(User)).first()
        if not user or not user.google_tokens:
            return {"error": "No authenticated user"}
        
        # Build calendar
        creds = Credentials.from_authorized_user_info(
            user.google_tokens,
            ["https://www.googleapis.com/auth/calendar.readonly"]
        )
        cal = build("calendar", "v3", credentials=creds)
        
        # Get account email
        calendar_info = cal.calendarList().get(calendarId='primary').execute()
        account_email = calendar_info.get('id', 'Unknown')
        
        # Get events for today (timezone-aware)
        now = datetime.now().astimezone()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        
        events_result = cal.events().list(
            calendarId='primary',
            timeMin=start.isoformat(),
            timeMax=end.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        # Format events
        formatted_events = []
        for event in events:
            start_time = event['start'].get('dateTime', event['start'].get('date'))
            formatted_events.append({
                'title': event.get('summary', 'No title'),
                'start': start_time,
                'type': 'Timed' if 'dateTime' in event['start'] else 'All-day'
            })
        
        return {
            "account_email": account_email,
            "events": formatted_events,
            "count": len(formatted_events)
        }

@app.get("/status")
def status():
    from datetime import date
    with Session(engine) as s:
        user = s.exec(select(User)).first()
        if not user:
            return {"authed": False}
        today = s.exec(
            select(DaySummary).where(
                DaySummary.user_id == user.id,
                DaySummary.day == date.today()
            )
        ).first()
        return {
            "authed": user.google_tokens is not None,
            "today": {
                "percent_done": today.percent_done if today else 0,
                "mood": today.mood if today else "low",
                "message": today.message if today else "Let’s start the day 🐮",
                "milk_points": today.milk_points if today else 0,
            },
        }

CLIENT_CONFIG = {
    "installed": {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

@app.get("/auth/google/start")
def google_start():
    flow = Flow.from_client_config(
        CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
    )
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    app.state.oauth_state = state
    return {"auth_url": auth_url}

@app.get("/auth/google/callback")
def google_callback(request: Request, code: str, state: str):
    if state != getattr(app.state, "oauth_state", None):
        raise HTTPException(status_code=400, detail="State mismatch")

    flow = Flow.from_client_config(
        CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
    )
    flow.fetch_token(code=code)

    creds = flow.credentials
    tokens = {
        "token": creds.token,
        "refresh_token": getattr(creds, "refresh_token", None),
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": getattr(creds, "client_secret", None),
        "scopes": list(creds.scopes) if getattr(creds, "scopes", None) else [],
    }

    with Session(engine) as s:
        user = s.exec(select(User)).first()
        if not user:
            user = User(email="me@example.com")
        user.google_tokens = tokens
        s.add(user)
        s.commit()

    return "Google connected. You can close this tab."

class NotionQueryBody(BaseModel):
    database_id: str
    filter: Optional[Dict[str, Any]] = None
    sorts: Optional[List[Dict[str, Any]]] = None
    page_size: int = 25
    start_cursor: Optional[str] = None

class NotionAppendBody(BaseModel):
    block_id: str
    children: List[Dict[str, Any]]

@app.get("/notion/databases")
def api_notion_databases(query: Optional[str] = None, page_size: int = 10):
    return notion_list_databases(query=query, page_size=page_size)

@app.post("/notion/query")
def api_notion_query(body: NotionQueryBody):
    return notion_query_database(
        database_id=body.database_id,
        filter=body.filter,
        sorts=body.sorts,
        page_size=body.page_size,
        start_cursor=body.start_cursor,
    )

@app.get("/notion/page/{page_id}")
def api_notion_get_page(page_id: str):
    return notion_get_page(page_id)

@app.post("/notion/append")
def api_notion_append(body: NotionAppendBody):
    return notion_append_blocks(body.block_id, body.children)

@app.post("/mood/refresh/mcp")
async def refresh_mood_mcp():
    with Session(engine) as s:
        user = s.exec(select(User)).first()
        if not user:
            raise HTTPException(status_code=401, detail="No user found")

        # Get account email for debugging
        account_email = who_am_i(user.google_tokens)
        
        # Get events for debugging
        from .calendar_client import get_today_events
        debug_events = get_today_events(user.google_tokens)
        
        # deterministic % done from finished events only
        pct_today = percent_done_completed_only(user.google_tokens)

        # 2) Recent history (optional context for mood)
        rows = s.exec(
            select(DaySummary)
            .where(DaySummary.user_id == user.id)
            .order_by(DaySummary.day.desc())
            .limit(7)
        ).all()
        hist = [r.percent_done for r in rows[::-1]]

        # MCP decide mood/message (pass history; percent is ours)
        result = await decide_mood_with_mcp(settings.ANTHROPIC_API_KEY, hist)

        # 4) Upsert today's row
        today = date.today()
        row = s.exec(
            select(DaySummary).where(
                DaySummary.user_id == user.id,
                DaySummary.day == today
            )
        ).first()

        if not row:
            row = DaySummary(
                user_id=user.id,
                day=today,
                percent_done=pct_today,
                mood=result["mood"],
                message=result["message"],
                milk_points=pct_today // 10,
            )
            s.add(row)
        else:
            row.percent_done = pct_today
            row.mood = result["mood"]
            row.message = result["message"]
            row.milk_points = pct_today // 10

        s.commit()
        s.refresh(row)
        return {
            "percent_done": row.percent_done,
            "mood": row.mood,
            "message": row.message,
            "milk_points": row.milk_points,
            "debug_account_email": account_email,
            "debug_events": debug_events,
        }