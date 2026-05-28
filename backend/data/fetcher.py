"""Market data fetcher with TTL caching.

Uses yfinance to fetch OHLCV data and caches results with a 5-minute TTL.
"""

from __future__ import annotations

import logging
from typing import Any

import yfinance as yf

from backend.cache import ttl_cache

logger = logging.getLogger(__name__)


@ttl_cache(maxsize=128, ttl=300)
def fetch_market_data(symbol: str = "BTC-USD") -> dict[str, Any]:
    """Fetches the latest 1-minute candle market data for a given ticker symbol.

    Results are cached for 300 seconds (5 minutes) keyed by symbol.

    Args:
        symbol: The ticker symbol to fetch (e.g. "BTC-USD", "AAPL").

    Returns:
        A dict with ``symbol``, ``current_price``, ``open``, ``high``, ``low``,
        ``volume``.

    Raises:
        ValueError: No data returned for the symbol.
        RuntimeError: Other errors during data retrieval.
    """
    logger.debug("Fetching market data for %s", symbol)
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1d", interval="1m")

        if data.empty:
            raise ValueError(f"No market data found for symbol: '{symbol}'.")

        latest = data.iloc[-1]
        result = {
            "symbol": symbol.upper(),
            "current_price": float(latest["Close"]),
            "open": float(latest["Open"]),
            "high": float(latest["High"]),
            "low": float(latest["Low"]),
            "volume": int(latest["Volume"]),
        }
        logger.debug("Cache miss for %s — fetched %d rows", symbol, len(data))
        return result

    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(f"Failed to fetch market data for '{symbol}': {e}") from e
