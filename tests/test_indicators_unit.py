"""Unit tests for the Python indicator calculation layer.

Tests the calculate_indicators function with mocked yfinance data.
"""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pandas as pd

from backend.quant.indicators import calculate_indicators


class TestCalculateIndicators:
    def _make_mock_df(self, n: int = 500) -> pd.DataFrame:
        np.random.seed(42)
        closes = 100.0 + np.cumsum(np.random.randn(n) * 0.5)
        highs = closes + np.abs(np.random.randn(n) * 0.3)
        lows = closes - np.abs(np.random.randn(n) * 0.3)
        opens = closes + np.random.randn(n) * 0.1
        index = pd.date_range("2025-01-01", periods=n, freq="h")
        return pd.DataFrame(
            {
                "Open": opens, "High": highs, "Low": lows,
                "Close": closes, "Volume": np.random.randint(100_000, 1_000_000, size=n),
            },
            index=index,
        )

    @patch("backend.quant.indicators.yf.Ticker")
    def test_returns_expected_keys(self, mock_ticker):
        mock_instance = mock_ticker.return_value
        mock_instance.history.return_value = self._make_mock_df(500)
        result = calculate_indicators("TEST")
        expected_keys = {
            "symbol", "current price", "current_price", "RSI",
            "MACD", "MACD signal", "MACD_signal", "EMA20", "EMA50", "ATR",
        }
        assert expected_keys.issubset(result.keys())
        assert result["symbol"] == "TEST"

    @patch("backend.quant.indicators.yf.Ticker")
    def test_rsi_is_between_0_and_100(self, mock_ticker):
        mock_instance = mock_ticker.return_value
        mock_instance.history.return_value = self._make_mock_df(500)
        result = calculate_indicators("TEST")
        assert 0.0 <= result["RSI"] <= 100.0

    @patch("backend.quant.indicators.yf.Ticker")
    def test_atr_is_positive(self, mock_ticker):
        mock_instance = mock_ticker.return_value
        mock_instance.history.return_value = self._make_mock_df(500)
        result = calculate_indicators("TEST")
        assert result["ATR"] > 0.0

    @patch("backend.quant.indicators.yf.Ticker")
    def test_current_price_is_positive(self, mock_ticker):
        mock_instance = mock_ticker.return_value
        mock_instance.history.return_value = self._make_mock_df(500)
        result = calculate_indicators("TEST")
        assert result["current_price"] > 0.0

    @patch("backend.quant.indicators.yf.Ticker")
    def test_raises_value_error_on_empty_df(self, mock_ticker):
        mock_instance = mock_ticker.return_value
        mock_instance.history.return_value = pd.DataFrame()
        import pytest
        with pytest.raises(ValueError):
            calculate_indicators("TEST")

    @patch("backend.quant.indicators.yf.Ticker")
    def test_insufficient_data_fallback(self, mock_ticker):
        mock_instance = mock_ticker.return_value
        short_df = self._make_mock_df(30)
        long_df = self._make_mock_df(500)

        def history_side_effect(period="1d", interval="1m"):
            if period == "1d":
                return short_df
            return long_df

        mock_instance.history.side_effect = history_side_effect
        result = calculate_indicators("TEST")
        assert result["current_price"] > 0.0

    @patch("backend.quant.indicators.yf.Ticker")
    def test_raises_on_persistent_insufficient_data(self, mock_ticker):
        mock_instance = mock_ticker.return_value
        mock_instance.history.return_value = self._make_mock_df(10)
        import pytest
        with pytest.raises(ValueError, match="Insufficient"):
            calculate_indicators("TEST")
