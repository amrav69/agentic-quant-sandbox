"""Tests for the LangGraph critique feedback-loop pipeline.

Covers:
  - PASS on first attempt → total_iterations == 1
  - FAIL first, PASS second → total_iterations == 2
  - FAIL both attempts → final_verdict == FAIL, total_iterations == 2
  - State schema: iterations list structure
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.pipeline.graph import run_critique_pipeline


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_execution(status: str = "SUCCESS"):
    result = MagicMock()
    result.model_dump.return_value = {
        "status": status,
        "sharpe_ratio": 1.2 if status == "SUCCESS" else None,
        "max_drawdown": -0.05 if status == "SUCCESS" else None,
        "cagr": 0.12 if status == "SUCCESS" else None,
        "win_rate": 0.55 if status == "SUCCESS" else None,
        "total_trades": 25 if status == "SUCCESS" else None,
        "total_return": 0.14 if status == "SUCCESS" else None,
        "error_msg": None if status == "SUCCESS" else "RuntimeError",
    }
    return result


def _research_result():
    return {
        "agent": "research",
        "analysis": '{"regime": "Bullish", "confidence": 0.7}',
        "raw_data": {"symbol": "AAPL"},
    }


def _codegen_result():
    return {"agent": "codegen", "code": "portfolio = None", "based_on": "test"}


def _critique_result(verdict: str):
    issues = (
        []
        if verdict == "PASS"
        else [
            {"severity": "fatal", "issue": "Code did not run"},
            {"severity": "serious", "issue": "Missing stop loss"},
        ]
    )
    return {
        "agent": "CriticAgent",
        "verdict": verdict,
        "issues": issues,
        "suggestions": [],
        "execution_status": "SUCCESS",
    }


# ---------------------------------------------------------------------------
# Tests — patch at the graph node level (research/codegen/critic methods)
# ---------------------------------------------------------------------------


class TestPipelinePassFirstAttempt:
    """PASS on first attempt — total_iterations must be 1."""

    @pytest.mark.asyncio
    async def test_pass_first_attempt_total_iterations(self):
        with (
            patch(
                "backend.pipeline.graph.execute_backtest",
                return_value=_mock_execution("SUCCESS"),
            ),
            patch(
                "backend.agents.research_agent.ResearchAgent.analyze",
                new=AsyncMock(return_value=_research_result()),
            ),
            patch(
                "backend.agents.codegen_agent.CodeGenAgent.generate",
                new=AsyncMock(return_value=_codegen_result()),
            ),
            patch(
                "backend.agents.critic_agent.CriticAgent.critique",
                new=AsyncMock(return_value=_critique_result("PASS")),
            ),
        ):
            result = await run_critique_pipeline({"symbol": "AAPL"})

        assert result["total_iterations"] == 1
        assert result["final_verdict"] == "PASS"
        assert len(result["iterations"]) == 1

    @pytest.mark.asyncio
    async def test_pass_first_attempt_response_shape(self):
        with (
            patch(
                "backend.pipeline.graph.execute_backtest",
                return_value=_mock_execution("SUCCESS"),
            ),
            patch(
                "backend.agents.research_agent.ResearchAgent.analyze",
                new=AsyncMock(return_value=_research_result()),
            ),
            patch(
                "backend.agents.codegen_agent.CodeGenAgent.generate",
                new=AsyncMock(return_value=_codegen_result()),
            ),
            patch(
                "backend.agents.critic_agent.CriticAgent.critique",
                new=AsyncMock(return_value=_critique_result("PASS")),
            ),
        ):
            result = await run_critique_pipeline({"symbol": "AAPL"})

        # Backward-compatible keys
        assert "research_analysis" in result
        assert "generated_code" in result
        assert "execution_result" in result
        assert "critique" in result
        # New fields
        assert "iterations" in result
        assert "final_verdict" in result
        assert "final_execution_result" in result
        assert "final_critique" in result
        assert "total_iterations" in result


class TestPipelineFailThenPass:
    """FAIL on first attempt, PASS on second → total_iterations == 2."""

    @pytest.mark.asyncio
    async def test_fail_then_pass_total_iterations(self):
        critique_mock = AsyncMock(
            side_effect=[_critique_result("FAIL"), _critique_result("PASS")]
        )
        with (
            patch(
                "backend.pipeline.graph.execute_backtest",
                return_value=_mock_execution("SUCCESS"),
            ),
            patch(
                "backend.agents.research_agent.ResearchAgent.analyze",
                new=AsyncMock(return_value=_research_result()),
            ),
            patch(
                "backend.agents.codegen_agent.CodeGenAgent.generate",
                new=AsyncMock(return_value=_codegen_result()),
            ),
            patch(
                "backend.agents.critic_agent.CriticAgent.critique",
                new=critique_mock,
            ),
        ):
            result = await run_critique_pipeline({"symbol": "AAPL"})

        assert result["total_iterations"] == 2
        assert result["final_verdict"] == "PASS"
        assert len(result["iterations"]) == 2

    @pytest.mark.asyncio
    async def test_fail_then_pass_iterations_stored(self):
        critique_mock = AsyncMock(
            side_effect=[_critique_result("FAIL"), _critique_result("PASS")]
        )
        with (
            patch(
                "backend.pipeline.graph.execute_backtest",
                return_value=_mock_execution("SUCCESS"),
            ),
            patch(
                "backend.agents.research_agent.ResearchAgent.analyze",
                new=AsyncMock(return_value=_research_result()),
            ),
            patch(
                "backend.agents.codegen_agent.CodeGenAgent.generate",
                new=AsyncMock(return_value=_codegen_result()),
            ),
            patch(
                "backend.agents.critic_agent.CriticAgent.critique",
                new=critique_mock,
            ),
        ):
            result = await run_critique_pipeline({"symbol": "AAPL"})

        iters = result["iterations"]
        assert iters[0]["iteration"] == 1
        assert iters[1]["iteration"] == 2
        for it in iters:
            assert "code" in it
            assert "execution_result" in it
            assert "critique" in it


class TestPipelineFailBothAttempts:
    """FAIL on both attempts → final_verdict == FAIL, total_iterations == 2."""

    @pytest.mark.asyncio
    async def test_fail_both_attempts(self):
        critique_mock = AsyncMock(
            side_effect=[_critique_result("FAIL"), _critique_result("FAIL")]
        )
        with (
            patch(
                "backend.pipeline.graph.execute_backtest",
                return_value=_mock_execution("RUNTIME_ERROR"),
            ),
            patch(
                "backend.agents.research_agent.ResearchAgent.analyze",
                new=AsyncMock(return_value=_research_result()),
            ),
            patch(
                "backend.agents.codegen_agent.CodeGenAgent.generate",
                new=AsyncMock(return_value=_codegen_result()),
            ),
            patch(
                "backend.agents.critic_agent.CriticAgent.critique",
                new=critique_mock,
            ),
        ):
            result = await run_critique_pipeline({"symbol": "AAPL"})

        assert result["final_verdict"] == "FAIL"
        assert result["total_iterations"] == 2
        assert len(result["iterations"]) == 2

    @pytest.mark.asyncio
    async def test_no_more_than_two_iterations(self):
        """Pipeline must never exceed 2 total iterations."""
        with (
            patch(
                "backend.pipeline.graph.execute_backtest",
                return_value=_mock_execution("RUNTIME_ERROR"),
            ),
            patch(
                "backend.agents.research_agent.ResearchAgent.analyze",
                new=AsyncMock(return_value=_research_result()),
            ),
            patch(
                "backend.agents.codegen_agent.CodeGenAgent.generate",
                new=AsyncMock(return_value=_codegen_result()),
            ),
            patch(
                "backend.agents.critic_agent.CriticAgent.critique",
                new=AsyncMock(return_value=_critique_result("FAIL")),
            ),
        ):
            result = await run_critique_pipeline({"symbol": "AAPL"})

        assert result["total_iterations"] <= 2
