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

VECTORBT 1.0.0 SYNTAX RULES — follow exactly:

CORRECT indicator usage:
    ema20 = data['Close'].ewm(span=20, adjust=False).mean()
    ema50 = data['Close'].ewm(span=50, adjust=False).mean()
    delta = data['Close'].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    high_low = data['High'] - data['Low']
    high_close = (data['High'] - data['Close'].shift()).abs()
    low_close = (data['Low'] - data['Close'].shift()).abs()
    atr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1).rolling(14).mean()

CORRECT portfolio creation:
    entries = (condition_a) & (condition_b)
    exits = (condition_c) | (condition_d)
    entries = entries.fillna(False)
    exits = exits.fillna(False)
    portfolio = vbt.Portfolio.from_signals(
        data['Close'],
        entries,
        exits,
        fees=0.001,
        slippage=0.001,
        freq='D'
    )

FORBIDDEN — never use these:
    vbt.ta.RSI.run(...)
    vbt.ta.MACD.run(...)
    vbt.ta.ATR.run(...)
    vbt.ta.ema(...)
    vbt.logical_and(...)
    vbt.Signals(...)
    stop_loss=<Series>

TRADE COUNT REQUIREMENT — CRITICAL:
The backtest MUST produce at least 20 trades. This is a hard requirement.

To improve trade frequency:

- Download at least 5 years of history:
  yf.download(symbol, period="5y")

- Prefer broad, repeatable entry conditions.

Examples of GOOD entry conditions:
    entries = (rsi < 50)
    entries = (close > ema20) & (rsi < 60)
    entries = (close > ema20)

Examples of GOOD exit conditions:
    exits = (rsi > 55) | (close < ema50)

Avoid strategies that trigger only a handful of times.

Examples of BAD conditions:
    rsi < 30
    strict crossover-only logic
    extremely narrow ATR filters
    exits that almost never trigger

MINIMUM TRADE RULES:

- If using RSI:
    prefer thresholds around 50–60 rather than 30–35.

- If using EMA logic:
    avoid requiring rare crossover events alone.

- Use enough history to produce statistically meaningful trade counts.

- Do not rely solely on stop-loss exits.

CORE REQUIREMENTS:

* Use only pandas for indicator calculations.
* Never use vbt.ta APIs.
* Download data with:
  yf.download(symbol, period="5y")
* Include:
  fees=0.001
  slippage=0.001
* Always pass:
  freq="D"
* Call fillna(False) on entries and exits.
* The final Portfolio object MUST be named exactly:
  portfolio

EXECUTION CONTRACT:

* portfolio = vbt.Portfolio.from_signals(...) must exist as a top-level variable.
* Do not wrap portfolio creation inside a function.

OUTPUT REQUIREMENTS:

* Return ONLY executable Python code.
* No markdown.
* No explanations.
* No backticks.
* Clean variable names.
* Runnable immediately.
'''

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