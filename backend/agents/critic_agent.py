from langchain_core.messages import HumanMessage, SystemMessage
from backend.llm_client import get_groq_client
import json
import re
from typing import Dict, Any

class CriticAgent:
    """
    Skeptical, risk-focused institutional quant reviewer agent.
    Checks generated code and trading strategy logic for:
      - Lookahead bias / data leakage
      - Overfitting / curve fitting
      - Unrealistic transaction costs or slippage
      - Inadequate risk controls or missing stop-losses
      - Unrealistic returns or win rate expectations
    """
    def __init__(self):
        self.llm = get_groq_client()
        self.system_prompt = """You are a strict, highly skeptical institutional Quantitative Risk and Strategy Reviewer.

Your sole duty is to inspect trading strategies, backtest code, and quantitative models, looking for bugs, theoretical fallacies, and structural risks. You maintain a high bar and are extremely difficult to please.

Specifically, you look for:
1. Data Leakage / Lookahead Bias (e.g., using future information in entries, using indicators that shift back in time).
2. Overfitting (e.g., hyper-parameter tuning to noise, overly complex strategy rules).
3. Risk Management Issues (e.g., missing stop-loss controls, improper sizing, excessive leverage).
4. Unrealistic Assumptions (e.g., zero transaction costs, zero slippage, immediate market-order executions at exact close prices, unrealistic Sharpe ratios or win rates).

You MUST evaluate the input backtest and strategy and output your final critique ONLY in the following valid JSON format. Do not include any conversational text, markdown formatting (outside the JSON structure), or introductions.

Target JSON Schema:
{
  "agent": "CriticAgent",
  "verdict": "PASS" or "FAIL",
  "issues": [
    "Detailed description of issue 1",
    "Detailed description of issue 2"
  ],
  "suggestions": [
    "Practical solution/improvement 1",
    "Practical solution/improvement 2"
  ]
}"""

    async def critique(self, codegen_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Critiques a quantitative strategy backtest and analysis.
        
        Args:
            codegen_output (dict): Contains "research_analysis" and "generated_code".
            
        Returns:
            Dict[str, Any]: The structured risk review response.
        """
        research_analysis = codegen_output.get("research_analysis", {})
        generated_code = codegen_output.get("generated_code", {})

        prompt = f"""Review the following quantitative strategy and generated python backtest code:

--- RESEARCH ANALYSIS ---
{research_analysis.get('analysis')}

--- GENERATED BACKTEST CODE ---
{generated_code.get('code')}

--- SYMBOL ---
{research_analysis.get('raw_data', {}).get('symbol')}

Perform a strict quant audit on the methodology and code. Detail every issue, suggest fixes, and decide a PASS or FAIL verdict."""

        try:
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=prompt)
            ]

            response = await self.llm.ainvoke(messages)
            content = response.content.strip()

            # Clean and parse JSON from the LLM response
            parsed_critique = self._parse_json(content)
            return parsed_critique

        except Exception as e:
            return {
                "agent": "CriticAgent",
                "verdict": "FAIL",
                "issues": [f"An error occurred during risk review execution: {str(e)}"],
                "suggestions": ["Check client connectivity to Groq LLM API."]
            }

    def _parse_json(self, raw_content: str) -> Dict[str, Any]:
        # Try direct parse first
        try:
            return json.loads(raw_content)
        except json.JSONDecodeError:
            pass

        # Try to locate the JSON block inside any markdown or extra text
        json_match = re.search(r"\{.*\}", raw_content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        # Fallback if parsing fails
        return {
            "agent": "CriticAgent",
            "verdict": "FAIL",
            "issues": [
                "Could not parse the critic response as standard JSON.",
                f"Raw response dump: {raw_content[:300]}..."
            ],
            "suggestions": [
                "Ensure your system configuration utilizes a model that supports strict JSON output formats.",
                "Review potential network formatting or truncation errors."
            ]
        }
