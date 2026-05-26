"""Additional edge-case and property tests for the risk engine."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backend.risk.engine import (
    PositionSizer,
    RiskChecker,
    TradeValidator,
    RiskConfig,
)


# ──────────────────────────────────────────────────────────────────────
# PositionSizer — edge cases
# ──────────────────────────────────────────────────────────────────────


class TestPositionSizerEdgeCases:
    def test_kelly_fraction_win_rate_one(self):
        assert PositionSizer.kelly_fraction(1.0, 1.1, 0.95) == 0.0

    def test_kelly_fraction_win_rate_zero(self):
        assert PositionSizer.kelly_fraction(0.0, 1.1, 0.95) == 0.0

    def test_kelly_fraction_avg_loss_one(self):
        assert PositionSizer.kelly_fraction(0.5, 1.1, 1.0) == 0.0

    def test_kelly_fraction_avg_loss_greater_than_one(self):
        assert PositionSizer.kelly_fraction(0.5, 1.1, 1.5) == 0.0

    def test_kelly_fraction_avg_win_less_than_one(self):
        result = PositionSizer.kelly_fraction(0.5, 0.9, 0.95)
        assert result == 0.0

    def test_kelly_fraction_cap_respected(self):
        result = PositionSizer.kelly_fraction(1.0, 2.0, 0.5, cap=0.25)
        assert result == 0.0

    def test_fixed_fraction_zero_capital(self):
        assert PositionSizer.fixed_fraction(0, 0.02, 50.0, 45.0) == 0

    def test_fixed_fraction_zero_risk_pct(self):
        assert PositionSizer.fixed_fraction(100_000, 0.0, 50.0, 45.0) == 0

    def test_fixed_fraction_entry_stop_equal(self):
        assert PositionSizer.fixed_fraction(100_000, 0.02, 50.0, 50.0) == 0

    def test_fixed_fraction_entry_below_stop(self):
        shares = PositionSizer.fixed_fraction(100_000, 0.02, 45.0, 50.0)
        assert shares > 0

    def test_volatility_adjusted_zero_capital(self):
        assert PositionSizer.volatility_adjusted(0, 2.5, 0.02, 100.0) == 0

    def test_volatility_adjusted_very_low_atr(self):
        shares = PositionSizer.volatility_adjusted(100_000, 0.01, 0.02, 100.0)
        assert shares >= 0

    def test_volatility_adjusted_large_atr(self):
        shares = PositionSizer.volatility_adjusted(100_000, 50.0, 0.02, 100.0)
        # atr=50 => vol_risk=0.5, dollars_at_risk=2000 => shares=2000/50=40
        assert shares == 40

    @pytest.mark.parametrize(
        "win_rate, avg_win, avg_loss, cap, expected_range",
        [
            (0.6, 2.0, 0.5, 0.25, (0.0, 0.25)),
            (0.0, 1.1, 0.95, 0.25, (0.0, 0.0)),
            (0.5, 1.0, 0.95, 0.25, (0.0, 0.25)),
        ],
    )
    def test_kelly_parameterized(self, win_rate, avg_win, avg_loss, cap, expected_range):
        result = PositionSizer.kelly_fraction(win_rate, avg_win, avg_loss, cap)
        assert expected_range[0] <= result <= expected_range[1]


# ──────────────────────────────────────────────────────────────────────
# RiskChecker — edge cases
# ──────────────────────────────────────────────────────────────────────


class TestRiskCheckerEdgeCases:
    def test_drawdown_single_element(self):
        ok, dd = RiskChecker.check_max_drawdown([100.0], 0.25)
        assert ok
        assert dd == 0.0

    def test_drawdown_negative_equity(self):
        ok, dd = RiskChecker.check_max_drawdown([100, 50, -50], 0.5)
        assert not ok

    def test_drawdown_all_zeros(self):
        ok, dd = RiskChecker.check_max_drawdown([0, 0, 0], 0.25)
        assert ok
        assert dd == 0.0

    def test_concentration_empty_positions(self):
        assert RiskChecker.check_position_concentration({}, 0.2) == []

    def test_concentration_all_zero_values(self):
        assert RiskChecker.check_position_concentration({"AAPL": 0, "MSFT": 0}, 0.2) == []

    def test_concentration_single_position_within_limit(self):
        assert RiskChecker.check_position_concentration({"AAPL": 50_000}, 1.0) == []

    def test_concentration_zero_total(self):
        result = RiskChecker.check_position_concentration({"AAPL": 0}, 0.5)
        assert result == []

    def test_correlation_nan_values(self):
        df = pd.DataFrame({"A": [1, 2, 3], "B": [np.nan, np.nan, np.nan]})
        pairs = RiskChecker.check_correlation(df, 0.85)
        assert len(pairs) == 0

    def test_var_single_return(self):
        var = RiskChecker.var_historical([-0.05], 0.95)
        assert abs(var - 0.05) < 0.01

    def test_var_all_positive(self):
        var = RiskChecker.var_historical([0.01, 0.02, 0.03], 0.95)
        assert abs(var - 0.01) < 0.001

    def test_cvar_single_return(self):
        cvar = RiskChecker.cvar_historical([-0.10], 0.95)
        assert abs(cvar - 0.10) < 0.01

    def test_cvar_all_positive(self):
        cvar = RiskChecker.cvar_historical([0.01, 0.02, 0.03], 0.95)
        assert abs(cvar - 0.01) < 0.001

    def test_var_high_confidence(self):
        returns = [-0.1, -0.08, -0.05, -0.03, -0.01, 0.0, 0.01, 0.02, 0.03, 0.04]
        var = RiskChecker.var_historical(returns, 0.99)
        assert abs(var - 0.10) < 0.01

    def test_cvar_high_confidence(self):
        returns = [-0.1, -0.08, -0.05, -0.03, -0.01, 0.0, 0.01, 0.02, 0.03, 0.04]
        cvar = RiskChecker.cvar_historical(returns, 0.99)
        assert abs(cvar - 0.10) < 0.01


# ──────────────────────────────────────────────────────────────────────
# TradeValidator — edge cases
# ──────────────────────────────────────────────────────────────────────


class TestTradeValidatorEdgeCases:
    def test_validate_empty_portfolio(self):
        validator = TradeValidator(RiskConfig(max_position_pct=0.5))
        signal = {"symbol": "AAPL", "side": "BUY", "entry": 150.0, "stop": 140.0, "size": 100}
        approved, reasons = validator.validate(signal, {"positions": {}, "equity_curve": [100_000]})
        assert approved
        assert reasons == []

    def test_validate_blocks_var_breach(self):
        validator = TradeValidator(RiskConfig(max_var_1d=0.01))
        signal = {"symbol": "AAPL", "side": "BUY", "entry": 150.0, "stop": 140.0, "size": 100}
        portfolio = {
            "positions": {},
            "equity_curve": [100_000],
            "returns_list": [-0.05, -0.04, -0.03, -0.02, 0.01, 0.02],
        }
        approved, reasons = validator.validate(signal, portfolio)
        assert not approved
        assert any("VaR" in r for r in reasons)

    def test_validate_allows_side_sell(self):
        validator = TradeValidator()
        signal = {"symbol": "AAPL", "side": "SELL", "entry": 150.0, "stop": 160.0, "size": 100}
        portfolio = {"equity_curve": [100_000], "positions": {}, "returns": None, "returns_list": []}
        approved, reasons = validator.validate(signal, portfolio)
        assert approved

    def test_validate_missing_fields_defaults_safe(self):
        validator = TradeValidator()
        signal = {"symbol": "AAPL"}
        portfolio = {"equity_curve": [100_000], "positions": {}}
        approved, reasons = validator.validate(signal, portfolio)
        assert isinstance(approved, bool)
        assert isinstance(reasons, list)

    def test_validate_with_custom_config(self):
        validator = TradeValidator(RiskConfig(max_drawdown_pct=0.5))
        signal = {"symbol": "AAPL", "side": "BUY", "entry": 150.0, "stop": 140.0, "size": 100}
        portfolio = {"equity_curve": [100, 50], "positions": {}}
        approved, reasons = validator.validate(signal, portfolio)
        assert approved

    def test_risk_config_from_env(self, monkeypatch):
        monkeypatch.setenv("MAX_POSITION_PCT", "0.15")
        monkeypatch.setenv("MAX_DRAWDOWN_PCT", "0.30")
        monkeypatch.setenv("KELLY_CAP", "0.20")
        config = RiskConfig.from_env()
        assert config.max_position_pct == 0.15
        assert config.max_drawdown_pct == 0.30
        assert config.kelly_cap == 0.20
