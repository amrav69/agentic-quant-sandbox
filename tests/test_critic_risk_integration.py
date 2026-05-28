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
