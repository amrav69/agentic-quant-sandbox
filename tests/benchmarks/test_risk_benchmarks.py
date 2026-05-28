"""Benchmarks for the risk engine.

Run with: pytest tests/benchmarks/ --benchmark-only
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from backend.risk.engine import PositionSizer, RiskChecker


class TestPositionSizerBenchmarks:
    def test_bench_kelly_fraction(self, benchmark):
        result = benchmark(
            PositionSizer.kelly_fraction,
            0.6, 1.15, 0.92, 0.25,
        )
        assert 0.0 <= result <= 0.25

    def test_bench_fixed_fraction(self, benchmark):
        result = benchmark(
            PositionSizer.fixed_fraction,
            100_000, 0.02, 50.0, 45.0,
        )
        assert result == 400

    def test_bench_volatility_adjusted(self, benchmark):
        result = benchmark(
            PositionSizer.volatility_adjusted,
            100_000, 2.5, 0.02, 100.0,
        )
        assert result > 0


class TestRiskCheckerBenchmarks:
    def test_bench_max_drawdown_large(self, benchmark):
        equity = [100_000 + np.random.randn() * 500 for _ in range(10_000)]
        result = benchmark(RiskChecker.check_max_drawdown, equity, 0.25)
        assert isinstance(result, tuple)

    def test_bench_var_historical_large(self, benchmark):
        returns = list(np.random.randn(10_000) * 0.02)
        result = benchmark(RiskChecker.var_historical, returns, 0.95)
        assert isinstance(result, float)

    def test_bench_cvar_historical_large(self, benchmark):
        returns = list(np.random.randn(10_000) * 0.02)
        result = benchmark(RiskChecker.cvar_historical, returns, 0.95)
        assert isinstance(result, float)

    def test_bench_correlation_large(self, benchmark):
        n_assets = 20
        n_obs = 1000
        data = {f"Asset_{i}": np.random.randn(n_obs) for i in range(n_assets)}
        df = pd.DataFrame(data)
        result = benchmark(RiskChecker.check_correlation, df, 0.85)
        assert isinstance(result, list)

    def test_bench_concentration_many_assets(self, benchmark):
        positions = {f"Asset_{i}": np.random.uniform(1000, 100_000) for i in range(100)}
        result = benchmark(RiskChecker.check_position_concentration, positions, 0.20)
        assert isinstance(result, list)
