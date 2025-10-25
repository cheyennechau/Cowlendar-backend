import asyncio, json
from mcp.server import Server
from mcp.types import Tool, CallToolResult

srv = Server("moo-google-calendar")

@srv.tool(name="get_today_events", description="Return today's Google Calendar events for the signed-in user.")
async def get_today_events_tool() -> CallToolResult:
    try:
        # Load tokens from DB
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        
        from app.calendar_client import get_today_events
        from app.settings import engine
        from app.model import User
        from sqlmodel import Session, select
        
        with Session(engine) as s:
            user = s.exec(select(User)).first()
            if not user or not user.google_tokens:
                return CallToolResult(content=[{"type": "text", "text": "No authenticated user found"}])
            
            events = get_today_events(user.google_tokens)
            return CallToolResult(content=[{"type": "json", "json": events}])
    except Exception as e:
        return CallToolResult(content=[{"type": "text", "text": f"Error: {str(e)}"}])

async def main():
    await srv.run_stdio()

if __name__ == "__main__":
    asyncio.run(main())
