from langchain_core.messages import HumanMessage, SystemMessage
from backend.llm_client import get_groq_client
from backend.risk.engine import TradeValidator
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
        self.system_prompt = """You are an institutional quantitative risk committee reviewer operating inside a multi-agent AI trading pipeline.

You are adversarial, skeptical, conservative, and extremely difficult to impress. Your sole job is to audit trading strategies and backtests for structural weaknesses, unrealistic assumptions, and statistical credibility issues.

REVIEW AREAS - inspect for ALL of these:
1. Data leakage and lookahead bias
2. Overfitting and curve fitting
3. Missing or inadequate stop losses
4. Excessive leverage assumptions
5. Unrealistic execution assumptions
6. Missing transaction costs and slippage
7. Unrealistic Sharpe ratios
8. Unrealistic win rates
9. Regime fragility
10. Weak statistical significance
11. Insufficient backtest duration
12. Poor risk management
13. Market microstructure issues

MANDATORY RULES:
- Flag Sharpe ratio above 3.0 as suspicious
- Flag win rate above 70% as suspicious
- Flag backtests under 2 years duration
- Always provide minimum 3 issues even on PASS
- Distinguish fatal flaws from minor concerns using severity levels

SEVERITY LEVELS: every issue must include one of:
- fatal
- serious
- warning
- suspicious

OUTPUT REQUIREMENTS:
- Output ONLY valid JSON. No markdown. No explanations outside JSON.
- Use this EXACT schema:
{
  "agent": "CriticAgent",
  "verdict": "PASS" or "FAIL",
  "issues": [
    {
      "severity": "",
      "issue": ""
    }
  ],
  "suggestions": [
    "Suggestion 1",
    "Suggestion 2"
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

            parsed_critique = CriticAgent._parse_json(content)

            risk_flags = self._run_risk_checks(research_analysis, generated_code)

            if risk_flags:
                parsed_critique.setdefault("risk_flags", []).extend(risk_flags)
                parsed_critique["action"] = "HOLD"

                issues = parsed_critique.setdefault("issues", [])
                for flag in risk_flags:
                    issues.append({
                        "severity": "serious",
                        "issue": f"Risk check failed: {flag}"
                    })

                if parsed_critique.get("verdict") != "FAIL":
                    parsed_critique["verdict"] = "FAIL"

            return parsed_critique

        except Exception as e:
            return {
                "agent": "CriticAgent",
                "verdict": "FAIL",
                "issues": [f"An error occurred during risk review execution: {str(e)}"],
                "suggestions": ["Check client connectivity to Groq LLM API."]
            }

    def _run_risk_checks(
        self,
        research_analysis: Dict[str, Any],
        generated_code: Dict[str, Any]
    ) -> list[str]:
        """Run quantitative risk checks and return a list of flag messages."""
        flags: list[str] = []
        raw_data = research_analysis.get("raw_data", {})
        symbol = raw_data.get("symbol", "UNKNOWN")
        analysis = research_analysis.get("analysis", "")

        # Extract real trade parameters from raw payload data when available.
        raw_price = raw_data.get("price") or raw_data.get("current_price")
        entry_price = raw_price if isinstance(raw_price, (int, float)) else 0.0

        signal = {
            "symbol": symbol,
            "side": "BUY",
            "entry": entry_price,
            "stop": entry_price * 0.95 if entry_price > 0 else 0.0,
            "size": 100,
        }

        portfolio_state: Dict[str, Any] = {
            "equity_curve": [],
            "positions": {},
            "returns": None,
            "returns_list": [],
            "capital": 100_000.0,
        }

        validator = TradeValidator()
        approved, reasons = validator.validate(signal, portfolio_state)
        if not approved:
            flags.extend(reasons)

        # Check if the research itself mentions high-risk patterns
        risk_keywords = [
            "high leverage", "no stop", "overfit", "lookahead",
            "survivorship", "data snooping",
        ]
        analysis_lower = analysis.lower() if analysis else ""
        if any(kw in analysis_lower for kw in risk_keywords):
            for kw in risk_keywords:
                if kw in analysis_lower:
                    flags.append(f"Research analysis mentions risk pattern: '{kw}'")

        return flags

    @staticmethod
    def _parse_json(raw_content: str) -> Dict[str, Any]:
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
                {"severity": "fatal", "issue": "Could not parse the critic response as standard JSON."},
                {"severity": "warning", "issue": f"Raw response dump: {raw_content[:300]}..."}
            ],
            "suggestions": [
                "Ensure your system configuration utilizes a model that supports strict JSON output formats.",
                "Review potential network formatting or truncation errors."
            ]
        }
