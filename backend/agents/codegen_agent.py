from langchain_core.messages import HumanMessage, SystemMessage
from backend.llm_client import get_groq_client

class CodeGenAgent:
    def __init__(self):
        self.llm = get_groq_client()
        self.system_prompt = '''You are a quantitative trading code generator.

Your job: Take a trade hypothesis and write a complete vectorbt backtest in Python.

Rules
1. Always use vectorbt for backtesting
2. Include entry and exit signals based on the hypothesis
3. Set stop loss using ATR multiplier
4. Print Sharpe ratio, max drawdown, total return
5. Keep code clean and runnable

Return ONLY Python code. No explanation. No markdown.'''

    async def generate(self, research_output: dict) -> dict:
        prompt = f'''Write a vectorbt backtest for this trade idea:

{research_output.get('analysis')}

Symbol: {research_output.get('raw_data', {}).get('symbol')}

Generate complete runnable Python code.'''

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=prompt)
        ]

        response = await self.llm.ainvoke(messages)

        return {
            'agent': 'codegen',
            'code': response.content,
            'based_on': research_output.get('analysis')
        }