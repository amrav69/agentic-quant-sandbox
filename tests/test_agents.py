"""Tests for the three AI agents (Research, CodeGen, Critic)."""

from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, patch

from backend.agents.research_agent import ResearchAgent
from backend.agents.codegen_agent import CodeGenAgent
from backend.agents.critic_agent import CriticAgent


class TestResearchAgent:
    async def test_analyze_returns_expected_structure(self, mock_llm):
        agent = ResearchAgent()
        result = await agent.analyze({"symbol": "AAPL", "price": 150.0})
        assert "agent" in result
        assert result["agent"] == "research"
        assert "analysis" in result
        assert "raw_data" in result


class TestCodeGenAgent:
    async def test_generate_returns_code(self, mock_llm):
        agent = CodeGenAgent()
        result = await agent.generate({"analysis": "Trend up", "raw_data": {"symbol": "AAPL"}})
        assert "agent" in result
        assert result["agent"] == "codegen"
        assert "code" in result


class TestCriticAgent:
    async def test_critique_returns_json(self, mock_llm):
        agent = CriticAgent()
        result = await agent.critique({
            "research_analysis": {"analysis": "Bullish", "raw_data": {"symbol": "AAPL"}},
            "generated_code": {"code": "print('ok')", "based_on": "analysis"},
        })
        assert "agent" in result
        assert "verdict" in result

    def test_parse_json_valid(self):
        raw = '{"agent": "CriticAgent", "verdict": "PASS", "issues": [], "suggestions": []}'
        result = CriticAgent._parse_json(raw)
        assert result["verdict"] == "PASS"

    def test_parse_json_with_markdown_fences(self):
        raw = "```json\n{\"agent\": \"CriticAgent\", \"verdict\": \"FAIL\"}\n```"
        result = CriticAgent._parse_json(raw)
        assert result["verdict"] == "FAIL"

    def test_parse_json_with_trailing_garbage(self):
        raw = '{"agent": "CriticAgent", "verdict": "PASS"}\nSome trailing text\nAnd more'
        result = CriticAgent._parse_json(raw)
        assert result["verdict"] == "PASS"

    def test_parse_json_completely_invalid(self):
        result = CriticAgent._parse_json("this is not json at all")
        assert result["verdict"] == "FAIL"

    async def test_critique_includes_risk_flags(self, mock_llm):
        agent = CriticAgent()
        result = await agent.critique({
            "research_analysis": {"analysis": "High leverage and no stop loss", "raw_data": {"symbol": "AAPL"}},
            "generated_code": {"code": "print('backtest')", "based_on": "analysis"},
        })
        # The risk checker should flag the "high leverage" keyword
        assert "risk_flags" in result
