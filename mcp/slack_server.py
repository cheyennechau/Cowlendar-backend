import os, sys, json
from mcp.types import CallToolResult
from slack_sdk import WebClient

# Ensure app package is importable (same pattern as calendar_server)
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app.settings import engine
from app.model import User
from sqlmodel import Session, select


def _get_user_token() -> str:
    with Session(engine) as s:
        user = s.exec(select(User)).first()
        if not user or not user.slack_tokens:
            raise RuntimeError("No Slack authenticated user found")
        token = user.slack_tokens.get("access_token")
        if not token:
            raise RuntimeError("Slack access token missing")
        return token


async def slack_list_conversations(types: str = "public_channel,private_channel,im,mpim", limit: int = 100, cursor: str | None = None) -> CallToolResult:
    try:
        token = _get_user_token()
        client = WebClient(token=token)
        resp = client.conversations_list(types=types, limit=limit, cursor=cursor)
        return CallToolResult(content=[{"type": "text", "text": json.dumps(resp.data)}])
    except Exception as e:
        return CallToolResult(content=[{"type": "text", "text": f"Error: {e}"}])


async def slack_fetch_messages(channel_id: str, oldest_ts: str | None = None, latest_ts: str | None = None, limit: int = 100, cursor: str | None = None) -> CallToolResult:
    try:
        token = _get_user_token()
        client = WebClient(token=token)
        kwargs = {
            "channel": channel_id,
            "limit": limit,
        }
        if cursor:
            kwargs["cursor"] = cursor
        if oldest_ts:
            kwargs["oldest"] = oldest_ts
        if latest_ts:
            kwargs["latest"] = latest_ts
        resp = client.conversations_history(**kwargs)
        return CallToolResult(content=[{"type": "text", "text": json.dumps(resp.data)}])
    except Exception as e:
        return CallToolResult(content=[{"type": "text", "text": f"Error: {e}"}])
