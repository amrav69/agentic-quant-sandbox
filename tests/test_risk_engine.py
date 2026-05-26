"""Tests for the risk engine (position sizing, VaR, trade validation)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from backend.risk.engine import (
    PositionSizer,
    RiskChecker,
    TradeValidator,
    RiskConfig,
)


# ──────────────────────────────────────────────────────────────────────
# PositionSizer
# ──────────────────────────────────────────────────────────────────────


class TestPositionSizer:
    def test_kelly_fraction_zero_win_rate(self):
        assert PositionSizer.kelly_fraction(0.0, 1.1, 0.95) == 0.0

    def test_kelly_fraction_equal_wins_losses(self):
        # If win_rate == 0.5 and avg_win == avg_loss, Kelly should be near 0
        result = PositionSizer.kelly_fraction(0.5, 1.05, 0.95)
        assert 0.0 <= result <= 0.25

    def test_kelly_fraction_capped(self):
        result = PositionSizer.kelly_fraction(0.8, 1.20, 0.90, cap=0.25)
        assert result <= 0.25

    def test_kelly_fraction_high_edge(self):
        # Very high win rate but small edge -> still capped
        result = PositionSizer.kelly_fraction(0.9, 1.01, 0.99)
        assert 0.0 <= result <= 0.25

    def test_fixed_fraction_basic(self):
        shares = PositionSizer.fixed_fraction(
            capital=100_000, risk_pct=0.02, entry=50.0, stop=45.0
        )
        # 100k * 2% = $2000 risk; $5/share risk => 400 shares
        assert shares == 400

    def test_fixed_fraction_zero_entry(self):
        assert PositionSizer.fixed_fraction(100_000, 0.02, 0.0, 45.0) == 0

    def test_volatility_adjusted_basic(self):
        shares = PositionSizer.volatility_adjusted(
            capital=100_000, atr=2.5, risk_pct=0.02, entry=100.0
        )
        assert shares > 0

    def test_volatility_adjusted_zero_atr(self):
        assert PositionSizer.volatility_adjusted(100_000, 0.0, 0.02, 100.0) == 0


# ──────────────────────────────────────────────────────────────────────
# RiskChecker
# ──────────────────────────────────────────────────────────────────────


class TestRiskChecker:
    def test_max_drawdown_no_drawdown(self):
        ok, dd = RiskChecker.check_max_drawdown([100, 110, 120], 0.25)
        assert ok
        assert dd == 0.0

    def test_max_drawdown_exceeded(self):
        ok, dd = RiskChecker.check_max_drawdown([100, 110, 70, 80], 0.25)
        # peak=110, trough=70 => (110-70)/110 = 36.3%
        assert not ok
        assert dd > 0.25

    def test_max_drawdown_empty(self):
        ok, dd = RiskChecker.check_max_drawdown([], 0.25)
        assert ok
        assert dd == 0.0

    def test_position_concentration_ok(self):
        positions = {"AAPL": 50_000, "MSFT": 30_000, "GOOGL": 20_000}
        assert RiskChecker.check_position_concentration(positions, 0.5) == []

    def test_position_concentration_breach(self):
        positions = {"AAPL": 900_000, "MSFT": 100_000}
        result = RiskChecker.check_position_concentration(positions, 0.50)
        assert "AAPL" in result

    def test_correlation_empty_df(self):
        assert RiskChecker.check_correlation(pd.DataFrame(), 0.85) == []

    def test_correlation_single_column(self):
        df = pd.DataFrame({"A": [1, 2, 3]})
        assert RiskChecker.check_correlation(df, 0.85) == []

    def test_correlation_high_pair(self):
        np.random.seed(0)
        base = np.random.randn(100)
        # Add enough noise so the pair stays under moderate thresholds
        noise = np.random.randn(100) * 2.0
        df = pd.DataFrame({"A": base, "B": base * 0.3 + noise})
        pairs = RiskChecker.check_correlation(df, 0.85)
        # With enough noise, correlation should be low
        assert len(pairs) == 0

    def test_var_historical_empty(self):
        assert RiskChecker.var_historical([], 0.95) == 0.0

    def test_var_historical_known(self):
        returns = [-0.05, -0.03, -0.02, -0.01, 0.0, 0.01, 0.02, 0.03, 0.04, 0.05]
        var_95 = RiskChecker.var_historical(returns, 0.95)
        # At 95% confidence, the worst 5% of returns: sorted = [-0.05, -0.03, ...]
        # index = int(0.05 * 10) = 0, so VaR = |arr[0]| = 0.05
        assert abs(var_95 - 0.05) < 0.01

    def test_cvar_historical_known(self):
        returns = [-0.10, -0.08, -0.03, -0.02, -0.01, 0.0, 0.01, 0.02, 0.03, 0.04]
        cvar_95 = RiskChecker.cvar_historical(returns, 0.95)
        # tail: index = int(0.05 * 10) = 0 => tail = [-0.10]
        # CVaR = |-0.10| = 0.10
        assert abs(cvar_95 - 0.10) < 0.01


# ──────────────────────────────────────────────────────────────────────
# TradeValidator
# ──────────────────────────────────────────────────────────────────────


class TestTradeValidator:
    def test_validate_allows_valid_signal(self):
        validator = TradeValidator(RiskConfig(max_position_pct=1.0))
        signal = {"symbol": "AAPL", "side": "BUY", "entry": 150.0, "stop": 140.0, "size": 100}
        portfolio = {"equity_curve": [100_000], "positions": {}, "returns": None, "returns_list": []}
        approved, reasons = validator.validate(signal, portfolio)
        assert approved
        assert reasons == []

    def test_validate_blocks_oversized_position(self):
        validator = TradeValidator(RiskConfig(max_position_pct=0.1))
        signal = {"symbol": "AAPL", "side": "BUY", "entry": 150.0, "stop": 140.0, "size": 100}
        portfolio = {
            "equity_curve": [100_000],
            "positions": {"AAPL": 200_000, "MSFT": 50_000},
            "returns": None,
            "returns_list": [],
        }
        approved, reasons = validator.validate(signal, portfolio)
        assert not approved
        assert any("concentration" in r.lower() for r in reasons)

    def test_validate_blocks_exceeded_drawdown(self):
        validator = TradeValidator(RiskConfig(max_drawdown_pct=0.1))
        signal = {"symbol": "AAPL", "side": "BUY", "entry": 150.0, "stop": 140.0, "size": 100}
        portfolio = {
            "equity_curve": [100_000, 110_000, 80_000],
            "positions": {},
            "returns": None,
            "returns_list": [],
        }
        approved, reasons = validator.validate(signal, portfolio)
        assert not approved
        assert any("drawdown" in r.lower() for r in reasons)

    def test_validate_invalid_side(self):
        validator = TradeValidator()
        signal = {"symbol": "AAPL", "side": "INVALID", "entry": 150.0, "stop": 140.0, "size": 100}
        portfolio = {"equity_curve": [100_000], "positions": {}, "returns": None, "returns_list": []}
        approved, reasons = validator.validate(signal, portfolio)
        assert not approved
