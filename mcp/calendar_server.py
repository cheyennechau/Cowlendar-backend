import asyncio, json
from mcp.server import Server
from mcp.types import Tool, CallToolResult

srv = Server("moo-google-calendar")

@srv.tool(name="get_today_events", description="Return today's Google Calendar events for the signed-in user.")
async def get_today_events_tool() -> CallToolResult:
    # In a real build, load tokens from a known place and call app.calendar_client.get_today_events
    from app.calendar_client import get_today_events
    from app.settings import load_tokens
    events = get_today_events(load_tokens())
    return CallToolResult(content=[{"type": "json", "json": events}])

async def main():
    await srv.run_stdio()

if __name__ == "__main__":
    asyncio.run(main())
