"""Async MongoDB persistence helpers for pipeline runs.

All public functions are async.  Every function is designed to degrade
gracefully: if MongoDB is down, a warning is logged and ``None`` is returned
(or an empty list for list-returning helpers).  Callers must never receive
an exception propagated from this module.

Configuration
-------------
MONGODB_URI  (env)  — default: ``mongodb://localhost:27017``
Database     : ``agentic_quant``
Collection   : ``pipeline_runs``
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal: lazily-initialised client
# ---------------------------------------------------------------------------

_client: AsyncIOMotorClient | None = None

_MONGODB_URI_DEFAULT = "mongodb://localhost:27017"
_DB_NAME = "agentic_quant"
_COLLECTION_NAME = "pipeline_runs"


def _get_client() -> AsyncIOMotorClient:
    """Return (and cache) the motor client.  Instantiated once per process."""
    global _client  # noqa: PLW0603
    if _client is None:
        uri = os.getenv("MONGODB_URI", _MONGODB_URI_DEFAULT)
        _client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=3_000)
        logger.info("mongo: client initialised (uri=%s)", uri)
    return _client


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


async def get_database():
    """Return the ``agentic_quant`` motor Database object."""
    return _get_client()[_DB_NAME]


async def get_pipeline_runs_collection() -> AsyncIOMotorCollection:
    """Return the ``pipeline_runs`` motor Collection object."""
    db = await get_database()
    return db[_COLLECTION_NAME]


async def save_pipeline_run(document: dict[str, Any]) -> str | None:
    """Insert *document* into ``pipeline_runs``.

    Automatically stamps ``timestamp`` (UTC ISO-8601) if not already present.

    Returns the inserted ``_id`` as a string, or ``None`` on failure.
    """
    if "timestamp" not in document:
        document = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **document,
        }
    try:
        col = await get_pipeline_runs_collection()
        result = await col.insert_one(document)
        run_id = str(result.inserted_id)
        logger.info("mongo: saved pipeline_run id=%s symbol=%s verdict=%s",
                    run_id,
                    document.get("symbol"),
                    document.get("final_verdict"))
        return run_id
    except Exception:
        logger.warning("mongo: save_pipeline_run failed — continuing without persistence",
                       exc_info=True)
        return None


async def get_recent_runs(limit: int = 20) -> list[dict[str, Any]]:
    """Return up to *limit* most-recent runs, **without** the ``iterations`` field.

    Returns an empty list on failure.
    """
    try:
        col = await get_pipeline_runs_collection()
        cursor = col.find(
            {},
            projection={
                "iterations": 0,       # exclude heavy per-iteration records
            },
        ).sort("timestamp", -1).limit(limit)
        runs = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])   # ObjectId → str for JSON serialisation
            runs.append(doc)
        return runs
    except Exception:
        logger.warning("mongo: get_recent_runs failed", exc_info=True)
        return []


async def get_run_by_id(run_id: str) -> dict[str, Any] | None:
    """Return the full document (including ``iterations``) for *run_id*.

    Returns ``None`` when the document is not found or on failure.
    """
    try:
        oid = ObjectId(run_id)
    except Exception:
        logger.warning("mongo: get_run_by_id — invalid ObjectId %r", run_id)
        return None
    try:
        col = await get_pipeline_runs_collection()
        doc = await col.find_one({"_id": oid})
        if doc is None:
            return None
        doc["_id"] = str(doc["_id"])
        return doc
    except Exception:
        logger.warning("mongo: get_run_by_id failed for id=%s", run_id, exc_info=True)
        return None
