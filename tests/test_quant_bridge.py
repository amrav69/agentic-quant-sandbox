"""Tests for backend/quant_bridge.py.

Covers:
- Rust path (when quant_core is available)
- Pandas-ta fallback (when Rust is unavailable or fails)
- Return types are always pd.Series
- Output lengths preserved
"""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def close_series() -> pd.Series:
    """100-bar close price series."""
    rng = np.random.default_rng(42)
    prices = 100.0 + np.cumsum(rng.normal(0, 1, 100))
    return pd.Series(prices, name="Close")


@pytest.fixture()
def ohlc_series() -> tuple[pd.Series, pd.Series, pd.Series]:
    """200-bar (high, low, close) series with realistic spreads."""
    rng = np.random.default_rng(7)
    closes = 100.0 + np.cumsum(rng.normal(0, 1, 200))
    spreads = np.abs(rng.normal(0.5, 0.2, 200)) + 0.05
    highs = closes + spreads
    lows = closes - spreads
    index = pd.RangeIndex(200)
    return (
        pd.Series(highs, index=index, name="High"),
        pd.Series(lows, index=index, name="Low"),
        pd.Series(closes, index=index, name="Close"),
    )


# ---------------------------------------------------------------------------
# Helper: strip quant_core from sys.modules so bridge re-evaluates
# ---------------------------------------------------------------------------

def _bridge_without_rust():
    """Import quant_bridge in a context where quant_core is absent."""
    # Remove cached module so the bridge re-evaluates _RUST_AVAILABLE
    for key in list(sys.modules):
        if "quant_bridge" in key or "quant_core" in key:
            del sys.modules[key]

    with patch.dict("sys.modules", {"quant_core": None}):
        import backend.quant_bridge as bridge  # noqa: PLC0415
        return bridge


# ---------------------------------------------------------------------------
# Tests — Rust path
# ---------------------------------------------------------------------------

class TestRustPath:
    def test_calculate_rsi_returns_series(self, close_series):
        from backend import quant_bridge as bridge
        result = bridge.calculate_rsi(close_series, period=14)
        assert isinstance(result, pd.Series)

    def test_calculate_rsi_length_preserved(self, close_series):
        from backend import quant_bridge as bridge
        result = bridge.calculate_rsi(close_series, period=14)
        assert len(result) == len(close_series)

    def test_calculate_ema_returns_series(self, close_series):
        from backend import quant_bridge as bridge
        result = bridge.calculate_ema(close_series, period=20)
        assert isinstance(result, pd.Series)

    def test_calculate_ema_length_preserved(self, close_series):
        from backend import quant_bridge as bridge
        result = bridge.calculate_ema(close_series, period=20)
        assert len(result) == len(close_series)

    def test_calculate_macd_returns_three_series(self, close_series):
        from backend import quant_bridge as bridge
        result = bridge.calculate_macd(close_series)
        assert len(result) == 3
        for s in result:
            assert isinstance(s, pd.Series)

    def test_calculate_macd_lengths_preserved(self, close_series):
        from backend import quant_bridge as bridge
        macd_line, signal_line, histogram = bridge.calculate_macd(close_series)
        assert len(macd_line) == len(close_series)
        assert len(signal_line) == len(close_series)
        assert len(histogram) == len(close_series)

    def test_calculate_atr_returns_series(self, ohlc_series):
        from backend import quant_bridge as bridge
        high, low, close = ohlc_series
        result = bridge.calculate_atr(high, low, close, period=14)
        assert isinstance(result, pd.Series)

    def test_calculate_atr_length_preserved(self, ohlc_series):
        from backend import quant_bridge as bridge
        high, low, close = ohlc_series
        result = bridge.calculate_atr(high, low, close, period=14)
        assert len(result) == len(close)
        # Warmup prefix matches pandas-ta (first period-1 values NaN)
        assert result.iloc[:13].isna().all()
        assert result.iloc[13:].notna().all()


# ---------------------------------------------------------------------------
# Tests — Pandas fallback (Rust unavailable)
# ---------------------------------------------------------------------------

class TestPandasFallback:
    def test_rsi_fallback_returns_series(self, close_series):
        bridge = _bridge_without_rust()
        result = bridge.calculate_rsi(close_series, period=14)
        assert isinstance(result, pd.Series)

    def test_rsi_fallback_length(self, close_series):
        bridge = _bridge_without_rust()
        result = bridge.calculate_rsi(close_series, period=14)
        assert len(result) == len(close_series)

    def test_ema_fallback_returns_series(self, close_series):
        bridge = _bridge_without_rust()
        result = bridge.calculate_ema(close_series, period=20)
        assert isinstance(result, pd.Series)

    def test_ema_fallback_length(self, close_series):
        bridge = _bridge_without_rust()
        result = bridge.calculate_ema(close_series, period=20)
        assert len(result) == len(close_series)

    def test_macd_fallback_returns_three_series(self, close_series):
        bridge = _bridge_without_rust()
        result = bridge.calculate_macd(close_series)
        assert len(result) == 3
        for s in result:
            assert isinstance(s, pd.Series)

    def test_macd_fallback_lengths(self, close_series):
        bridge = _bridge_without_rust()
        macd_line, signal_line, histogram = bridge.calculate_macd(close_series)
        assert len(macd_line) == len(close_series)
        assert len(signal_line) == len(close_series)
        assert len(histogram) == len(close_series)

    def test_atr_fallback_returns_series(self, ohlc_series):
        bridge = _bridge_without_rust()
        high, low, close = ohlc_series
        result = bridge.calculate_atr(high, low, close, period=14)
        assert isinstance(result, pd.Series)

    def test_atr_fallback_length(self, ohlc_series):
        bridge = _bridge_without_rust()
        high, low, close = ohlc_series
        result = bridge.calculate_atr(high, low, close, period=14)
        assert len(result) == len(close)


# ---------------------------------------------------------------------------
# Tests — Rust failure falls back silently
# ---------------------------------------------------------------------------

class TestRustFailFallback:
    def test_rsi_rust_failure_falls_back(self, close_series):
        """If the Rust call raises, bridge silently falls back to pandas."""
        # Reload bridge fresh
        for key in list(sys.modules):
            if "quant_bridge" in key:
                del sys.modules[key]

        failing_qc = MagicMock()
        failing_qc.calculate_rsi_py.side_effect = RuntimeError("forced failure")

        with patch.dict("sys.modules", {"quant_core": failing_qc}):
            import backend.quant_bridge as bridge  # noqa: PLC0415
            bridge._qc = failing_qc
            bridge._RUST_AVAILABLE = True
            result = bridge.calculate_rsi(close_series, period=14)

        assert isinstance(result, pd.Series)
        assert len(result) == len(close_series)

    def test_ema_rust_failure_falls_back(self, close_series):
        for key in list(sys.modules):
            if "quant_bridge" in key:
                del sys.modules[key]

        failing_qc = MagicMock()
        failing_qc.calculate_ema_py.side_effect = RuntimeError("forced failure")

        with patch.dict("sys.modules", {"quant_core": failing_qc}):
            import backend.quant_bridge as bridge  # noqa: PLC0415
            bridge._qc = failing_qc
            bridge._RUST_AVAILABLE = True
            result = bridge.calculate_ema(close_series, period=20)

        assert isinstance(result, pd.Series)
        assert len(result) == len(close_series)

    def test_atr_rust_failure_falls_back(self, ohlc_series):
        for key in list(sys.modules):
            if "quant_bridge" in key:
                del sys.modules[key]

        failing_qc = MagicMock()
        failing_qc.calculate_atr_py.side_effect = RuntimeError("forced failure")

        with patch.dict("sys.modules", {"quant_core": failing_qc}):
            import backend.quant_bridge as bridge  # noqa: PLC0415
            bridge._qc = failing_qc
            bridge._RUST_AVAILABLE = True
            high, low, close = ohlc_series
            result = bridge.calculate_atr(high, low, close, period=14)

        assert isinstance(result, pd.Series)
        assert len(result) == len(close)


# ---------------------------------------------------------------------------
# Tests — Rust ATR matches pandas-ta (skipped where extension is absent)
# ---------------------------------------------------------------------------

class TestAtrParity:
    def test_rust_atr_matches_pandas_ta(self, ohlc_series):
        """Direct extension call must agree with pandas-ta ATR(14)."""
        quant_core = pytest.importorskip("quant_core")
        import pandas_ta as ta

        high, low, close = ohlc_series
        rust_vals = quant_core.calculate_atr_py(
            high.tolist(), low.tolist(), close.tolist(), 14
        )
        ta_vals = ta.atr(high, low, close, length=14)

        rust_s = pd.Series(rust_vals, index=close.index, dtype=float)
        assert len(rust_s.dropna()) == len(ta_vals.dropna())
        assert rust_s.iloc[-1] == pytest.approx(ta_vals.iloc[-1], rel=1e-6)
        # Full-series agreement, not just the last bar
        both = pd.DataFrame({"rust": rust_s, "ta": ta_vals}).dropna()
        assert (both["rust"] - both["ta"]).abs().max() < 1e-6 * both["ta"].abs().max()

    def test_bridge_delegates_to_rust_atr(self, ohlc_series):
        """Bridge output must equal the direct extension output."""
        quant_core = pytest.importorskip("quant_core")
        from backend import quant_bridge as bridge

        assert bridge._RUST_AVAILABLE
        high, low, close = ohlc_series
        via_bridge = bridge.calculate_atr(high, low, close, period=14)
        direct = quant_core.calculate_atr_py(
            high.tolist(), low.tolist(), close.tolist(), 14
        )
        pd.testing.assert_series_equal(
            via_bridge,
            pd.Series(direct, index=close.index, dtype=float),
            check_names=False,
        )
