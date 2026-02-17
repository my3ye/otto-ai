import logging
from datetime import datetime, timezone

import httpx
from .config import settings

logger = logging.getLogger(__name__)

GRAPHITI_TIMEOUT = 15.0


async def graphiti_ingest(group_id: str, messages: list[dict]) -> bool:
    """Send messages to Graphiti for entity/relationship extraction.

    Fire-and-forget — Graphiti returns 202 and processes async.
    Each message dict should have: content, role_type, role, timestamp (optional).
    """
    try:
        async with httpx.AsyncClient(timeout=GRAPHITI_TIMEOUT) as client:
            resp = await client.post(
                f"{settings.graphiti_url}/messages",
                json={"group_id": group_id, "messages": messages},
            )
            if resp.status_code in (200, 202):
                logger.info(f"Graphiti ingested {len(messages)} messages for group '{group_id}'")
                return True
            logger.warning(f"Graphiti ingest returned {resp.status_code}: {resp.text[:200]}")
            return False
    except Exception as e:
        logger.warning(f"Graphiti ingest failed: {e}")
        return False


async def graphiti_search(
    query: str,
    group_ids: list[str] | None = None,
    max_facts: int = 10,
) -> list[dict]:
    """Search Graphiti for relevant facts/relationships.

    Returns list of fact dicts with: uuid, name, fact, valid_at, invalid_at, created_at, expired_at.
    """
    try:
        payload: dict = {"query": query, "max_facts": max_facts}
        if group_ids is not None:
            payload["group_ids"] = group_ids

        async with httpx.AsyncClient(timeout=GRAPHITI_TIMEOUT) as client:
            resp = await client.post(
                f"{settings.graphiti_url}/search",
                json=payload,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("facts", [])
            logger.warning(f"Graphiti search returned {resp.status_code}: {resp.text[:200]}")
            return []
    except Exception as e:
        logger.warning(f"Graphiti search failed: {e}")
        return []


async def graphiti_get_memory(
    group_id: str,
    messages: list[dict],
    center_node_uuid: str | None = None,
    max_facts: int = 10,
) -> list[dict]:
    """Get memory from Graphiti centered on a specific entity node.

    Returns list of fact dicts (same format as graphiti_search).
    """
    try:
        async with httpx.AsyncClient(timeout=GRAPHITI_TIMEOUT) as client:
            resp = await client.post(
                f"{settings.graphiti_url}/get-memory",
                json={
                    "group_id": group_id,
                    "messages": messages,
                    "center_node_uuid": center_node_uuid,
                    "max_facts": max_facts,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("facts", [])
            logger.warning(f"Graphiti get-memory returned {resp.status_code}: {resp.text[:200]}")
            return []
    except Exception as e:
        logger.warning(f"Graphiti get-memory failed: {e}")
        return []


def make_message(content: str, role_type: str, role: str, timestamp: datetime | None = None) -> dict:
    """Helper to build a Graphiti message dict."""
    ts = timestamp or datetime.now(timezone.utc)
    return {
        "content": content,
        "role_type": role_type,
        "role": role,
        "timestamp": ts.isoformat(),
        "source_description": "Otto Memory API",
    }
