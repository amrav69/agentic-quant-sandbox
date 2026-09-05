"""Tests for CriticAgent risk integration with TradeValidator."""

from __future__ import annotations

from unittest.mock import patch

from backend.agents.critic_agent import CriticAgent


class TestCriticRiskIntegration:
    def _make_agent(self):
        with patch("backend.agents.critic_agent.get_groq_client") as mock_get:
            mock_get.return_value = None
            return CriticAgent()

    def test_run_risk_checks_high_leverage_flag(self):
        agent = self._make_agent()
        analysis = {"analysis": "This strategy uses high leverage with no stop loss", "raw_data": {"symbol": "AAPL"}}
        code = {"code": "print('ok')", "based_on": "analysis"}
        flags = agent._run_risk_checks(analysis, code)
        assert any("high leverage" in f.lower() or "no stop" in f.lower() for f in flags)

    def test_run_risk_checks_no_keywords(self):
        agent = self._make_agent()
        analysis = {"analysis": "Standard trend following strategy", "raw_data": {"symbol": "AAPL"}}
        code = {"code": "print('ok')", "based_on": "analysis"}
        flags = agent._run_risk_checks(analysis, code)
        assert isinstance(flags, list)

    def test_run_risk_checks_overfit_keyword(self):
        agent = self._make_agent()
        analysis = {"analysis": "Warning: this model is overfit on training data", "raw_data": {"symbol": "AAPL"}}
        code = {"code": "print('ok')", "based_on": "analysis"}
        flags = agent._run_risk_checks(analysis, code)
        assert any("overfit" in f.lower() for f in flags)

    def test_run_risk_checks_empty_analysis(self):
        agent = self._make_agent()
        analysis = {"analysis": "", "raw_data": {"symbol": "AAPL"}}
        code = {"code": "print('ok')", "based_on": "analysis"}
        flags = agent._run_risk_checks(analysis, code)
        assert isinstance(flags, list)

    def test_run_risk_checks_survivorship_bias(self):
        agent = self._make_agent()
        analysis = {"analysis": "survivorship bias may affect results", "raw_data": {"symbol": "AAPL"}}
        code = {"code": "print('ok')", "based_on": "analysis"}
        flags = agent._run_risk_checks(analysis, code)
        assert any("survivorship" in f.lower() for f in flags)

    def test_run_risk_checks_data_snooping(self):
        agent = self._make_agent()
        analysis = {"analysis": "Potential data snooping issues detected", "raw_data": {"symbol": "AAPL"}}
        code = {"code": "print('ok')", "based_on": "analysis"}
        flags = agent._run_risk_checks(analysis, code)
        assert any("data snooping" in f.lower() for f in flags)

    # ── Real-signal checks ─────────────────────────────────────────────

    def _hypothesis(self, stop: str) -> dict:
        import json as _json

        return {
            "analysis": _json.dumps(
                {
                    "agent": "ResearchAgent",
                    "regime": "Bullish Trend",
                    "trade_hypothesis": "Momentum continuation",
                    "stop_loss_level": stop,
                    "confidence": 0.7,
                }
            ),
            "raw_data": {"symbol": "AAPL", "price": 150.0},
        }

    def test_stop_parsed_from_hypothesis_no_flag(self):
        """A machine-readable hypothesis stop means no missing-stop flag."""
        agent = self._make_agent()
        flags = agent._run_risk_checks(
            self._hypothesis("142.50"),
            {"code": "print('ok')", "based_on": "analysis"},
        )
        assert flags == []

    def test_missing_stop_everywhere_flagged(self):
        """No stop in hypothesis or code must raise the stop-loss flag."""
        agent = self._make_agent()
        analysis = {"analysis": "Standard trend following strategy", "raw_data": {"symbol": "AAPL", "price": 150.0}}
        code = {"code": "print('ok')", "based_on": "analysis"}
        flags = agent._run_risk_checks(analysis, code)
        assert any("stop-loss" in f.lower() for f in flags)

    def test_code_stop_markers_suppress_flag(self):
        """An sl_stop in generated code counts as an explicit stop."""
        agent = self._make_agent()
        analysis = {"analysis": "Standard trend following strategy", "raw_data": {"symbol": "AAPL", "price": 150.0}}
        code = {
            "code": "portfolio = vbt.Portfolio.from_signals(close, entries, exits, sl_stop=0.05)",
            "based_on": "analysis",
        }
        flags = agent._run_risk_checks(analysis, code)
        assert not any("stop-loss" in f.lower() for f in flags)

    def test_stop_above_entry_rejected(self):
        """A stop at/above the entry cannot protect a long — treated as missing."""
        agent = self._make_agent()
        flags = agent._run_risk_checks(
            self._hypothesis("160.00"),
            {"code": "print('ok')", "based_on": "analysis"},
        )
        assert any("stop-loss" in f.lower() for f in flags)

    def test_drawdown_breach_flagged_from_execution(self):
        """A measured backtest drawdown over the limit must flag."""
        agent = self._make_agent()
        flags = agent._run_risk_checks(
            self._hypothesis("142.50"),
            {"code": "portfolio = vbt.Portfolio.from_signals(close, entries, exits, sl_stop=0.05)", "based_on": "analysis"},
            {"status": "SUCCESS", "max_drawdown": 0.40, "total_trades": 50},
        )
        assert any("drawdown" in f.lower() for f in flags)

    def test_healthy_execution_no_flags(self):
        """Real stop + healthy execution metrics must stay silent."""
        agent = self._make_agent()
        flags = agent._run_risk_checks(
            self._hypothesis("$142.50"),
            {"code": "portfolio = vbt.Portfolio.from_signals(close, entries, exits, sl_stop=0.05)", "based_on": "analysis"},
            {"status": "SUCCESS", "max_drawdown": 0.05, "total_trades": 50},
        )
        assert flags == []

    def test_low_sample_not_double_flagged(self):
        """LOW_SAMPLE keeps its single serious issue — no extra trade-count flag."""
        agent = self._make_agent()
        flags = agent._run_risk_checks(
            self._hypothesis("142.50"),
            {"code": "print('ok')", "based_on": "analysis"},
            {"status": "LOW_SAMPLE", "max_drawdown": 0.05, "total_trades": 5},
        )
        assert flags == []

    def test_success_below_minimum_trades_flagged(self):
        """SUCCESS below the configured minimum trade count must flag."""
        agent = self._make_agent()
        flags = agent._run_risk_checks(
            self._hypothesis("142.50"),
            {"code": "print('ok')", "based_on": "analysis"},
            {"status": "SUCCESS", "max_drawdown": 0.05, "total_trades": 3},
        )
        assert any("trades" in f.lower() and "minimum" in f.lower() for f in flags)
