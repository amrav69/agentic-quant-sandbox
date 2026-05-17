import yfinance as yf
import pandas as pd
import pandas_ta as ta
from typing import Dict, Any

def calculate_indicators(symbol: str = "BTC-USD") -> Dict[str, Any]:
    """
    Fetches historical candle data for a given ticker symbol and calculates
    technical indicators including RSI (14), MACD (12, 26, 9), EMA 20, EMA 50, and ATR (14).

    Args:
        symbol (str): The ticker symbol to fetch and calculate indicators for. Defaults to "BTC-USD".

    Returns:
        Dict[str, Any]: A dictionary containing:
            - symbol (str): The ticker symbol (uppercase)
            - current price (float): The latest closing price
            - RSI (float): Relative Strength Index (14)
            - MACD (float): MACD line value
            - MACD signal (float): MACD signal line value
            - EMA20 (float): Exponential Moving Average (20)
            - EMA50 (float): Exponential Moving Average (50)
            - ATR (float): Average True Range (14)

    Raises:
        ValueError: If no candle data or insufficient candle data is available.
        RuntimeError: For other unexpected retrieval or calculation errors.
    """
    try:
        # Create a yfinance Ticker instance for the symbol
        ticker = yf.Ticker(symbol)
        
        # Fetch candle history. We fetch 1d of 1-minute interval data.
        # This provides ~390 candles for US stocks and 1440 candles for crypto,
        # which is plenty for 14-period, 20-period, and 50-period indicators to stabilize.
        df = ticker.history(period="1d", interval="1m")
        
        # If the market recently opened or the symbol is less active, df might be short.
        # Fall back to 5d history to ensure we have enough bars (at least 50 bars are needed for EMA50).
        if df.empty or len(df) < 50:
            df = ticker.history(period="5d", interval="1m")
            
        if df.empty:
            raise ValueError(f"No market data could be retrieved for symbol: '{symbol}'. Please check the symbol name.")
            
        if len(df) < 50:
            raise ValueError(
                f"Insufficient historical data retrieved for symbol: '{symbol}'. "
                f"Requires at least 50 candles, but only found {len(df)}."
            )
            
        # Get the latest closing price of the asset
        current_price = float(df["Close"].iloc[-1])
        
        # --- Calculate Indicators using pandas-ta ---
        # 1. RSI (14)
        rsi_series = df.ta.rsi(length=14)
        
        # 2. MACD (default: fast=12, slow=26, signal=9)
        macd_df = df.ta.macd(fast=12, slow=26, signal=9)
        
        # 3. EMA 20 & EMA 50
        ema20_series = df.ta.ema(length=20)
        ema50_series = df.ta.ema(length=50)
        
        # 4. ATR (14)
        atr_series = df.ta.atr(length=14)
        
        # --- Helper function for robust float extraction ---
        def extract_latest_value(series: pd.Series) -> float:
            """Safely extracts the latest non-NaN float value from a pandas Series."""
            if series is None or series.empty:
                raise ValueError("Series is empty or None.")
            valid_series = series.dropna()
            if valid_series.empty:
                raise ValueError(f"Indicator calculation returned all NaN values for series.")
            return float(valid_series.iloc[-1])
            
        # --- Extract values safely ---
        rsi_val = extract_latest_value(rsi_series)
        ema20_val = extract_latest_value(ema20_series)
        ema50_val = extract_latest_value(ema50_series)
        atr_val = extract_latest_value(atr_series)
        
        # Since MACD returns a DataFrame with dynamically named columns depending on parameters,
        # we locate the MACD and MACD Signal column names programmatically.
        macd_col = [col for col in macd_df.columns if col.startswith("MACD_")][0]
        macd_sig_col = [col for col in macd_df.columns if col.startswith("MACDs_")][0]
        
        macd_val = extract_latest_value(macd_df[macd_col])
        macd_signal_val = extract_latest_value(macd_df[macd_sig_col])
        
        # Construct the final JSON-serializable dictionary
        indicators = {
            "symbol": symbol.upper(),
            "current price": current_price,
            "current_price": current_price,  # Alias
            "RSI": rsi_val,
            "MACD": macd_val,
            "MACD signal": macd_signal_val,
            "MACD_signal": macd_signal_val,  # Alias
            "EMA20": ema20_val,
            "EMA50": ema50_val,
            "ATR": atr_val
        }
        
        return indicators
        
    except ValueError as ve:
        raise ve
    except Exception as e:
        raise RuntimeError(f"An error occurred while calculating indicators for '{symbol}': {str(e)}") from e
