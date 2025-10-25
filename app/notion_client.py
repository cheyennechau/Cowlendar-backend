import os
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()


def get_client() -> Client:
    token = os.getenv("NOTION_API_KEY", "")
    if not token:
        raise RuntimeError("NOTION_API_KEY not set in environment")
    return Client(auth=token)


def list_databases(query: Optional[str] = None, page_size: int = 10) -> Dict[str, Any]:
    client = get_client()
    kwargs = {
        "filter": {"property": "object", "value": "page"},
        "page_size": page_size,
    }
    if query:
        kwargs["query"] = query
    return client.search(**kwargs)


def query_database(
    database_id: str,
    filter: Optional[Dict[str, Any]] = None,
    sorts: Optional[List[Dict[str, Any]]] = None,
    page_size: int = 25,
    start_cursor: Optional[str] = None,
) -> Dict[str, Any]:
    client = get_client()
    kwargs: Dict[str, Any] = {"page_size": page_size}
    if filter is not None:
        kwargs["filter"] = filter
    if sorts is not None:
        kwargs["sorts"] = sorts
    if start_cursor:
        kwargs["start_cursor"] = start_cursor
    return client.databases.query(database_id=database_id, **kwargs)


def get_page(page_id: str) -> Dict[str, Any]:
    client = get_client()
    return client.pages.retrieve(page_id=page_id)


def append_blocks(block_id: str, children: List[Dict[str, Any]]) -> Dict[str, Any]:
    client = get_client()
    return client.blocks.children.append(block_id=block_id, children=children)
