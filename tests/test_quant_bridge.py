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
