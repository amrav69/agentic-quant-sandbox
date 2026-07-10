"""Tests for the TTL caching layer and async Redis cache."""

from __future__ import annotations

import json
import time
from unittest.mock import AsyncMock, patch

import pytest

from backend.cache import ttl_cache


class TestTtlCache:
    def test_cache_hits_and_misses(self):
        call_count = 0

        @ttl_cache(maxsize=16, ttl=60)
        def fetch(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        assert fetch(1) == 2
        assert call_count == 1
        assert fetch(1) == 2
        assert call_count == 1
        assert fetch(2) == 4
        assert call_count == 2
        assert fetch(1) == 2
        assert call_count == 2

    def test_cache_expiry(self):
        call_count = 0

        @ttl_cache(maxsize=16, ttl=1)
        def fetch(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        fetch(1)
        assert call_count == 1
        fetch(1)
        assert call_count == 1
        time.sleep(1.1)
        fetch(1)
        assert call_count == 2

    def test_cache_maxsize_eviction(self):
        call_count = 0

        @ttl_cache(maxsize=2, ttl=60)
        def fetch(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        fetch(1)
        fetch(2)
        fetch(3)
        # 3rd call should evict oldest (1)
        assert call_count == 3
        fetch(1)
        assert call_count == 4

    def test_cache_clear(self):
        call_count = 0

        @ttl_cache(maxsize=16, ttl=60)
        def fetch(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        fetch(1)
        assert call_count == 1
        fetch.cache_clear()
        fetch(1)
        assert call_count == 2

    def test_cache_different_args(self):
        call_count = 0

        @ttl_cache(maxsize=16, ttl=60)
        def fetch(a: int, b: str) -> str:
            nonlocal call_count
            call_count += 1
            return f"{a}:{b}"

        assert fetch(1, "a") == "1:a"
        assert call_count == 1
        assert fetch(1, "a") == "1:a"
        assert call_count == 1
        assert fetch(1, "b") == "1:b"
        assert call_count == 2

    def test_cache_kwargs(self):
        call_count = 0

        @ttl_cache(maxsize=16, ttl=60)
        def fetch(a: int, b: int = 0) -> int:
            nonlocal call_count
            call_count += 1
            return a + b

        assert fetch(1, b=2) == 3
        assert call_count == 1



def _research_result(symbol: str = "AAPL") -> dict:
    return {"agent": "research", "analysis": "{}", "raw_data": {"symbol": symbol}}


class TestGetCached:
    @pytest.mark.asyncio
    async def test_hit_returns_dict(self):
        stored = _research_result()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=json.dumps(stored))
        with patch("backend.redis_cache._get_client", return_value=mock_client):
            from backend.redis_cache import get_cached
            result = await get_cached("research:AAPL")
        assert result == stored

    @pytest.mark.asyncio
    async def test_miss_returns_none(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=None)
        with patch("backend.redis_cache._get_client", return_value=mock_client):
            from backend.redis_cache import get_cached
            result = await get_cached("research:MISSING")
        assert result is None

    @pytest.mark.asyncio
    async def test_redis_error_returns_none(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=ConnectionError("refused"))
        with patch("backend.redis_cache._get_client", return_value=mock_client):
            from backend.redis_cache import get_cached
            result = await get_cached("research:AAPL")
        assert result is None

    @pytest.mark.asyncio
    async def test_no_client_returns_none(self):
        with patch("backend.redis_cache._get_client", return_value=None):
            from backend.redis_cache import get_cached
            result = await get_cached("research:AAPL")
        assert result is None


class TestSetCached:
    @pytest.mark.asyncio
    async def test_calls_setex(self):
        mock_client = AsyncMock()
        mock_client.setex = AsyncMock()
        data = _research_result()
        with patch("backend.redis_cache._get_client", return_value=mock_client):
            from backend.redis_cache import set_cached
            await set_cached("research:AAPL", data, ttl_seconds=300)
        mock_client.setex.assert_awaited_once_with("research:AAPL", 300, json.dumps(data))

    @pytest.mark.asyncio
    async def test_redis_error_is_silent(self):
        mock_client = AsyncMock()
        mock_client.setex = AsyncMock(side_effect=ConnectionError("refused"))
        with patch("backend.redis_cache._get_client", return_value=mock_client):
            from backend.redis_cache import set_cached
            await set_cached("research:AAPL", _research_result())  # must not raise

    @pytest.mark.asyncio
    async def test_no_client_is_silent(self):
        with patch("backend.redis_cache._get_client", return_value=None):
            from backend.redis_cache import set_cached
            await set_cached("research:AAPL", _research_result())  # must not raise


class TestResearchAgentCache:
    @pytest.mark.asyncio
    async def test_cache_hit_skips_llm(self, mock_llm):
        stored = _research_result("TSLA")
        market_data = {"symbol": "TSLA", "price": 200.0}
        with (
            patch("backend.agents.research_agent.get_cached", new_callable=AsyncMock, return_value=stored) as mock_get,
            patch("backend.agents.research_agent.set_cached", new_callable=AsyncMock) as mock_set,
        ):
            from backend.agents.research_agent import ResearchAgent
            agent = ResearchAgent()
            result = await agent.analyze(market_data)
        mock_get.assert_awaited_once_with("research:TSLA")
        mock_set.assert_not_awaited()
        assert result == stored

    @pytest.mark.asyncio
    async def test_cache_miss_runs_llm_and_stores(self, mock_llm):
        market_data = {"symbol": "AAPL", "price": 150.0}
        with (
            patch("backend.agents.research_agent.get_cached", new_callable=AsyncMock, return_value=None) as mock_get,
            patch("backend.agents.research_agent.set_cached", new_callable=AsyncMock) as mock_set,
        ):
            from backend.agents.research_agent import ResearchAgent
            agent = ResearchAgent()
            result = await agent.analyze(market_data)
        mock_get.assert_awaited_once_with("research:AAPL")
        mock_set.assert_awaited_once()
        assert result["agent"] == "research"

    @pytest.mark.asyncio
    async def test_redis_unavailable_does_not_break_agent(self, mock_llm):
        """When Redis is down, get_cached returns None (silent-fail) and analysis still runs."""
        market_data = {"symbol": "GOOG", "price": 100.0}
        with (
            patch("backend.agents.research_agent.get_cached", new_callable=AsyncMock, return_value=None),
            patch("backend.agents.research_agent.set_cached", new_callable=AsyncMock),
        ):
            from backend.agents.research_agent import ResearchAgent
            agent = ResearchAgent()
            result = await agent.analyze(market_data)  # must not raise
        assert result["agent"] == "research"
