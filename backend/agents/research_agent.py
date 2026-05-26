from langchain_core.messages import HumanMessage, SystemMessage
from backend.llm_client import get_groq_client

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
        prompt = f'''Analyze this market data and propose a trading idea:

Symbol: {market_data.get('symbol')}
Current Price: {market_data.get('current_price')}
RSI: {market_data.get('rsi')}
MACD Line: {market_data.get('macd_line')}
MACD Signal: {market_data.get('macd_signal')}
EMA20: {market_data.get('ema20')}
EMA50: {market_data.get('ema50')}
ATR: {market_data.get('atr')}
Volume Trend: {market_data.get('volume_trend')}

Output your analysis as valid JSON only.'''

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=prompt)
        ]

        response = await self.llm.ainvoke(messages)

        return {
            'agent': 'research',
            'analysis': response.content,
            'raw_data': market_data
        }
