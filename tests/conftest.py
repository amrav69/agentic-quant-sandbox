"""Test configuration and shared fixtures for the agentic-quant-sandbox test suite."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import numpy as np
import pandas as pd
import pytest
from typing import AsyncGenerator

from backend.main import app


# ──────────────────────────────────────────────────────────────────────
# Fixtures: mock LLM client (prevents real API calls)
# ──────────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_llm():
    """Patches the LLM client used by all agents so no real API is called.

    The mock returns a canned JSON response that each agent's ``_parse_json``
    can digest.
    """
    canned = AsyncMock()
    canned.content = (
        '{"agent": "MockAgent", "regime": "Bullish", '
        '"trade_hypothesis": "Momentum continuation", '
        '"confidence": 0.65, "verdict": "PASS", '
        '"issues": [], "suggestions": [], '
        '"code": "print(1)", "based_on": "analysis"}'
    )
    mock_instance = AsyncMock()
    mock_instance.ainvoke.return_value = canned

    with patch("backend.agents.research_agent.get_groq_client", return_value=mock_instance):
        with patch("backend.agents.codegen_agent.get_groq_client", return_value=mock_instance):
            with patch("backend.agents.critic_agent.get_groq_client", return_value=mock_instance):
                yield mock_instance


# ──────────────────────────────────────────────────────────────────────
# Fixture: FastAPI test client via httpx
# ──────────────────────────────────────────────────────────────────────


@pytest.fixture
async def test_app() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provide an ``httpx.AsyncClient`` wired to the FastAPI app."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


# ──────────────────────────────────────────────────────────────────────
# Fixture: sample OHLCV DataFrame
# ──────────────────────────────────────────────────────────────────────


@pytest.fixture
def sample_ohlcv() -> pd.DataFrame:
    """Return a realistic OHLCV DataFrame with 100 rows of synthetic data."""
    np.random.seed(42)
    n = 100
    closes = 100.0 + np.cumsum(np.random.randn(n) * 0.5)
    highs = closes + np.abs(np.random.randn(n) * 0.3)
    lows = closes - np.abs(np.random.randn(n) * 0.3)
    opens = closes + np.random.randn(n) * 0.1

    index = pd.date_range("2025-01-01", periods=n, freq="h")
    return pd.DataFrame(
        {
            "Open": opens,
            "High": highs,
            "Low": lows,
            "Close": closes,
            "Volume": np.random.randint(100_000, 1_000_000, size=n),
        },
        index=index,
    )
