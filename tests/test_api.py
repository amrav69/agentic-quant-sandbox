"""Tests for the FastAPI REST endpoints."""

from __future__ import annotations

import pytest
from unittest.mock import patch


class TestHealth:
    """GET /health — always returns 200."""

    async def test_health_returns_200(self, test_app):
        resp = await test_app.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"

    async def test_root_returns_running(self, test_app):
        resp = await test_app.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "running"


class TestAnalyze:
    """POST /analyze — market analysis endpoint."""

    @patch("backend.agents.research_agent.ResearchAgent.analyze")
    async def test_analyze_happy_path(self, mock_analyze, test_app, mock_llm):
        mock_analyze.return_value = {"agent": "research", "analysis": "Bullish momentum", "raw_data": {}}
        resp = await test_app.post("/analyze", json={"symbol": "AAPL", "price": 150.0})
        assert resp.status_code == 200
        data = resp.json()
        assert "analysis" in str(data) or "agent" in str(data)

    async def test_analyze_empty_body(self, test_app):
        resp = await test_app.post("/analyze", json={})
        # Pydantic requires 'symbol' field
        assert resp.status_code == 422

    async def test_analyze_missing_symbol(self, test_app):
        resp = await test_app.post("/analyze", json={"price": 100.0})
        # Pydantic requires 'symbol' field
        assert resp.status_code == 422

    async def test_analyze_invalid_json(self, test_app):
        resp = await test_app.post("/analyze", content=b"not json")
        assert resp.status_code == 422 or resp.status_code == 400


class TestGenerate:
    """POST /generate — backtest code generation."""

    @patch("backend.agents.research_agent.ResearchAgent.analyze")
    @patch("backend.agents.codegen_agent.CodeGenAgent.generate")
    async def test_generate_happy_path(self, mock_generate, mock_analyze, test_app, mock_llm):
        mock_analyze.return_value = {"agent": "research", "analysis": "Trend following", "raw_data": {}}
        mock_generate.return_value = {"agent": "codegen", "code": "print('backtest')", "based_on": "analysis"}

        resp = await test_app.post("/generate", json={"symbol": "AAPL", "price": 150.0})
        assert resp.status_code == 200
        data = resp.json()
        assert "research_analysis" in data
        assert "generated_code" in data


class TestCritique:
    """POST /critique — full 3-agent pipeline."""

    @patch("backend.agents.research_agent.ResearchAgent.analyze")
    @patch("backend.agents.codegen_agent.CodeGenAgent.generate")
    @patch("backend.agents.critic_agent.CriticAgent.critique")
    async def test_critique_happy_path(
        self, mock_critique, mock_generate, mock_analyze, test_app, mock_llm
    ):
        mock_analyze.return_value = {"agent": "research", "analysis": "Bullish", "raw_data": {}}
        mock_generate.return_value = {"agent": "codegen", "code": "x", "based_on": ""}
        mock_critique.return_value = {
            "agent": "CriticAgent",
            "verdict": "PASS",
            "issues": [],
            "suggestions": ["Add trailing stop"],
        }

        resp = await test_app.post("/critique", json={"symbol": "AAPL", "price": 150.0})
        assert resp.status_code == 200
        data = resp.json()
        assert "research_analysis" in data
        assert "generated_code" in data
        assert "critique" in data


class TestStream:
    """POST /analyze/stream — SSE streaming pipeline."""

    @patch("backend.agents.research_agent.ResearchAgent.analyze")
    @patch("backend.agents.codegen_agent.CodeGenAgent.generate")
    @patch("backend.agents.critic_agent.CriticAgent.critique")
    async def test_stream_returns_sse_events(
        self, mock_critique, mock_generate, mock_analyze, test_app, mock_llm
    ):
        mock_analyze.return_value = {"agent": "research", "analysis": "Bullish", "raw_data": {}}
        mock_generate.return_value = {"agent": "codegen", "code": "x", "based_on": ""}
        mock_critique.return_value = {"agent": "CriticAgent", "verdict": "PASS", "issues": []}

        resp = await test_app.post("/analyze/stream", json={"symbol": "AAPL"})
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        text = await resp.aread()
        body = text.decode()
        assert "research" in body
        assert "codegen" in body
        assert "critic" in body
