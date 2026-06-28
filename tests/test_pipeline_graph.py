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


def _make_mock_agents(critique_side_effect=None, critique_return=None):
    """Return a mock agents dict that bypasses all real constructors."""
    research = MagicMock()
    research.analyze = AsyncMock(return_value=_research_result())

    codegen = MagicMock()
    codegen.generate = AsyncMock(return_value=_codegen_result())

    critic = MagicMock()
    if critique_side_effect is not None:
        critic.critique = AsyncMock(side_effect=critique_side_effect)
    else:
        critic.critique = AsyncMock(return_value=critique_return or _critique_result("PASS"))

    return {"research": research, "codegen": codegen, "critic": critic}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPipelinePassFirstAttempt:
    """PASS on first attempt — total_iterations must be 1."""

    @pytest.mark.asyncio
    async def test_pass_first_attempt_total_iterations(self):
        agents = _make_mock_agents(critique_return=_critique_result("PASS"))
        with (
            patch("backend.pipeline.graph.execute_backtest", return_value=_mock_execution("SUCCESS")),
            patch("backend.pipeline.graph._make_agents", return_value=agents),
        ):
            result = await run_critique_pipeline({"symbol": "AAPL"})

        assert result["total_iterations"] == 1
        assert result["final_verdict"] == "PASS"
        assert len(result["iterations"]) == 1

    @pytest.mark.asyncio
    async def test_pass_first_attempt_response_shape(self):
        agents = _make_mock_agents(critique_return=_critique_result("PASS"))
        with (
            patch("backend.pipeline.graph.execute_backtest", return_value=_mock_execution("SUCCESS")),
            patch("backend.pipeline.graph._make_agents", return_value=agents),
        ):
            result = await run_critique_pipeline({"symbol": "AAPL"})

        assert "research_analysis" in result
        assert "generated_code" in result
        assert "execution_result" in result
        assert "critique" in result
        assert "iterations" in result
        assert "final_verdict" in result
        assert "final_execution_result" in result
        assert "final_critique" in result
        assert "total_iterations" in result


class TestPipelineFailThenPass:
    """FAIL on first attempt, PASS on second → total_iterations == 2."""

    @pytest.mark.asyncio
    async def test_fail_then_pass_total_iterations(self):
        agents = _make_mock_agents(
            critique_side_effect=[_critique_result("FAIL"), _critique_result("PASS")]
        )
        with (
            patch("backend.pipeline.graph.execute_backtest", return_value=_mock_execution("SUCCESS")),
            patch("backend.pipeline.graph._make_agents", return_value=agents),
        ):
            result = await run_critique_pipeline({"symbol": "AAPL"})

        assert result["total_iterations"] == 2
        assert result["final_verdict"] == "PASS"
        assert len(result["iterations"]) == 2

    @pytest.mark.asyncio
    async def test_fail_then_pass_iterations_stored(self):
        agents = _make_mock_agents(
            critique_side_effect=[_critique_result("FAIL"), _critique_result("PASS")]
        )
        with (
            patch("backend.pipeline.graph.execute_backtest", return_value=_mock_execution("SUCCESS")),
            patch("backend.pipeline.graph._make_agents", return_value=agents),
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
        agents = _make_mock_agents(
            critique_side_effect=[_critique_result("FAIL"), _critique_result("FAIL")]
        )
        with (
            patch("backend.pipeline.graph.execute_backtest", return_value=_mock_execution("RUNTIME_ERROR")),
            patch("backend.pipeline.graph._make_agents", return_value=agents),
        ):
            result = await run_critique_pipeline({"symbol": "AAPL"})

        assert result["final_verdict"] == "FAIL"
        assert result["total_iterations"] == 2
        assert len(result["iterations"]) == 2

    @pytest.mark.asyncio
    async def test_no_more_than_two_iterations(self):
        agents = _make_mock_agents(critique_return=_critique_result("FAIL"))
        with (
            patch("backend.pipeline.graph.execute_backtest", return_value=_mock_execution("RUNTIME_ERROR")),
            patch("backend.pipeline.graph._make_agents", return_value=agents),
        ):
            result = await run_critique_pipeline({"symbol": "AAPL"})

        assert result["total_iterations"] <= 2