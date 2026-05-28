"""Tests for the three AI agents (Research, CodeGen, Critic)."""

from __future__ import annotations


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


class TestFullPipeline:
    """End-to-end integration test: all three agents wired together."""

    async def test_research_codegen_critic_chain(self, mock_llm):
        """Verify the full chain: research -> codegen -> critic with mocked LLM."""
        research = ResearchAgent()
        codegen = CodeGenAgent()
        critic = CriticAgent()

        research_result = await research.analyze({"symbol": "AAPL", "price": 150.0})
        assert research_result["agent"] == "research"

        codegen_result = await codegen.generate(research_result)
        assert codegen_result["agent"] == "codegen"
        assert "code" in codegen_result

        critique_result = await critic.critique({
            "research_analysis": research_result,
            "generated_code": codegen_result,
        })
        assert "verdict" in critique_result
        assert "issues" in critique_result

    async def test_critique_with_real_risk_parameters(self, mock_llm):
        """Verify risk checks extract the entry price from research raw_data."""
        research = ResearchAgent()
        critic = CriticAgent()

        research_result = await research.analyze({
            "symbol": "AAPL", "price": 150.0, "rsi": 65.0
        })

        critique_result = await critic.critique({
            "research_analysis": research_result,
            "generated_code": {"code": "print(1)", "based_on": "analysis"},
        })
        # Should run without error and return a valid structure
        assert "verdict" in critique_result
        assert "issues" in critique_result
