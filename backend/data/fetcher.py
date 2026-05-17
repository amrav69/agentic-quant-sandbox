import yfinance as yf
from typing import Dict, Any

def fetch_market_data(symbol: str = "BTC-USD") -> Dict[str, Any]:
    """
    Fetches the latest 1-minute candle market data for a given ticker symbol using yfinance.

    Args:
        symbol (str): The ticker symbol to fetch (e.g., "BTC-USD", "AAPL"). Defaults to "BTC-USD".

    Returns:
        Dict[str, Any]: A dictionary containing:
            - symbol (str): The ticker symbol (uppercase)
            - current price (float): The latest closing price of the 1-minute candle
            - open (float): The opening price of the 1-minute candle
            - high (float): The highest price of the 1-minute candle
            - low (float): The lowest price of the 1-minute candle
            - volume (int): The volume of the 1-minute candle

    Raises:
        ValueError: If no data was returned for the symbol.
        RuntimeError: For other errors during data retrieval.
    """
    try:
        # Create a yfinance Ticker instance for the given symbol
        ticker = yf.Ticker(symbol)
        
        # Fetch the latest 1-minute candle data for today (1d period)
        data = ticker.history(period="1d", interval="1m")
        
        # Check if the DataFrame is empty (e.g., invalid symbol or no data available)
        if data.empty:
            raise ValueError(f"No market data found for symbol: '{symbol}'. Please verify the symbol is correct.")
        
        # Get the latest candle (the very last row in the retrieved DataFrame)
        latest_candle = data.iloc[-1]
        
        # Extract and format the market data into a clean python dictionary.
        # We explicitly cast numpy data types to native Python float/int types
        # to ensure the dictionary is fully JSON-serializable.
        result = {
            "symbol": symbol.upper(),
            "current price": float(latest_candle["Close"]),
            "current_price": float(latest_candle["Close"]),  # Adding current_price as a camel_case alias for programmatic safety
            "open": float(latest_candle["Open"]),
            "high": float(latest_candle["High"]),
            "low": float(latest_candle["Low"]),
            "volume": int(latest_candle["Volume"])
        }
        
        return result

    except ValueError as ve:
        # Re-raise standard value errors for the caller to handle
        raise ve
    except Exception as e:
        # Wrap any network, parsing, or unexpected errors in a RuntimeError with helpful details
        raise RuntimeError(f"Failed to fetch market data for '{symbol}': {str(e)}") from e
