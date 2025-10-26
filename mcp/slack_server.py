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
        # Minimize payload
        channels = []
        for ch in resp.data.get("channels", []):
            channels.append({
                "id": ch.get("id"),
                "name": ch.get("name"),
                "is_channel": ch.get("is_channel"),
                "is_group": ch.get("is_group"),
                "is_im": ch.get("is_im"),
                "is_private": ch.get("is_private"),
            })
        data = {
            "ok": resp.data.get("ok", True),
            "channels": channels,
            "response_metadata": {
                "next_cursor": (resp.data.get("response_metadata") or {}).get("next_cursor")
            }
        }
        return CallToolResult(content=[{"type": "text", "text": json.dumps(data)}])
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
        # Minimize payload and truncate text
        messages = []
        for m in resp.data.get("messages", []):
            text = m.get("text") or ""
            if isinstance(text, str) and len(text) > 1000:
                text = text[:1000]
            messages.append({
                "ts": m.get("ts"),
                "user": m.get("user"),
                "text": text,
                "subtype": m.get("subtype"),
                "thread_ts": m.get("thread_ts"),
            })
        data = {
            "ok": resp.data.get("ok", True),
            "messages": messages,
            "has_more": resp.data.get("has_more"),
            "response_metadata": {
                "next_cursor": (resp.data.get("response_metadata") or {}).get("next_cursor")
            }
        }
        return CallToolResult(content=[{"type": "text", "text": json.dumps(data)}])
    except Exception as e:
        return CallToolResult(content=[{"type": "text", "text": f"Error: {e}"}])
