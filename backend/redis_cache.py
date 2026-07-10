"""Async Redis cache with silent-fail behaviour."""
from __future__ import annotations

import json
import logging
import os

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
_client = None


async def _get_client():
    global _client
    if _client is None:
        try:
            import redis.asyncio as aioredis
            _client = aioredis.from_url(REDIS_URL, decode_responses=True)
        except Exception as exc:
            logger.warning("Redis client init failed: %s", exc)
            return None
    return _client


async def get_cached(key: str) -> dict | None:
    try:
        client = await _get_client()
        if client is None:
            return None
        value = await client.get(key)
        if value is None:
            return None
        return json.loads(value)
    except Exception as exc:
        logger.warning("Redis get_cached error: %s", exc)
        return None


async def set_cached(key: str, value: dict, ttl_seconds: int = 300) -> None:
    try:
        client = await _get_client()
        if client is None:
            return
        await client.setex(key, ttl_seconds, json.dumps(value))
    except Exception as exc:
        logger.warning("Redis set_cached error: %s", exc)
