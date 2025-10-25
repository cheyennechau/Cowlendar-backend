import asyncio, os, json
from dotenv import load_dotenv
from mcp.server import Server
from mcp.types import CallToolResult
from notion_client import Client

load_dotenv()

srv = Server("moo-notion")

def get_client() -> Client:
    token = os.getenv("NOTION_API_KEY", "")
    if not token:
        raise RuntimeError("NOTION_API_KEY not set in environment")
    return Client(auth=token)

@srv.tool(name="notion_list_databases", description="List Notion databases accessible by the integration. Optional query to filter by name.")
async def notion_list_databases(query: str | None = None, page_size: int = 10) -> CallToolResult:
    try:
        client = get_client()
        res = client.search(
            query=query or None,
            filter={"property": "object", "value": "database"},
            page_size=page_size,
        )
        return CallToolResult(content=[{"type": "json", "json": res}])
    except Exception as e:
        return CallToolResult(content=[{"type": "text", "text": f"error: {e}"}])

@srv.tool(name="notion_query_database", description="Query a Notion database. filter_json/sorts_json should be JSON strings matching Notion API.")
async def notion_query_database(database_id: str, filter_json: str = "", sorts_json: str = "", page_size: int = 25, start_cursor: str | None = None) -> CallToolResult:
    try:
        client = get_client()
        filt = json.loads(filter_json) if filter_json else None
        sorts = json.loads(sorts_json) if sorts_json else None
        res = client.databases.query(
            database_id=database_id,
            **({"filter": filt} if filt is not None else {}),
            **({"sorts": sorts} if sorts is not None else {}),
            **({"start_cursor": start_cursor} if start_cursor else {}),
            page_size=page_size,
        )
        return CallToolResult(content=[[{"type": "json", "json": res}]][0])
    except Exception as e:
        return CallToolResult(content=[{"type": "text", "text": f"error: {e}"}])

@srv.tool(name="notion_get_page", description="Retrieve a Notion page by page_id.")
async def notion_get_page(page_id: str) -> CallToolResult:
    try:
        client = get_client()
        res = client.pages.retrieve(page_id=page_id)
        return CallToolResult(content=[{"type": "json", "json": res}])
    except Exception as e:
        return CallToolResult(content=[{"type": "text", "text": f"error: {e}"}])

@srv.tool(name="notion_append_blocks", description="Append blocks to a block/page. children_json should be a JSON array of Notion block objects.")
async def notion_append_blocks(block_id: str, children_json: str) -> CallToolResult:
    try:
        client = get_client()
        children = json.loads(children_json)
        res = client.blocks.children.append(block_id=block_id, children=children)
        return CallToolResult(content=[{"type": "json", "json": res}])
    except Exception as e:
        return CallToolResult(content=[{"type": "text", "text": f"error: {e}"}])

async def main():
    await srv.run_stdio()

if __name__ == "__main__":
    asyncio.run(main())

