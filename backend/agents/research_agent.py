from langchain_core.messages  import HumanMessage, SystemMessage
from backend.llm_client import get_groq_client

class ResearchAgent:
    def __init__(self):
        self.llm = get_groq_client()
        self.system_prompt = '''You are a quantitative trading research agent.
        
Your job: Analyze market data and identify potential trading opportunities.

When given price data, indicators, and context, you should:
1. Identify the current market regime (trending/ranging/volatile)
2. Look for divergences or anomalies in indicators
3. Propose a trade hypothesis with clear logic
4. Define success/failure conditions

Be concise and data-driven. Output your analysis in clear sections.'''

    async def analyze(self, market_data: dict) -> dict:
        prompt = f'''Analyze this market data and propose a trading idea:

Symbol: {market_data.get('symbol')}
Current Price: {market_data.get('price')}
RSI: {market_data.get('rsi')}
MACD: {market_data.get('macd')}
Volume Trend: {market_data.get('volume_trend')}

Provide your analysis.'''

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
