"""
MCP-powered brain that lets Claude call multiple tools.
Simplified embedded approach for hackathon speed.
"""
from anthropic import Anthropic
from typing import Dict, Any, List
import json
import importlib.util

# Import MCP tool functions directly (embedded approach)
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

async def get_calendar_events():
    """Wrapper for calendar MCP tool"""
    from mcp.calendar_server import get_today_events_tool
    result = await get_today_events_tool()
    return result.content[0].get("json", [])

async def query_notion(database_id: str, filter_json: str = ""):
    """Wrapper for Notion MCP tool"""
    from mcp.notion_server import notion_query_database
    result = await notion_query_database(database_id, filter_json)
    return result.content[0].get("json", {})

async def fetch_ai_query(query: str):
    """Wrapper for Fetch AI MCP tool"""
    from mcp.fetch_ai_server import fetch_ai_query_tool
    result = await fetch_ai_query_tool(query)
    return result.content[0].get("json", {})

async def slack_list_conversations(types: str = "public_channel,private_channel,im,mpim", limit: int = 100, cursor: str | None = None):
    base = os.path.join(os.path.dirname(os.path.dirname(__file__)), "mcp", "slack_server.py")
    spec = importlib.util.spec_from_file_location("local_mcp_slack_server", base)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    result = await mod.slack_list_conversations(types, limit, cursor)
    # Extract JSON payload robustly
    blocks = getattr(result, "content", [])
    if blocks:
        b = blocks[0]
        if isinstance(b, dict):
            if "json" in b:
                return b.get("json", {})
            if "text" in b:
                try:
                    return json.loads(b["text"])  # server returned JSON as text
                except Exception:
                    return {"text": b["text"]}
            return {}
        # Pydantic content block (avoid BaseModel.json() name collision)
        if hasattr(b, "model_dump"):
            bd = b.model_dump()
            if getattr(b, "type", None) == "json":
                return bd.get("json", {})
            if getattr(b, "type", None) == "text":
                txt = bd.get("text", "")
                try:
                    return json.loads(txt)
                except Exception:
                    return {"text": txt}
        if hasattr(b, "text"):
            txt = getattr(b, "text")
            try:
                return json.loads(txt)
            except Exception:
                return {"text": txt}
    return {}

async def slack_fetch_messages(channel_id: str, oldest_ts: str | None = None, latest_ts: str | None = None, limit: int = 100, cursor: str | None = None):
    base = os.path.join(os.path.dirname(os.path.dirname(__file__)), "mcp", "slack_server.py")
    spec = importlib.util.spec_from_file_location("local_mcp_slack_server", base)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    result = await mod.slack_fetch_messages(channel_id, oldest_ts, latest_ts, limit, cursor)
    blocks = getattr(result, "content", [])
    if blocks:
        b = blocks[0]
        if isinstance(b, dict):
            if "json" in b:
                return b.get("json", {})
            if "text" in b:
                try:
                    return json.loads(b["text"])  # server returned JSON as text
                except Exception:
                    return {"text": b["text"]}
            return {}
        if hasattr(b, "model_dump"):
            bd = b.model_dump()
            if getattr(b, "type", None) == "json":
                return bd.get("json", {})
            if getattr(b, "type", None) == "text":
                txt = bd.get("text", "")
                try:
                    return json.loads(txt)
                except Exception:
                    return {"text": txt}
        if hasattr(b, "text"):
            txt = getattr(b, "text")
            try:
                return json.loads(txt)
            except Exception:
                return {"text": txt}
    return {}

# Tool definitions for Claude
TOOLS = [
    {
        "name": "get_calendar_events",
        "description": "Fetch today's Google Calendar events with completion status",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "query_notion",
        "description": "Query Notion database for tasks. Provide database_id and optional filter_json",
        "input_schema": {
            "type": "object",
            "properties": {
                "database_id": {
                    "type": "string",
                    "description": "Notion database ID"
                },
                "filter_json": {
                    "type": "string",
                    "description": "JSON string for Notion API filter (optional)"
                }
            },
            "required": ["database_id"]
        }
    },
    {
        "name": "fetch_ai_query",
        "description": "Query Fetch AI agent for productivity insights",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Query to send to Fetch AI"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "slack_list_conversations",
        "description": "List Slack conversations accessible by the authenticated user",
        "input_schema": {
            "type": "object",
            "properties": {
                "types": {"type": "string", "description": "Comma-separated types: public_channel,private_channel,im,mpim"},
                "limit": {"type": "integer"},
                "cursor": {"type": "string"}
            },
            "required": []
        }
    },
    {
        "name": "slack_fetch_messages",
        "description": "Fetch recent messages from a Slack conversation",
        "input_schema": {
            "type": "object",
            "properties": {
                "channel_id": {"type": "string"},
                "oldest_ts": {"type": "string"},
                "latest_ts": {"type": "string"},
                "limit": {"type": "integer"},
                "cursor": {"type": "string"}
            },
            "required": ["channel_id"]
        }
    }
]

async def call_tool(tool_name: str, tool_input: Dict[str, Any]) -> Any:
    """Route tool calls to appropriate MCP functions"""
    if tool_name == "get_calendar_events":
        return await get_calendar_events()
    elif tool_name == "query_notion":
        return await query_notion(
            tool_input.get("database_id", ""),
            tool_input.get("filter_json", "")
        )
    elif tool_name == "fetch_ai_query":
        return await fetch_ai_query(tool_input.get("query", ""))
    elif tool_name == "slack_list_conversations":
        return await slack_list_conversations(
            tool_input.get("types", "public_channel,private_channel,im,mpim"),
            tool_input.get("limit", 100),
            tool_input.get("cursor")
        )
    elif tool_name == "slack_fetch_messages":
        return await slack_fetch_messages(
            tool_input.get("channel_id", ""),
            tool_input.get("oldest_ts"),
            tool_input.get("latest_ts"),
            tool_input.get("limit", 100),
            tool_input.get("cursor")
        )
    else:
        raise ValueError(f"Unknown tool: {tool_name}")

async def decide_mood_with_mcp(api_key: str, history_percent: List[int]) -> Dict[str, Any]:
    """
    Use Claude with MCP tools to analyze productivity.
    Claude decides which tools to call and synthesizes the data.
    """
    client = Anthropic(api_key=api_key)
    
    # Initial prompt
    messages = [{
        "role": "user",
        "content": f"""You are the Cow's Brain in a productivity game.

Analyze the user's productivity today by:
1. Fetching their calendar events
2. Optionally querying Notion for tasks (if you think it's helpful)
3. Optionally using Fetch AI for insights

Based on the data, determine:
- percent_done: 0-100 (percentage of completed events/tasks)
- mood: "great" (80-100%), "okay" (50-79%), or "low" (0-49%)
- message: Short encouraging message (max 120 chars) in cute cow tone

Recent history: {history_percent[-7:]}

Return ONLY valid JSON: {{"percent_done": <int>, "mood": "<string>", "message": "<string>"}}
"""
    }]
    
    # Multi-turn loop: let Claude call tools
    max_turns = 10  # Safety limit
    for turn in range(max_turns):
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=4096,
            messages=messages,
            tools=TOOLS
        )
        
        # Check if Claude is done
        if response.stop_reason == "end_turn":
            # Extract final answer from text content
            for block in response.content:
                if block.type == "text":
                    try:
                        data = json.loads(block.text)
                        return data
                    except json.JSONDecodeError:
                        # Try to extract JSON from text
                        import re
                        json_match = re.search(r'\{.*\}', block.text, re.DOTALL)
                        if json_match:
                            data = json.loads(json_match.group())
                            return data
            
            # Fallback if no valid JSON
            return {
                "percent_done": 0,
                "mood": "low",
                "message": "Unable to analyze productivity 🐮"
            }
        
        # Claude wants to use tools
        if response.stop_reason == "tool_use":
            # Add assistant's response to messages
            messages.append({"role": "assistant", "content": response.content})
            
            # Process tool calls
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    try:
                        # Call the tool
                        result = await call_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result)
                        })
                    except Exception as e:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"Error: {str(e)}",
                            "is_error": True
                        })
            
            # Add tool results to messages
            messages.append({"role": "user", "content": tool_results})
        else:
            # Unexpected stop reason
            break
    
    # Fallback if max turns reached
    return {
        "percent_done": 0,
        "mood": "low",
        "message": "Analysis took too long 🐮"
    }

async def summarize_slack_with_mcp(api_key: str, hours: int = 24, max_channels: int = 5, messages_per_channel: int = 100) -> Dict[str, Any]:
    """
    Use Claude with Slack tools to read recent messages and produce summaries and suggestions.
    """
    client = Anthropic(api_key=api_key)

    messages = [{
        "role": "user",
        "content": f"""
You are the Cow Assistant.

Goal: Read recent Slack conversations and produce concise summaries and actionable suggestions.

Instructions:
- Use slack_list_conversations to discover channels/DMs the user can access.
- Select up to {max_channels} conversations that look most relevant (active recently, work-related names).
- For each, use slack_fetch_messages to fetch up to {messages_per_channel} recent messages (default recency is OK). Prefer last {hours} hours if possible.

Output only valid JSON with this schema:
{
  "channels": [
    {
      "id": "string",
      "name": "string",
      "summary": "short summary of recent discussion",
      "key_points": ["point1", "point2"],
      "action_items": ["action1", "action2"]
    }
  ],
  "overall_insights": ["insight1", "insight2"],
  "suggestions": ["next-step suggestion 1", "suggestion 2"]
}
"""
    }]

    max_turns = 10
    for _ in range(max_turns):
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=4096,
            messages=messages,
            tools=TOOLS
        )

        if response.stop_reason == "end_turn":
            for block in response.content:
                if block.type == "text":
                    try:
                        data = json.loads(block.text)
                        return data
                    except json.JSONDecodeError:
                        import re
                        m = re.search(r'\{.*\}', block.text, re.DOTALL)
                        if m:
                            return json.loads(m.group())
            return {"channels": [], "overall_insights": [], "suggestions": []}

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    try:
                        result = await call_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result)
                        })
                    except Exception as e:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"Error: {str(e)}",
                            "is_error": True
                        })
            messages.append({"role": "user", "content": tool_results})
        else:
            break

    return {"channels": [], "overall_insights": [], "suggestions": []}
