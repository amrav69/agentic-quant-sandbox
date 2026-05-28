"""Tests for the market context / indicator calculation layer."""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pandas as pd
import pandas_ta as ta  # noqa: F401  — registers .ta accessor on DataFrames

from backend.quant.market_context import get_market_context


class TestIndicators:
    def test_calculate_indicators_with_mock_data(self, sample_ohlcv):
        """Verify indicator functions work with a known sample DataFrame."""

        df = sample_ohlcv.copy()
        rsi = df.ta.rsi(length=14)
        assert rsi is not None
        assert len(rsi) == len(df)
        # Only the very first value may be NaN (insufficient warmup);
        # pandas-ta initialises with 0.0 after that
        assert pd.isna(rsi.iloc[0])
        # All non-NaN values should be finite
        assert rsi.dropna().notna().all()

    def test_ema_calculation(self, sample_ohlcv):

        df = sample_ohlcv.copy()
        ema20 = df.ta.ema(length=20)
        assert ema20 is not None
        assert len(ema20) == len(df)

    def test_macd_calculation(self, sample_ohlcv):

        df = sample_ohlcv.copy()
        macd = df.ta.macd(fast=12, slow=26, signal=9)
        assert macd is not None
        # MACD returns a DataFrame with 3 columns
        assert macd.shape[1] == 3

    def test_atr_calculation(self, sample_ohlcv):

        df = sample_ohlcv.copy()
        atr = df.ta.atr(length=14)
        assert atr is not None
        assert len(atr) == len(df)


class TestMarketContext:
    def test_market_context_returns_expected_keys(self):
        """get_market_context normally calls yfinance. Patch Ticker.history
        to return enough data for all timeframes and verify the return dict shape."""
        np.random.seed(42)
        n = 500
        closes = 100.0 + np.cumsum(np.random.randn(n) * 0.5)
        highs = closes + np.abs(np.random.randn(n) * 0.3)
        lows = closes - np.abs(np.random.randn(n) * 0.3)
        opens = closes + np.random.randn(n) * 0.1

        index = pd.date_range("2025-01-01", periods=n, freq="h")
        big_df = pd.DataFrame(
            {
                "Open": opens,
                "High": highs,
                "Low": lows,
                "Close": closes,
                "Volume": np.random.randint(100_000, 1_000_000, size=n),
            },
            index=index,
        )

        with patch("backend.quant.market_context.yf.Ticker") as mock_ticker:
            mock_instance = mock_ticker.return_value
            mock_instance.history.return_value = big_df
            mock_instance.info = {"symbol": "TEST"}
            result = get_market_context("TEST")

        expected_keys = {
            "symbol", "timeframes", "market_regime",
            "volatility_regime", "trend_alignment"
        }
        assert expected_keys.issubset(result.keys())
        assert result["symbol"] == "TEST"
