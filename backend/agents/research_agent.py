from langchain_core.messages import HumanMessage, SystemMessage
from backend.llm_client import get_groq_client
from backend.redis_cache import get_cached, set_cached

class ResearchAgent:
    def __init__(self):
        self.llm = get_groq_client()
        self.system_prompt = '''You are a senior institutional quantitative strategist operating inside a multi-agent AI trading pipeline.

You receive structured market indicator data and your sole job is to analyze it, classify the market regime, and generate a concise quantitative trade thesis as machine-readable JSON.

INPUT SCHEMA you will receive:
{
  "symbol": "...",
  "current_price": float,
  "rsi": float,
  "macd_line": float,
  "macd_signal": float,
  "ema20": float,
  "ema50": float,
  "atr": float,
  "volume_trend": "increasing" | "decreasing" | "neutral"
}

OUTPUT REQUIREMENTS:
- Output ONLY valid JSON. No markdown. No conversational text. No explanations outside JSON.
- Use this EXACT schema:
{
  "agent": "ResearchAgent",
  "regime": "",
  "regime_label": "",
  "indicator_reading": "",
  "trade_hypothesis": "",
  "entry_condition": "",
  "stop_loss_level": "",
  "invalidation_point": "",
  "confidence": 0
}

ALLOWED regime_label values ONLY:
- Bullish Trend
- Bearish Trend
- Ranging
- High Volatility

BEHAVIOR RULES:
- Use specific numeric reasoning. Reference exact indicator values.
- GOOD: "RSI at 72.4 indicates overbought momentum."
- BAD: "RSI looks high."
- Never guarantee profitability. Never fabricate data.
- Always define invalidation conditions.
- Include realistic stop-loss logic using ATR context.
- Express probabilistic thinking. Remain concise, analytical, skeptical.
- Avoid vague language, generic commentary, conversational tone.'''

    async def analyze(self, market_data: dict) -> dict:
        import logging
        logger = logging.getLogger(__name__)

        # Ensure market_data is a dictionary and we have a copy to modify if needed
        market_data = dict(market_data)
        symbol = market_data.get('symbol')

        # Redis cache check (silent-fail)
        cache_key = f"research:{symbol}"
        cached = await get_cached(cache_key)
        if cached is not None:
            logger.info("ResearchAgent: cache hit for %s", symbol)
            return cached

        if symbol:
            symbol_upper = symbol.upper()
            # If key indicators are missing or None, fetch and calculate them automatically
            needs_fetch = (
                market_data.get('rsi') is None or
                market_data.get('macd_line') is None or
                market_data.get('ema20') is None or
                market_data.get('ema50') is None or
                market_data.get('atr') is None
            )

            if needs_fetch:
                try:
                    logger.info("Auto-fetching market indicators for symbol %s inside ResearchAgent", symbol_upper)
                    from backend.quant.indicators import calculate_indicators
                    from backend.data.fetcher import fetch_market_data

                    indicators = calculate_indicators(symbol_upper)
                    live_data = fetch_market_data(symbol_upper)

                    # Populate missing values
                    if market_data.get('price') is None:
                        market_data['price'] = indicators.get('current_price')
                    if market_data.get('current_price') is None:
                        market_data['current_price'] = indicators.get('current_price')
                    if market_data.get('rsi') is None:
                        market_data['rsi'] = indicators.get('RSI')
                    if market_data.get('macd_line') is None:
                        market_data['macd_line'] = indicators.get('MACD')
                    if market_data.get('macd_signal') is None:
                        market_data['macd_signal'] = indicators.get('MACD_signal')
                    if market_data.get('ema20') is None:
                        market_data['ema20'] = indicators.get('EMA20')
                    if market_data.get('ema50') is None:
                        market_data['ema50'] = indicators.get('EMA50')
                    if market_data.get('atr') is None:
                        market_data['atr'] = indicators.get('ATR')
                    if market_data.get('volume_trend') is None:
                        volume_val = live_data.get('volume', 0)
                        ema20 = indicators.get('EMA20')
                        ema50 = indicators.get('EMA50')
                        trend_status = "Unknown"
                        if ema20 is not None and ema50 is not None:
                            trend_status = "Bullish (EMA20 > EMA50)" if ema20 > ema50 else "Bearish (EMA20 < EMA50)"
                        market_data['volume_trend'] = (
                            f"Volume: {volume_val:,} | Trend: {trend_status} | "
                            f"EMA20: {ema20:.2f} | EMA50: {ema50:.2f} | "
                            f"ATR: {indicators.get('ATR'):.4f}"
                        )
                except Exception as e:
                    logger.warning("Failed to auto-populate indicators for %s: %s", symbol_upper, e)

        # Resolve aliases / alternate keys
        current_price = market_data.get('current_price')
        if current_price is None:
            current_price = market_data.get('price')

        rsi = market_data.get('rsi')
        if rsi is None:
            rsi = market_data.get('RSI')

        macd_line = market_data.get('macd_line')
        macd_signal = market_data.get('macd_signal')

        # Try to parse MACD line & signal from formatted strings if still missing
        macd_str = market_data.get('macd')
        if macd_line is None and macd_str is not None:
            if isinstance(macd_str, str) and "Line:" in macd_str:
                try:
                    parts = macd_str.split(',')
                    for p in parts:
                        p = p.strip()
                        if p.startswith("Line:"):
                            macd_line = float(p.replace("Line:", "").strip())
                        elif p.startswith("Signal:"):
                            macd_signal = float(p.replace("Signal:", "").strip())
                except Exception:
                    pass
            elif isinstance(macd_str, (int, float)):
                macd_line = float(macd_str)

        ema20 = market_data.get('ema20')
        ema50 = market_data.get('ema50')
        atr = market_data.get('atr')

        # Try to parse EMA20, EMA50, ATR from formatted volume_trend strings if still missing
        volume_trend_str = market_data.get('volume_trend')
        if isinstance(volume_trend_str, str) and "|" in volume_trend_str:
            try:
                parts = volume_trend_str.split('|')
                for p in parts:
                    p = p.strip()
                    if p.startswith("EMA20:"):
                        ema20 = float(p.replace("EMA20:", "").strip())
                    elif p.startswith("EMA50:"):
                        ema50 = float(p.replace("EMA50:", "").strip())
                    elif p.startswith("ATR:"):
                        atr = float(p.replace("ATR:", "").strip())
            except Exception:
                pass

        prompt = f'''Analyze this market data and propose a trading idea:

Symbol: {market_data.get('symbol')}
Current Price: {current_price}
RSI: {rsi}
MACD Line: {macd_line}
MACD Signal: {macd_signal}
EMA20: {ema20}
EMA50: {ema50}
ATR: {atr}
Volume Trend: {volume_trend_str}

Output your analysis as valid JSON only.'''

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=prompt)
        ]

        response = await self.llm.ainvoke(messages)

        result = {
            'agent': 'research',
            'analysis': response.content,
            'raw_data': market_data
        }
        await set_cached(cache_key, result, ttl_seconds=300)
        return result
