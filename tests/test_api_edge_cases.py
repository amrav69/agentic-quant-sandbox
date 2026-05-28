"""Additional edge-case and endpoint tests for the FastAPI app."""

from __future__ import annotations

from unittest.mock import patch


class TestCacheClear:
    """POST /cache/clear — cache management."""

    async def test_cache_clear_returns_ok(self, test_app):
        resp = await test_app.post("/cache/clear")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "cache cleared"


class TestAnalyzeAutonomous:
    """GET /analyze/{symbol} — fully autonomous analysis."""

    @patch("backend.main.fetch_market_data")
    @patch("backend.main.calculate_indicators")
    @patch("backend.agents.research_agent.ResearchAgent.analyze")
    async def test_autonomous_happy_path(
        self, mock_analyze, mock_calc_indicators, mock_fetch, test_app, mock_llm
    ):
        mock_fetch.return_value = {"symbol": "AAPL", "current_price": 150.0, "volume": 50_000_000}
        mock_calc_indicators.return_value = {
            "symbol": "AAPL", "current_price": 150.0, "RSI": 55.0,
            "MACD": 0.5, "MACD_signal": 0.3, "EMA20": 148.0, "EMA50": 145.0,
            "ATR": 2.5,
        }
        mock_analyze.return_value = {"agent": "research", "analysis": "Bullish", "raw_data": {}}

        resp = await test_app.get("/analyze/AAPL")
        assert resp.status_code == 200
        data = resp.json()
        assert data["symbol"] == "AAPL"
        assert "live_indicators" in data
        assert "ai_analysis" in data

    @patch("backend.main.fetch_market_data")
    async def test_autonomous_symbol_not_found(self, mock_fetch, test_app):
        mock_fetch.side_effect = ValueError("Symbol not found")
        resp = await test_app.get("/analyze/UNKNOWN")
        assert resp.status_code == 404

    @patch("backend.main.fetch_market_data")
    @patch("backend.main.calculate_indicators")
    async def test_autonomous_indicator_failure(
        self, mock_calc_indicators, mock_fetch, test_app
    ):
        mock_fetch.return_value = {"symbol": "AAPL", "current_price": 150.0, "volume": 50_000_000}
        mock_calc_indicators.side_effect = ValueError("Symbol not found")
        resp = await test_app.get("/analyze/FAIL")
        assert resp.status_code == 404


class TestDurationHeader:
    """Verify X-Request-Duration-Ms header is set."""

    async def test_duration_header_present(self, test_app):
        resp = await test_app.get("/health")
        assert resp.status_code == 200
        assert "X-Request-Duration-Ms" in resp.headers

    async def test_duration_header_is_integer(self, test_app):
        resp = await test_app.get("/health")
        ms = resp.headers.get("X-Request-Duration-Ms", "0")
        assert ms.isdigit()


class TestAnalyzeStreamErrors:
    """POST /analyze/stream — error handling."""

    @patch("backend.agents.research_agent.ResearchAgent.analyze")
    async def test_stream_pipeline_error(self, mock_analyze, test_app, mock_llm):
        mock_analyze.side_effect = RuntimeError("Pipeline crashed")

        resp = await test_app.post("/analyze/stream", json={"symbol": "AAPL"})
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        text = await resp.aread()
        body = text.decode()
        assert "error" in body


class TestGenerateErrors:
    """POST /generate — error handling."""

    @patch("backend.agents.research_agent.ResearchAgent.analyze")
    async def test_generate_pipeline_failure(self, mock_analyze, test_app, mock_llm):
        mock_analyze.side_effect = RuntimeError("Research failed")
        resp = await test_app.post("/generate", json={"symbol": "AAPL"})
        assert resp.status_code == 500


class TestCritiqueErrors:
    """POST /critique — error handling."""

    @patch("backend.agents.research_agent.ResearchAgent.analyze")
    async def test_critique_pipeline_failure(self, mock_analyze, test_app, mock_llm):
        mock_analyze.side_effect = RuntimeError("Research failed")
        resp = await test_app.post("/critique", json={"symbol": "AAPL"})
        assert resp.status_code == 500


class TestAnalyzeValidation:
    """POST /analyze — additional validation."""

    async def test_analyze_invalid_symbol_type(self, test_app):
        resp = await test_app.post("/analyze", json={"symbol": 123, "price": 150.0})
        assert resp.status_code == 422

    async def test_analyze_defaults_without_price(self, test_app):
        resp = await test_app.post("/analyze", json={"symbol": "AAPL"})
        assert resp.status_code == 200
