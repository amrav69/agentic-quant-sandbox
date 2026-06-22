from langchain_core.messages import HumanMessage, SystemMessage
from backend.llm_client import get_groq_client
import re

def strip_code_fences(code: str) -> str:
    code = code.strip()
    code = re.sub(r'^```(?:python)?\n?', '', code)
    code = re.sub(r'\n?```$', '', code)
    return code.strip()

class CodeGenAgent:
    def __init__(self):
        self.llm = get_groq_client()
        self.system_prompt = '''You are a professional quantitative strategy engineer operating inside a multi-agent AI trading pipeline.

You receive a structured trade hypothesis and your sole job is to convert it into a deterministic, executable vectorbt backtest in Python.

CORE REQUIREMENTS - generated code MUST:

* Use vectorbt version 1.0.0 compatible syntax
* Use yfinance for historical data retrieval
* Fetch minimum 2 years of data
* Include 0.1% transaction costs
* Avoid all future data leakage and lookahead bias
* Avoid repainting indicators
* Use deterministic logic only — no random parameter generation
* Include stop-loss logic using ATR multiplier
* Print: Sharpe ratio, max drawdown, total return, total trades

BACKTEST QUALITY RULES:

* Minimum 2 years OR 500 trades — whichever produces more trades
* Avoid unrealistic execution assumptions
* Avoid same-bar entry/exit cheating
* Avoid future candle access
* Include transaction cost modeling at 0.1%
* Use defensive coding — handle NaN values explicitly
* Keep strategy logic simple and interpretable

EXECUTION CONTRACT (mandatory):

* The final vectorbt Portfolio object MUST be assigned to a variable named exactly: portfolio
* Example: portfolio = vbt.Portfolio.from_signals(...)
* Do not assign the Portfolio object to any other variable name
* Do not wrap portfolio creation inside a function — it must exist as a top-level variable in the script

OUTPUT REQUIREMENTS:

* Return ONLY executable Python code
* No markdown. No explanations. No conversational text.
* Clean variable naming. Runnable immediately.'''

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
        code = strip_code_fences(response.content)

        return {
            'agent': 'codegen',
            'code': code,
            'based_on': research_output.get('analysis')
        }