"""Quant bridge: Rust quant-core first, pandas-ta fallback.

Public API mirrors what the research agent expects:
  calculate_rsi(close: pd.Series, period: int) -> pd.Series
  calculate_ema(close: pd.Series, period: int) -> pd.Series
  calculate_macd(close: pd.Series, fast, slow, signal) -> (pd.Series, pd.Series, pd.Series)

If quant_core (Rust extension) is importable, its vectorised implementation is
used. On any failure the functions silently fall back to pandas-ta and log the
reason — the pipeline never fails due to Rust unavailability.
"""
from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Try to load the Rust extension once at import time
# ---------------------------------------------------------------------------
try:
    import quant_core as _qc  # noqa: F401 — presence check

    _RUST_AVAILABLE = True
    logger.info("quant_bridge: Rust quant_core loaded")
except Exception as _e:
    _qc = None  # type: ignore[assignment]
    _RUST_AVAILABLE = False
    logger.info("quant_bridge: Rust quant_core unavailable (%s), using pandas-ta fallback", _e)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_list(series: pd.Series) -> list[float]:
    return [float(x) for x in series.values]


def _to_series(values: list[float], index: pd.Index) -> pd.Series:
    return pd.Series(values, index=index, dtype=float)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Return RSI as a pandas Series aligned to *close*."""
    if _RUST_AVAILABLE:
        try:
            result = _qc.calculate_rsi_py(_to_list(close), period)  # type: ignore[union-attr]
            return _to_series(result, close.index)
        except Exception as exc:
            logger.warning("quant_bridge.calculate_rsi: Rust failed (%s), falling back to pandas-ta", exc)

    # pandas-ta fallback
    import pandas_ta as ta  # noqa: F401
    return ta.rsi(close, length=period)


def calculate_ema(close: pd.Series, period: int = 20) -> pd.Series:
    """Return EMA as a pandas Series aligned to *close*."""
    if _RUST_AVAILABLE:
        try:
            result = _qc.calculate_ema_py(_to_list(close), period)  # type: ignore[union-attr]
            return _to_series(result, close.index)
        except Exception as exc:
            logger.warning("quant_bridge.calculate_ema: Rust failed (%s), falling back to pandas-ta", exc)

    import pandas_ta as ta  # noqa: F401
    return ta.ema(close, length=period)


def calculate_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> pd.Series:
    """Return ATR (Wilder's smoothing) as a pandas Series aligned to *close*."""
    if _RUST_AVAILABLE:
        try:
            result = _qc.calculate_atr_py(  # type: ignore[union-attr]
                _to_list(high), _to_list(low), _to_list(close), period
            )
            return _to_series(result, close.index)
        except Exception as exc:
            logger.warning("quant_bridge.calculate_atr: Rust failed (%s), falling back to pandas-ta", exc)

    import pandas_ta as ta  # noqa: F401
    return ta.atr(high, low, close, length=period)


def calculate_macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Return (macd_line, signal_line, histogram) each as a pandas Series."""
    if _RUST_AVAILABLE:
        try:
            macd_line, signal_line, histogram = _qc.calculate_macd_py(  # type: ignore[union-attr]
                _to_list(close), fast, slow, signal
            )
            idx = close.index
            return (
                _to_series(macd_line, idx),
                _to_series(signal_line, idx),
                _to_series(histogram, idx),
            )
        except Exception as exc:
            logger.warning("quant_bridge.calculate_macd: Rust failed (%s), falling back to pandas-ta", exc)

    import pandas_ta as ta  # noqa: F401
    df = ta.macd(close, fast=fast, slow=slow, signal=signal)
    # pandas-ta column names: MACD_<fast>_<slow>_<signal>, MACDs_*, MACDh_*
    macd_col = [c for c in df.columns if c.startswith("MACD_")][0]
    sig_col = [c for c in df.columns if c.startswith("MACDs_")][0]
    hist_col = [c for c in df.columns if c.startswith("MACDh_")][0]
    return df[macd_col], df[sig_col], df[hist_col]
