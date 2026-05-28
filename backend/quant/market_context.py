import yfinance as yf
import pandas as pd
import pandas_ta as ta  # noqa: F401  — registers .ta accessor on DataFrames
from typing import Dict, Any

def get_market_context(symbol: str = "BTC-USD") -> Dict[str, Any]:
    """
    Analyzes the market structure for a given symbol across multiple timeframes
    (1m, 5m, 15m, 1h) and returns a comprehensive market context dictionary
    suitable for AI reasoning.

    For each timeframe, it calculates:
      - RSI (14)
      - EMA20 & EMA50
      - ATR (14)
      - Trend Regime (Bullish, Bearish, Ranging)
      - Volatility Regime (High, Low, Normal)

    Finally, it aggregates the timeframes to detect overall trend alignment and regimes.

    Args:
        symbol (str): The ticker symbol to analyze (e.g., "BTC-USD", "AAPL").

    Returns:
        Dict[str, Any]: A JSON-serializable dictionary containing multi-timeframe analysis.
    """
    symbol_upper = symbol.upper()
    ticker = yf.Ticker(symbol_upper)

    # Timeframe configurations: (interval, primary period, fallback period)
    timeframe_configs = {
        "1m": ("1m", "1d", "5d"),
        "5m": ("5m", "5d", "1mo"),
        "15m": ("15m", "5d", "1mo"),
        "1h": ("1h", "1mo", "3mo")
    }

    timeframes_data = {}
    
    for tf, (interval, primary_period, fallback_period) in timeframe_configs.items():
        try:
            # 1. Fetch historical candle data
            df = ticker.history(period=primary_period, interval=interval)
            
            # Fall back to a longer period if data is insufficient for calculations (min 50 rows)
            if df.empty or len(df) < 50:
                df = ticker.history(period=fallback_period, interval=interval)
                
            if df.empty:
                raise ValueError(f"No candle data returned for timeframe {tf}.")
                
            if len(df) < 50:
                raise ValueError(f"Insufficient candles returned for timeframe {tf} (found {len(df)}, requires >= 50).")

            # 2. Extract current price and volume
            current_price = float(df["Close"].iloc[-1])
            current_volume = int(df["Volume"].iloc[-1])

            # 3. Calculate Technical Indicators using pandas-ta
            rsi_series = df.ta.rsi(length=14)
            ema20_series = df.ta.ema(length=20)
            ema50_series = df.ta.ema(length=50)
            atr_series = df.ta.atr(length=14)
            
            # Extract latest non-NaN values
            def get_latest_valid_val(series: pd.Series) -> float:
                if series is None or series.empty:
                    raise ValueError("Calculated indicator series is empty.")
                valid = series.dropna()
                if valid.empty:
                    raise ValueError("Indicator calculation returned all NaN.")
                return float(valid.iloc[-1])

            rsi_val = get_latest_valid_val(rsi_series)
            ema20_val = get_latest_valid_val(ema20_series)
            ema50_val = get_latest_valid_val(ema50_series)
            atr_val = get_latest_valid_val(atr_series)

            # 4. Volatility Regime Detection (Compare current ATR to its historical 20-period EMA)
            atr_ema_series = atr_series.ewm(span=20, adjust=False).mean()
            atr_ema_val = get_latest_valid_val(atr_ema_series)
            
            if atr_val > 1.25 * atr_ema_val:
                volatility_regime = "High Volatility"
            elif atr_val < 0.75 * atr_ema_val:
                volatility_regime = "Low Volatility"
            else:
                volatility_regime = "Normal Volatility"

            # 5. Trend Regime Detection
            # - Bullish Trend: EMA20 is above EMA50, and the current price is above the EMA20
            # - Bearish Trend: EMA20 is below EMA50, and the current price is below the EMA20
            # - Ranging: EMA20 and EMA50 are close or price is weaving in between
            price_to_ema20_pct = (current_price - ema20_val) / ema20_val
            ema_spread_pct = (ema20_val - ema50_val) / ema50_val

            if ema20_val > ema50_val and current_price > ema20_val:
                trend_regime = "Bullish"
            elif ema20_val < ema50_val and current_price < ema20_val:
                trend_regime = "Bearish"
            else:
                trend_regime = "Ranging"

            # Store the compiled, JSON-serializable timeframe context
            timeframes_data[tf] = {
                "current_price": current_price,
                "volume": current_volume,
                "RSI": round(rsi_val, 2),
                "EMA20": round(ema20_val, 2),
                "EMA50": round(ema50_val, 2),
                "ATR": round(atr_val, 4),
                "trend_regime": trend_regime,
                "volatility_regime": volatility_regime,
                "price_to_ema20_spread_pct": round(price_to_ema20_pct * 100, 4),
                "ema_crossover_spread_pct": round(ema_spread_pct * 100, 4)
            }

        except Exception as e:
            raise RuntimeError(f"Failed to compile market context for timeframe '{tf}': {str(e)}") from e

    # 6. Cross-Timeframe Multi-Timeframe Alignment
    trends = [timeframes_data[tf]["trend_regime"] for tf in ["1m", "5m", "15m", "1h"]]
    bullish_count = trends.count("Bullish")
    bearish_count = trends.count("Bearish")
    ranging_count = trends.count("Ranging")

    # Overall Market Trend Alignment Summary
    if bullish_count == 4:
        trend_alignment = "Fully Aligned Bullish"
        market_regime = "Strong Bullish Trend"
    elif bearish_count == 4:
        trend_alignment = "Fully Aligned Bearish"
        market_regime = "Strong Bearish Trend"
    elif bullish_count >= 3:
        trend_alignment = "Strong Bullish Bias"
        market_regime = "Bullish Trend"
    elif bearish_count >= 3:
        trend_alignment = "Strong Bearish Bias"
        market_regime = "Bearish Trend"
    elif ranging_count >= 2 or (bullish_count == 2 and bearish_count == 2):
        trend_alignment = "Mixed / No Alignment"
        market_regime = "Ranging Market"
    else:
        trend_alignment = "Mixed Bias"
        market_regime = "Consolidating / Mixed"

    # Volatility summary across key anchor timeframes (15m and 1h)
    vol_15m = timeframes_data["15m"]["volatility_regime"]
    vol_1h = timeframes_data["1h"]["volatility_regime"]
    
    if vol_15m == "High Volatility" or vol_1h == "High Volatility":
        overall_volatility_regime = "High Volatility"
    elif vol_15m == "Low Volatility" and vol_1h == "Low Volatility":
        overall_volatility_regime = "Low Volatility"
    else:
        overall_volatility_regime = "Normal Volatility"

    return {
        "symbol": symbol_upper,
        "timeframes": timeframes_data,
        "market_regime": market_regime,
        "volatility_regime": overall_volatility_regime,
        "trend_alignment": trend_alignment
    }
