import os
from sqlmodel import create_engine
from dotenv import load_dotenv
import os

load_dotenv()  # automatically loads variables from .env in project root

class Settings:
    DB_PATH = os.getenv("DB_PATH", "moo.db")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")

settings = Settings()
engine = create_engine(f"sqlite:///{settings.DB_PATH}")
