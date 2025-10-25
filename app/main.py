from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, create_engine, Session, select
from .model import User, DaySummary
from .scheduler import start_scheduler
from .settings import settings, engine
from google_auth_oauthlib.flow import Flow

app = FastAPI(title="Moo Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_start():
    SQLModel.metadata.create_all(engine)
    start_scheduler()

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
