"""Per-asker group memory from an external service (Edison patch, MAR-71).

OpenViking does not know chat membership, so the bot cannot decide which group memories a
sender may read. When ``bot.group_recall`` is enabled, a trusted service receives the
sender's Feishu union_id (taken from the message event) and the query, checks membership, and returns assembled context.
Failures never block the reply: they are logged and treated as "no group memory".
"""

import os
from typing import Any

import httpx
from loguru import logger

from vikingbot.config.schema import SessionKey


def applies(
    config: Any, session_key: SessionKey | None, sender_id: str | None, is_group_chat: bool
) -> bool:
    cfg = getattr(config, "group_recall", None)
    return bool(
        cfg
        and cfg.enabled
        and cfg.url
        and session_key is not None
        and session_key.type == "feishu"
        and not is_group_chat
        and sender_id
        and sender_id.startswith("on_")
    )


async def fetch_group_memory(
    config: Any,
    sender_id: str,
    query: str,
    transport: httpx.AsyncBaseTransport | None = None,
) -> str:
    """Return group memory for the sender (``sender_id`` is the union_id), or "" on any failure."""
    cfg = config.group_recall
    token = os.environ.get(cfg.token_env, "")
    if not token or not query.strip():
        if not token:
            logger.warning(f"group_recall enabled but {cfg.token_env} is not set")
        return ""
    try:
        async with httpx.AsyncClient(timeout=cfg.timeout_seconds, transport=transport) as client:
            response = await client.post(
                cfg.url,
                json={"union_id": sender_id, "query": query[:2000]},
                headers={"Authorization": f"Bearer {token}"},
            )
        if response.status_code != 200:
            logger.warning(f"group_recall HTTP {response.status_code}")
            return ""
        context = response.json().get("context") or ""
    except Exception as exc:  # network, timeout, malformed JSON: never block the reply
        logger.warning(f"group_recall failed: {type(exc).__name__}")
        return ""
    return str(context)[: cfg.max_chars]
