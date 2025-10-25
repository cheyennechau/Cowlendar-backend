# Current State of Cowlendar Backend

**Last Updated**: October 25, 2025

## ✅ What's Implemented

### Core Backend (Fully Working)

#### 1. FastAPI Server (`app/main.py`)
- ✅ CORS enabled for Chrome extension
- ✅ SQLite database auto-initialization
- ✅ Background scheduler starts on server startup

#### 2. Google Calendar Integration
- ✅ OAuth 2.0 flow (`/auth/google/start`, `/auth/google/callback`)
- ✅ Token storage in database
- ✅ Fetch today's events (`app/calendar_client.py`)
- ✅ Completion tracking (events marked done if `end_time < now`)

#### 3. Claude AI Brain (Simple Mode)
- ✅ `app/brain.py` - Direct Claude integration
- ✅ Computes completion percentage
- ✅ Generates mood (great/okay/low) and encouraging message
- ✅ Uses last 7 days of history for context

#### 4. Background Scheduler
- ✅ Runs every 5 minutes (`app/scheduler.py`)
- ✅ Auto-fetches calendar events
- ✅ Auto-updates mood and saves to database
- ✅ Calculates milk points (gamification)

#### 5. Database Models
- ✅ `User` table (stores email and Google tokens)
- ✅ `DaySummary` table (stores daily mood, percent, message, milk points)
- ✅ SQLite with SQLModel ORM

#### 6. Notion Integration (Optional)
- ✅ `app/notion_client.py` - Notion API wrapper
- ✅ List databases endpoint
- ✅ Query database endpoint
- ✅ Get page endpoint
- ✅ Append blocks endpoint

### MCP Architecture (Experimental, Fully Implemented)

#### 7. MCP Servers
- ✅ `mcp/calendar_server.py` - Google Calendar MCP server (fixed token loading)
- ✅ `mcp/notion_server.py` - Notion MCP server
- ✅ `mcp/fetch_ai_server.py` - Fetch AI MCP server (placeholder, ready for SDK integration)

#### 8. MCP-Powered Brain
- ✅ `app/brain_mcp.py` - Claude with tool calling
- ✅ Multi-turn conversation loop
- ✅ Tool routing (Calendar, Notion, Fetch AI)
- ✅ Embedded approach (no subprocess needed)
- ✅ `/mood/refresh/mcp` endpoint

### Documentation
- ✅ Comprehensive README.md
- ✅ `.env.sample` with all required variables
- ✅ API endpoint documentation
- ✅ Setup instructions
- ✅ Test script (`test_api.py`)

## 📋 API Endpoints Available

### Core
- `GET /status` - Get auth status and today's mood/stats
- `GET /auth/google/start` - Start Google OAuth flow
- `GET /auth/google/callback` - OAuth callback
- `POST /mood/refresh/mcp` - MCP-powered mood analysis

### Notion
- `GET /notion/databases` - List Notion databases
- `POST /notion/query` - Query a Notion database
- `GET /notion/page/{page_id}` - Get a Notion page
- `POST /notion/append` - Append blocks to a page

## 🧪 How to Test

### Quick Start
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create .env file
cp .env.sample .env
# Edit .env with your API keys

# 3. Start server
uvicorn app.main:app --reload --port 8000

# 4. Run test script
python test_api.py
```

### Manual Testing
```bash
# Check status
curl http://localhost:8000/status

# Get Google auth URL
curl http://localhost:8000/auth/google/start
# Open the auth_url in browser and authorize

# Test MCP refresh (after auth)
curl -X POST http://localhost:8000/mood/refresh/mcp

# List Notion databases (if NOTION_API_KEY set)
curl http://localhost:8000/notion/databases
```

## 🎯 What Each File Does

### `app/` Directory

| File | Purpose | Status |
|------|---------|--------|
| `main.py` | FastAPI app, all endpoints | ✅ Working |
| `brain.py` | Simple Claude integration (default) | ✅ Working |
| `brain_mcp.py` | MCP-powered Claude (experimental) | ✅ Working |
| `calendar_client.py` | Google Calendar API wrapper | ✅ Working |
| `notion_client.py` | Notion API wrapper | ✅ Working |
| `scheduler.py` | Background job (every 5 min) | ✅ Working |
| `model.py` | Database models (User, DaySummary) | ✅ Working |
| `settings.py` | Config, env vars, DB engine | ✅ Working |

### `mcp/` Directory

| File | Purpose | Status |
|------|---------|--------|
| `calendar_server.py` | MCP server for Google Calendar | ✅ Fixed |
| `notion_server.py` | MCP server for Notion | ✅ Working |
| `fetch_ai_server.py` | MCP server for Fetch AI | 🟡 Placeholder |

### Root Files

| File | Purpose |
|------|---------|
| `README.md` | Full documentation |
| `.env.sample` | Environment variables template |
| `test_api.py` | API test script |
| `requirements.txt` | Python dependencies |
| `moo.db` | SQLite database (auto-created) |
| `CURRENT_STATE.md` | This file |

## 🔄 How Data Flows

### Simple Mode (Default)
```
Every 5 minutes:
  Background Scheduler
    ↓
  Fetch Google Calendar events (calendar_client.py)
    ↓
  Compute completion % (scheduler.py)
    ↓
  Ask Claude for mood + message (brain.py)
    ↓
  Save to DaySummary table
    ↓
  Extension polls /status to get latest data
```

### MCP Mode (On-Demand)
```
Extension calls POST /mood/refresh/mcp
  ↓
  brain_mcp.py sends prompt to Claude with tools
    ↓
  Claude: "I need to call get_calendar_events"
    ↓
  brain_mcp.py routes to mcp/calendar_server.py
    ↓
  Returns events to Claude
    ↓
  Claude: "I need to call query_notion" (optional)
    ↓
  brain_mcp.py routes to mcp/notion_server.py
    ↓
  Returns tasks to Claude
    ↓
  Claude synthesizes data → {percent, mood, message}
    ↓
  Save to DaySummary table
    ↓
  Return to extension
```

## 🚀 Ready to Use

### What Works Right Now
1. ✅ Start server → auto-creates database
2. ✅ Authenticate with Google → stores tokens
3. ✅ Background scheduler → updates mood every 5 min
4. ✅ `/status` endpoint → returns current mood/percent
5. ✅ `/mood/refresh/mcp` → on-demand MCP analysis
6. ✅ Notion endpoints → query databases and pages

### What You Can Build Next
1. **Chrome Extension**
   - Poll `/status` every N minutes
   - Display cow based on `mood` field
   - Show `message` and `percent_done`
   - "Refresh" button → calls `/mood/refresh/mcp`

2. **Fetch AI Integration**
   - Replace placeholder in `mcp/fetch_ai_server.py`
   - Add Fetch AI SDK calls
   - Claude will automatically use it via MCP

## ⚙️ Configuration Required

### Required Environment Variables
```bash
ANTHROPIC_API_KEY=sk-ant-...        # Get from console.anthropic.com
GOOGLE_CLIENT_ID=...                # Get from Google Cloud Console
GOOGLE_CLIENT_SECRET=...            # Get from Google Cloud Console
```

### Optional Environment Variables
```bash
NOTION_API_KEY=secret_...           # For Notion integration
FETCH_AI_KEY=...                    # For Fetch AI integration
DB_PATH=moo.db                      # SQLite database path
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
```

## 🐛 Known Issues / TODOs

### Minor
- [ ] No `/mood/refresh` endpoint for simple mode (only MCP mode has refresh)
- [ ] Mood states are 3-level (great/okay/low), not 6-level (0/20/40/60/80/100)
- [ ] No `/events/today` endpoint (extension would need to call `/mood/refresh/mcp` to get events)
- [ ] No `/history` endpoint (extension can't see past days)

### Future Enhancements
- [ ] Add discrete mood states (0/20/40/60/80/100)
- [ ] Add `icon_hint` field to `/status` response
- [ ] Integrate Notion tasks into completion percentage
- [ ] Add weekly/monthly summaries
- [ ] Add streaks and achievements
- [ ] Multi-user support

## 📊 Database Schema

### User Table
```sql
CREATE TABLE user (
    id INTEGER PRIMARY KEY,
    email VARCHAR NOT NULL,
    google_tokens JSON  -- {token, refresh_token, token_uri, ...}
);
```

### DaySummary Table
```sql
CREATE TABLE daysummary (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    day DATE NOT NULL,
    total_events INTEGER DEFAULT 0,
    completed_events INTEGER DEFAULT 0,
    percent_done INTEGER DEFAULT 0,
    mood VARCHAR NOT NULL,  -- "great", "okay", "low"
    message VARCHAR NOT NULL,
    milk_points INTEGER DEFAULT 0,
    created_at DATETIME NOT NULL
);
```

## 🎓 Key Concepts

### MCP (Model Context Protocol)
- Standard protocol for AI models to call tools
- Your MCP servers expose tools (get_calendar_events, query_notion, etc.)
- Claude decides which tools to call based on the prompt
- Multi-turn conversation: Claude → tool → Claude → tool → final answer

### Why Two Modes?
1. **Simple Mode** (brain.py)
   - Fast: 1 API call to Claude
   - Predictable: Always fetches same data
   - Used by: Background scheduler

2. **MCP Mode** (brain_mcp.py)
   - Flexible: Claude decides what data to fetch
   - Extensible: Easy to add new tools
   - Used by: `/mood/refresh/mcp` endpoint

### When to Use Each?
- **Simple Mode**: Scheduled background updates (every 5 min)
- **MCP Mode**: On-demand refresh with multiple data sources

## 🔍 Debugging Tips

### Check if server is running
```bash
curl http://localhost:8000/status
```

### Check database
```bash
sqlite3 moo.db
SELECT * FROM user;
SELECT * FROM daysummary ORDER BY day DESC LIMIT 7;
```

### Check logs
Server logs show:
- Scheduler ticks
- API requests
- Claude API calls
- Errors with stack traces

### Common Issues
1. **"No authenticated user"** → Run Google OAuth flow
2. **"ANTHROPIC_API_KEY not set"** → Check .env file
3. **Scheduler not updating** → Wait 5 minutes, check logs
4. **MCP errors** → Check tool imports, look for detailed error in response

## 📝 Summary

**You have a fully functional backend** that:
- ✅ Authenticates with Google Calendar
- ✅ Fetches and tracks event completion
- ✅ Uses Claude AI to generate mood and messages
- ✅ Auto-updates every 5 minutes via background scheduler
- ✅ Supports MCP for multi-tool AI agent workflows
- ✅ Has Notion integration ready
- ✅ Has Fetch AI placeholder ready for your SDK

**Next step**: Build the Chrome extension to poll `/status` and display the cow!
