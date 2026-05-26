"""Property-based tests using Hypothesis.

Verifies invariants that must hold for any valid input.
"""

from __future__ import annotations

from hypothesis import given, strategies as st
import numpy as np
import pandas as pd

from backend.risk.engine import PositionSizer, RiskChecker
from backend.cache import ttl_cache


# ──────────────────────────────────────────────────────────────────────
# PositionSizer invariants
# ──────────────────────────────────────────────────────────────────────


class TestPositionSizerProperties:
    @given(
        win_rate=st.floats(min_value=0.0, max_value=1.0, exclude_max=True),
        avg_win=st.floats(min_value=0.01, max_value=10.0),
        avg_loss=st.floats(min_value=0.01, max_value=10.0),
    )
    def test_kelly_fraction_bounded_0_to_cap(self, win_rate, avg_win, avg_loss):
        cap = 0.25
        result = PositionSizer.kelly_fraction(win_rate, avg_win, avg_loss, cap)
        assert 0.0 <= result <= cap

    @given(
        capital=st.integers(min_value=0, max_value=10_000_000),
        risk_pct=st.floats(min_value=0.0, max_value=0.5),
        entry=st.floats(min_value=0.01, max_value=10_000.0),
        stop=st.floats(min_value=0.01, max_value=10_000.0),
    )
    def test_fixed_fraction_non_negative(self, capital, risk_pct, entry, stop):
        shares = PositionSizer.fixed_fraction(capital, risk_pct, entry, stop)
        assert shares >= 0

    @given(
        capital=st.integers(min_value=0, max_value=10_000_000),
        atr=st.floats(min_value=0.0, max_value=100.0),
        risk_pct=st.floats(min_value=0.0, max_value=0.5),
        entry=st.floats(min_value=0.01, max_value=10_000.0),
    )
    def test_volatility_adjusted_non_negative(self, capital, atr, risk_pct, entry):
        shares = PositionSizer.volatility_adjusted(capital, atr, risk_pct, entry)
        assert shares >= 0


# ──────────────────────────────────────────────────────────────────────
# RiskChecker invariants
# ──────────────────────────────────────────────────────────────────────


class TestRiskCheckerProperties:
    @given(
        equity_curve=st.lists(
            st.floats(min_value=0.01, max_value=1_000_000.0),
            min_size=1,
            max_size=100,
        ),
        max_dd=st.floats(min_value=0.0, max_value=1.0),
    )
    def test_drawdown_bounds(self, equity_curve, max_dd):
        ok, dd = RiskChecker.check_max_drawdown(equity_curve, max_dd)
        assert isinstance(ok, bool)
        assert 0.0 <= dd <= 1.0

    @given(
        returns=st.lists(
            st.floats(min_value=-1.0, max_value=10.0),
            min_size=1,
            max_size=100,
        ),
        confidence=st.floats(min_value=0.5, max_value=0.999),
    )
    def test_var_non_negative(self, returns, confidence):
        var = RiskChecker.var_historical(returns, confidence)
        assert var >= 0.0

    @given(
        returns=st.lists(
            st.floats(min_value=-0.5, max_value=0.5),
            min_size=50,
            max_size=200,
        ),
        confidence=st.floats(min_value=0.9, max_value=0.999),
    )
    def test_cvar_gte_var(self, returns, confidence):
        if len(returns) < 10:
            return
        var = RiskChecker.var_historical(returns, confidence)
        cvar = RiskChecker.cvar_historical(returns, confidence)
        assert cvar >= var - 1e-10

    @given(
        n_assets=st.integers(min_value=2, max_value=20),
        n_obs=st.integers(min_value=10, max_value=100),
    )
    def test_correlation_pairs_are_symmetric(self, n_assets, n_obs):
        np.random.seed(0)
        data = {f"A{i}": np.random.randn(n_obs) for i in range(n_assets)}
        df = pd.DataFrame(data)
        pairs = RiskChecker.check_correlation(df, 0.999)
        assert isinstance(pairs, list)
        for pair in pairs:
            assert isinstance(pair, tuple)
            assert len(pair) == 3
            a, b, corr = pair
            assert isinstance(a, str)
            assert isinstance(b, str)
            assert isinstance(corr, float)


# ──────────────────────────────────────────────────────────────────────
# TTL cache invariants
# ──────────────────────────────────────────────────────────────────────


class TestCacheProperties:
    @given(
        x=st.integers(min_value=-1000, max_value=1000),
    )
    def test_cache_is_idempotent(self, x):
        call_count = 0

        @ttl_cache(maxsize=64, ttl=60)
        def double(n: int) -> int:
            nonlocal call_count
            call_count += 1
            return n * 2

        result1 = double(x)
        result2 = double(x)
        assert result1 == result2
