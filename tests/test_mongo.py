"""Tests for MongoDB persistence layer and related API endpoints.

All MongoDB I/O is mocked with AsyncMock so no real Mongo instance is needed.
The /runs and /runs/{id} endpoints are exercised via TestClient (sync httpx
wrapper around ASGI).  The /critique fire-and-forget path is verified to NOT
block or raise even when the database is unavailable.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

SAMPLE_RUN = {
    "_id": "665f1a2b3c4d5e6f7a8b9c0d",
    "symbol": "AAPL",
    "timestamp": "2026-01-01T00:00:00+00:00",
    "final_verdict": "PASS",
    "total_iterations": 1,
    "research_analysis": {"agent": "research", "analysis": "bullish"},
    "final_execution_result": {"status": "SUCCESS", "sharpe_ratio": 1.2},
    "final_critique": {"agent": "CriticAgent", "verdict": "PASS", "issues": []},
}

SAMPLE_RUN_WITH_ITERATIONS = {
    **SAMPLE_RUN,
    "iterations": [
        {"iteration": 1, "code": "portfolio = ...", "execution_result": {}, "critique": {}}
    ],
}


# ---------------------------------------------------------------------------
# Unit: save_pipeline_run
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_pipeline_run_returns_id():
    """save_pipeline_run should insert the document and return a string id."""
    mock_result = MagicMock()
    mock_result.inserted_id = "abc123"

    mock_col = AsyncMock()
    mock_col.insert_one.return_value = mock_result

    with patch("backend.db.mongo.get_pipeline_runs_collection", return_value=mock_col):
        from backend.db.mongo import save_pipeline_run

        run_id = await save_pipeline_run({"symbol": "AAPL", "final_verdict": "PASS"})

    assert run_id == "abc123"
    mock_col.insert_one.assert_awaited_once()


@pytest.mark.asyncio
async def test_save_pipeline_run_adds_timestamp_when_missing():
    """save_pipeline_run must stamp a timestamp if not provided."""
    mock_result = MagicMock()
    mock_result.inserted_id = "xyz"

    captured: list[dict] = []

    async def fake_insert(doc):
        captured.append(doc)
        return mock_result

    mock_col = AsyncMock()
    mock_col.insert_one.side_effect = fake_insert

    with patch("backend.db.mongo.get_pipeline_runs_collection", return_value=mock_col):
        from backend.db.mongo import save_pipeline_run

        await save_pipeline_run({"symbol": "TSLA", "final_verdict": "FAIL"})

    assert "timestamp" in captured[0], "timestamp must be injected"


@pytest.mark.asyncio
async def test_save_pipeline_run_returns_none_on_error():
    """save_pipeline_run must return None (not raise) when Mongo is down."""
    mock_col = AsyncMock()
    mock_col.insert_one.side_effect = Exception("connection refused")

    with patch("backend.db.mongo.get_pipeline_runs_collection", return_value=mock_col):
        from backend.db.mongo import save_pipeline_run

        result = await save_pipeline_run({"symbol": "AAPL"})

    assert result is None


# ---------------------------------------------------------------------------
# Unit: get_recent_runs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_recent_runs_returns_list():
    """get_recent_runs should return serialised documents without iterations."""
    mock_doc = dict(SAMPLE_RUN)
    from bson import ObjectId

    mock_doc["_id"] = ObjectId("665f1a2b3c4d5e6f7a8b9c0d")

    class FakeCursor:
        def __init__(self, docs):
            self._docs = iter(docs)

        def sort(self, *a, **kw):
            return self

        def limit(self, n):
            return self

        def __aiter__(self):
            return self

        async def __anext__(self):
            try:
                return next(self._docs)
            except StopIteration:
                raise StopAsyncIteration

    # find() on the collection is called synchronously (motor chaining pattern)
    mock_col = MagicMock()
    mock_col.find.return_value = FakeCursor([mock_doc])

    # get_pipeline_runs_collection is async — return the mock_col from it
    async def fake_get_col():
        return mock_col

    with patch("backend.db.mongo.get_pipeline_runs_collection", side_effect=fake_get_col):
        from backend.db.mongo import get_recent_runs

        runs = await get_recent_runs(limit=20)

    assert len(runs) == 1
    assert runs[0]["_id"] == "665f1a2b3c4d5e6f7a8b9c0d"   # ObjectId serialised to str


@pytest.mark.asyncio
async def test_get_recent_runs_returns_empty_list_on_error():
    """get_recent_runs must return [] (not raise) when Mongo is down."""
    mock_col = AsyncMock()
    mock_col.find.side_effect = Exception("timeout")

    with patch("backend.db.mongo.get_pipeline_runs_collection", return_value=mock_col):
        from backend.db.mongo import get_recent_runs

        result = await get_recent_runs()

    assert result == []


# ---------------------------------------------------------------------------
# Unit: get_run_by_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_run_by_id_returns_document():
    from bson import ObjectId

    mock_doc = dict(SAMPLE_RUN_WITH_ITERATIONS)
    mock_doc["_id"] = ObjectId("665f1a2b3c4d5e6f7a8b9c0d")

    mock_col = AsyncMock()
    mock_col.find_one.return_value = mock_doc

    with patch("backend.db.mongo.get_pipeline_runs_collection", return_value=mock_col):
        from backend.db.mongo import get_run_by_id

        doc = await get_run_by_id("665f1a2b3c4d5e6f7a8b9c0d")

    assert doc is not None
    assert doc["_id"] == "665f1a2b3c4d5e6f7a8b9c0d"
    assert "iterations" in doc


@pytest.mark.asyncio
async def test_get_run_by_id_returns_none_for_invalid_id():
    from backend.db.mongo import get_run_by_id

    result = await get_run_by_id("not-a-valid-objectid")
    assert result is None


@pytest.mark.asyncio
async def test_get_run_by_id_returns_none_when_not_found():
    mock_col = AsyncMock()
    mock_col.find_one.return_value = None

    with patch("backend.db.mongo.get_pipeline_runs_collection", return_value=mock_col):
        from backend.db.mongo import get_run_by_id

        result = await get_run_by_id("665f1a2b3c4d5e6f7a8b9c0d")

    assert result is None


# ---------------------------------------------------------------------------
# API: GET /runs
# ---------------------------------------------------------------------------


def test_get_runs_endpoint_returns_list():
    """GET /runs should return a JSON object with 'runs' and 'count'."""
    async def fake_get_recent_runs(limit=20):
        return [
            {
                "_id": "665f1a2b3c4d5e6f7a8b9c0d",
                "symbol": "AAPL",
                "timestamp": "2026-01-01T00:00:00+00:00",
                "final_verdict": "PASS",
                "total_iterations": 1,
            }
        ]

    with patch("backend.main.get_recent_runs", side_effect=fake_get_recent_runs):
        from backend.main import app
        client = TestClient(app)
        resp = client.get("/runs")

    assert resp.status_code == 200
    body = resp.json()
    assert "runs" in body
    assert "count" in body
    assert body["count"] == 1
    assert body["runs"][0]["symbol"] == "AAPL"


# ---------------------------------------------------------------------------
# API: GET /runs/{run_id}
# ---------------------------------------------------------------------------


def test_get_run_by_id_endpoint_returns_document():
    """GET /runs/{id} should return the full document including iterations."""
    async def fake_get_run_by_id(run_id):
        return dict(SAMPLE_RUN_WITH_ITERATIONS)

    with patch("backend.main.get_run_by_id", side_effect=fake_get_run_by_id):
        from backend.main import app
        client = TestClient(app)
        resp = client.get("/runs/665f1a2b3c4d5e6f7a8b9c0d")

    assert resp.status_code == 200
    body = resp.json()
    assert "iterations" in body
    assert body["final_verdict"] == "PASS"


def test_get_run_by_id_endpoint_returns_404_when_missing():
    """GET /runs/{id} should return 404 when the run is not found."""
    async def fake_get_run_by_id(run_id):
        return None

    with patch("backend.main.get_run_by_id", side_effect=fake_get_run_by_id):
        from backend.main import app
        client = TestClient(app)
        resp = client.get("/runs/nonexistent")

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Integration: /critique persistence is fire-and-forget
# ---------------------------------------------------------------------------


def test_critique_mongo_unavailable_does_not_break_response():
    """/critique must succeed even when MongoDB is completely down.

    We mock the full pipeline to return a canned result, then make
    save_pipeline_run raise an exception -- the endpoint must still return 200.
    """
    CANNED_RESULT = {
        "research_analysis": {},
        "generated_code": {"agent": "codegen", "code": "portfolio = None"},
        "execution_result": {"status": "SUCCESS"},
        "critique": {"agent": "CriticAgent", "verdict": "PASS", "issues": []},
        "iterations": [],
        "final_verdict": "PASS",
        "final_execution_result": {"status": "SUCCESS"},
        "final_critique": {"agent": "CriticAgent", "verdict": "PASS", "issues": []},
        "total_iterations": 1,
    }

    async def fake_run_pipeline(payload):
        return CANNED_RESULT

    async def fake_save_fails(doc):
        raise Exception("mongo is down")

    with patch("backend.main.run_critique_pipeline", side_effect=fake_run_pipeline), \
         patch("backend.main.save_pipeline_run", side_effect=fake_save_fails):
        from backend.main import app
        client = TestClient(app)
        resp = client.post("/critique", json={"symbol": "AAPL"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["final_verdict"] == "PASS"
