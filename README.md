# 🐮 Cowlendar Backend

Backend API for Cowlendar - a productivity tracker with a mood-changing cow mascot.

## What This Does

Cowlendar tracks your productivity by analyzing your Google Calendar events and (optionally) Notion tasks. A cow mascot changes mood based on how up-to-date you are with your tasks.

### Core Features

- **Google Calendar Integration**: Fetches today's events and tracks completion
- **Claude AI Brain**: Analyzes productivity and generates encouraging messages
- **Mood System**: 3 mood states (great/okay/low) based on completion percentage
- **Background Scheduler**: Auto-updates every 5 minutes
- **Notion Integration**: Query Notion databases for tasks (optional)
- **MCP Support**: Modular tool system for adding AI agents (Fetch AI, etc.)

## Architecture

```
Chrome Extension (frontend)
    ↓ REST API
FastAPI Backend (this repo)
    ├── Simple Mode: Direct calendar → Claude analysis
    └── MCP Mode: Claude calls multiple tools (Calendar, Notion, Fetch AI)
```

### Two Operating Modes

1. **Simple Mode** (default, fast)
   - Background scheduler fetches calendar every 5 minutes
   - Computes completion percentage
   - Claude generates mood + message
   - Used by: `/status` endpoint

2. **MCP Mode** (experimental, flexible)
   - Claude decides which tools to call
   - Can query Calendar, Notion, Fetch AI dynamically
   - Used by: `/mood/refresh/mcp` endpoint

## Project Structure

```
Cowlendar-backend/
├── app/
│   ├── main.py              # FastAPI app, endpoints
│   ├── brain.py             # Simple Claude integration
│   ├── brain_mcp.py         # MCP-powered Claude (multi-tool)
│   ├── calendar_client.py   # Google Calendar API wrapper
│   ├── notion_client.py     # Notion API wrapper
│   ├── scheduler.py         # Background job (runs every 5 min)
│   ├── model.py             # Database models (User, DaySummary)
│   └── settings.py          # Config and DB engine
├── mcp/
│   ├── calendar_server.py   # MCP server for Google Calendar
│   ├── notion_server.py     # MCP server for Notion
│   └── fetch_ai_server.py   # MCP server for Fetch AI (placeholder)
├── requirements.txt
├── .env.sample             # Environment variables template
└── moo.db                  # SQLite database (auto-created)
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.sample` to `.env` and fill in your credentials:

```bash
cp .env.sample .env
```

Required variables:
- `ANTHROPIC_API_KEY`: Get from https://console.anthropic.com/
- `GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_SECRET`: Get from Google Cloud Console (see below)

Optional:
- `NOTION_API_KEY`: For Notion integration
- `FETCH_AI_KEY`: For Fetch AI integration (future)

### 3. Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable **Google Calendar API**
4. Go to **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**
5. Application type: **Web application**
6. Authorized redirect URIs: `http://localhost:8000/auth/google/callback`
7. Copy Client ID and Client Secret to `.env`

### 4. Notion Setup (Optional)

1. Go to https://www.notion.so/my-integrations
2. Create a new integration
3. Copy the Internal Integration Token to `.env` as `NOTION_API_KEY`
4. Share your Notion databases with the integration

## Running the Backend

### Start the Server

```bash
uvicorn app.main:app --reload --port 8000
```

Server will start at `http://localhost:8000`

### Verify It's Running

```bash
curl http://localhost:8000/status
```

Expected response:
```json
{
  "authed": false,
  "today": {
    "percent_done": 0,
    "mood": "low",
    "message": "Let's start the day 🐮",
    "milk_points": 0
  }
}
```

## Testing the API

### 1. Authenticate with Google

**Step 1**: Get auth URL
```bash
curl http://localhost:8000/auth/google/start
```

**Step 2**: Open the `auth_url` in your browser and authorize

**Step 3**: You'll be redirected to `/auth/google/callback` and see "Google connected"

**Step 4**: Verify authentication
```bash
curl http://localhost:8000/status
```

Should now show `"authed": true`

### 2. Wait for Background Scheduler

The scheduler runs every 5 minutes. After ~5 minutes, check status again:

```bash
curl http://localhost:8000/status
```

You should see updated `percent_done`, `mood`, and `message` based on your calendar events.

### 3. Test MCP Mode (Optional)

Trigger an on-demand MCP-powered analysis:

```bash
curl -X POST http://localhost:8000/mood/refresh/mcp
```

This lets Claude call multiple tools (Calendar, Notion, Fetch AI) and synthesize the data.

### 4. Test Notion Integration (Optional)

**List databases**:
```bash
curl "http://localhost:8000/notion/databases?page_size=5"
```

**Query a database**:
```bash
curl -X POST http://localhost:8000/notion/query \
  -H "Content-Type: application/json" \
  -d '{
    "database_id": "your_database_id_here",
    "page_size": 10
  }'
```

## API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/status` | Get current auth status and today's mood/stats |
| `GET` | `/auth/google/start` | Start Google OAuth flow |
| `GET` | `/auth/google/callback` | OAuth callback (redirect) |
| `POST` | `/mood/refresh/mcp` | Trigger MCP-powered mood analysis |

### Notion Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/notion/databases` | List accessible Notion databases |
| `POST` | `/notion/query` | Query a Notion database |
| `GET` | `/notion/page/{page_id}` | Get a Notion page |
| `POST` | `/notion/append` | Append blocks to a Notion page |

## Database Schema

### User Table
```python
id: int (primary key)
email: str
google_tokens: dict (JSON)  # OAuth tokens
```

### DaySummary Table
```python
id: int (primary key)
user_id: int
day: date
total_events: int
completed_events: int
percent_done: int (0-100)
mood: str ("great", "okay", "low")
message: str (encouraging message from Claude)
milk_points: int (gamification)
created_at: datetime
```

## How It Works

### Simple Mode Flow (Default)

1. **Background Scheduler** (every 5 min):
   - Fetch today's Google Calendar events
   - Mark events as done if `end_time < now`
   - Compute `percent_done = completed / total * 100`
   - Get last 7 days of history from DB

2. **Claude Analysis** (`app/brain.py`):
   - Send prompt with events count, percent, history
   - Claude returns `{mood, message}`
   - Mood mapping: ≥80% = "great", 50-79% = "okay", <50% = "low"

3. **Save to DB**:
   - Upsert `DaySummary` for today
   - Calculate `milk_points = percent_done // 10`

4. **Extension Polls** `/status`:
   - Gets latest mood/percent/message
   - Updates cow UI

### MCP Mode Flow (Experimental)

1. **Extension calls** `POST /mood/refresh/mcp`

2. **Claude with Tools** (`app/brain_mcp.py`):
   - Claude receives prompt: "Analyze my productivity"
   - Claude decides to call tools:
     - `get_calendar_events` → fetches today's events
     - `query_notion` → (optional) fetches Notion tasks
     - `fetch_ai_query` → (optional) gets AI insights
   - Multi-turn conversation until Claude has enough data

3. **Claude Synthesizes**:
   - Analyzes all tool results
   - Returns `{percent_done, mood, message}`

4. **Save to DB** and return to extension

## MCP Servers

MCP (Model Context Protocol) servers expose tools that Claude can call.

### Running MCP Servers Standalone

**Calendar Server**:
```bash
python -m mcp.calendar_server
```

**Notion Server**:
```bash
python -m mcp.notion_server
```

**Fetch AI Server** (placeholder):
```bash
python -m mcp.fetch_ai_server
```

### Adding New Tools

1. Create `mcp/your_tool_server.py`:
```python
from mcp.server import Server
from mcp.types import CallToolResult

srv = Server("your-tool-name")

@srv.tool(name="your_tool", description="What it does")
async def your_tool_function(param: str) -> CallToolResult:
    # Your logic
    result = {"data": "..."}
    return CallToolResult(content=[{"type": "json", "json": result}])
```

2. Add tool to `app/brain_mcp.py` in `TOOLS` list

3. Add routing in `call_tool()` function

## Troubleshooting

### "No authenticated user found"
- Run the Google OAuth flow: `GET /auth/google/start`
- Make sure you completed the authorization in your browser

### "ANTHROPIC_API_KEY not set"
- Check `.env` file exists and has `ANTHROPIC_API_KEY=...`
- Restart the server after editing `.env`

### Scheduler not updating
- Check server logs for errors
- Verify Google tokens are valid (re-authenticate if needed)
- Scheduler runs every 5 minutes - be patient

### MCP endpoint errors
- MCP mode is experimental
- Check that all MCP servers can import properly
- Look for detailed error messages in response

## Development

### Run in development mode
```bash
uvicorn app.main:app --reload --port 8000
```

### View logs
Server logs will show:
- Scheduler ticks every 5 minutes
- API requests
- Claude API calls
- Errors

### Database inspection
```bash
sqlite3 moo.db
.tables
SELECT * FROM user;
SELECT * FROM daysummary ORDER BY day DESC LIMIT 7;
```

## Next Steps

### For Chrome Extension
- Poll `GET /status` every N minutes
- Display cow based on `mood` field
- Show `message` and `percent_done`
- Add "Refresh" button → calls `POST /mood/refresh/mcp`

### Future Enhancements
- [ ] Discrete mood states (0/20/40/60/80/100 instead of 3 states)
- [ ] Notion task completion tracking
- [ ] Fetch AI integration (replace placeholder)
- [ ] Weekly/monthly summaries
- [ ] Streaks and achievements
- [ ] Multi-user support

## Tech Stack

- **FastAPI**: Web framework
- **SQLModel**: ORM (SQLite database)
- **Anthropic SDK**: Claude AI integration
- **Google Calendar API**: Event fetching
- **Notion SDK**: Task management
- **APScheduler**: Background jobs
- **MCP**: Model Context Protocol for tool calling

## License

MIT (or your preferred license)

## Contributing

This is a hackathon project. Feel free to fork and extend!

---

**Made with 🐮 for productivity tracking**