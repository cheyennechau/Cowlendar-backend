from datetime import datetime, date
from typing import Optional, List
from sqlmodel import SQLModel, Field, JSON

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str
    google_tokens: Optional[dict] = Field(default=None, sa_column_kwargs={"type_": JSON})

class DaySummary(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int
    day: date
    total_events: int
    completed_events: int
    percent_done: int
    mood: str                   # "great" | "okay" | "low"
    message: str
    milk_points: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
