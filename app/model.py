# app/model.py
from datetime import datetime, date
from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import Column
from sqlalchemy.types import JSON  # <-- from SQLAlchemy, not sqlmodel

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str
    google_tokens: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON)   # <-- this is the key line
    )

class DaySummary(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int
    day: date
    total_events: int = 0
    completed_events: int = 0
    percent_done: int = 0
    mood: str = "low"
    message: str = "Let’s start the day 🐮"
    milk_points: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
