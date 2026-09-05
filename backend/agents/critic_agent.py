from langchain_core.messages import HumanMessage, SystemMessage
from backend.llm_client import get_groq_client
from backend.risk.engine import TradeValidator
import json
import re
from typing import Dict, Any, Optional

# ---------------------------------------------------------------------------
# Real-signal parsing helpers
# ---------------------------------------------------------------------------

# Hypothesis JSON keys that may carry the stop-loss level (in priority order).
_STOP_LEVEL_KEYS = ("stop_loss_level", "stop_loss", "stop")

# Code markers indicating an explicit stop-loss implementation in generated code.
_STOP_CODE_MARKERS = ("sl_stop", "stop_loss", "stop-loss", "stoploss", "trailing")


def _extract_stop_level(analysis: str, entry_price: float) -> float | None:
    """Parse a numeric stop-loss price from the research hypothesis JSON.

    Returns ``None`` when the hypothesis defines no machine-readable stop
    (non-JSON prose, missing key, or unparseable/non-positive value). A
    stop at or above a known entry price is rejected — it cannot protect
    a long position.
    """
    if not isinstance(analysis, str) or not analysis:
        return None
    try:
        payload = json.loads(analysis)
    except (json.JSONDecodeError, TypeError):
        match = re.search(r"\{.*\}", analysis, re.DOTALL)
        if not match:
            return None
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    if not isinstance(payload, dict):
        return None
    for key in _STOP_LEVEL_KEYS:
        raw = payload.get(key)
        if raw is None:
            continue
        num = re.search(r"\$?\s*(\d+(?:\.\d+)?)", str(raw))
        if not num:
            continue
        try:
            stop = float(num.group(1))
        except ValueError:
            continue
        if stop <= 0:
            continue
        if entry_price > 0 and stop >= entry_price:
            continue
        return stop
    return None


def _code_has_stop(code: str) -> bool:
    """Return True when *code* contains an explicit stop-loss implementation."""
    if not isinstance(code, str) or not code:
        return False
    lowered = code.lower()
    return any(marker in lowered for marker in _STOP_CODE_MARKERS)


class CriticAgent:
    """
    Skeptical, risk-focused institutional quant reviewer agent.
    Checks generated code and trading strategy logic for:
      - Lookahead bias / data leakage
      - Overfitting / curve fitting
      - Unrealistic transaction costs or slippage
      - Inadequate risk controls or missing stop-losses
      - Unrealistic returns or win rate expectations
      - Execution failures (sanitizer rejections, timeouts, runtime errors)
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

    async def critique(
        self,
        codegen_output: Dict[str, Any],
        execution_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Critiques a quantitative strategy backtest and analysis.

        Args:
            codegen_output (dict): Contains "research_analysis" and "generated_code".
            execution_result (dict | None): Serialized ExecutionResult from the
                sandboxed executor.  When provided, its status and metrics are
                folded into the prompt and used to enforce deterministic FAILs.

        Returns:
            Dict[str, Any]: The structured risk review response, extended with
                ``execution_status`` when execution_result is supplied.
        """
        research_analysis = codegen_output.get("research_analysis", {})
        generated_code = codegen_output.get("generated_code", {})

        # ── Execution-aware context block ────────────────────────────────────
        execution_status: Optional[str] = None
        execution_context_block = ""
        if execution_result:
            execution_status = execution_result.get("status")
            sharpe = execution_result.get("sharpe_ratio")
            max_dd = execution_result.get("max_drawdown")
            total_trades = execution_result.get("total_trades")
            total_return = execution_result.get("total_return")
            error_msg = execution_result.get("error_msg")

            execution_context_block = f"""
--- EXECUTION RESULT ---
Status          : {execution_status}
Sharpe Ratio    : {sharpe}
Max Drawdown    : {max_dd}
Total Trades    : {total_trades}
Total Return    : {total_return}
Error Message   : {error_msg or 'None'}
"""

        prompt = f"""Review the following quantitative strategy and generated python backtest code:

--- RESEARCH ANALYSIS ---
{research_analysis.get('analysis')}

--- GENERATED BACKTEST CODE ---
{generated_code.get('code')}

--- SYMBOL ---
{research_analysis.get('raw_data', {}).get('symbol')}
{execution_context_block}
Perform a strict quant audit on the methodology and code. Detail every issue, suggest fixes, and decide a PASS or FAIL verdict."""

        try:
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=prompt)
            ]

            response = await self.llm.ainvoke(messages)
            content = response.content.strip()

            parsed_critique = CriticAgent._parse_json(content)

            risk_flags = self._run_risk_checks(
                research_analysis, generated_code, execution_result
            )

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

            # ── Deterministic FAIL for non-SUCCESS execution statuses ─────────
            if execution_status and execution_status not in ("SUCCESS", "LOW_SAMPLE"):
                parsed_critique["verdict"] = "FAIL"
                parsed_critique.setdefault("issues", []).insert(0, {
                    "severity": "fatal",
                    "issue": (
                        f"Backtest execution failed with status '{execution_status}'. "
                        f"The generated code did not run successfully and cannot be approved."
                    ),
                })

            # ── LOW_SAMPLE: flag as serious warning, don't auto-FAIL ─────────
            if execution_status == "LOW_SAMPLE":
                parsed_critique.setdefault("issues", []).insert(0, {
                    "severity": "serious",
                    "issue": (
                        "Execution completed but total_trades < 20 — "
                        "statistical significance is too low to trust backtest results."
                    ),
                })

            # ── Attach execution_status to response ───────────────────────────
            if execution_status is not None:
                parsed_critique["execution_status"] = execution_status

            return parsed_critique

        except Exception as e:
            return {
                "agent": "CriticAgent",
                "verdict": "FAIL",
                "issues": [f"An error occurred during risk review execution: {str(e)}"],
                "suggestions": ["Check client connectivity to Groq LLM API."],
            }

    def _run_risk_checks(
        self,
        research_analysis: Dict[str, Any],
        generated_code: Dict[str, Any],
        execution_result: Optional[Dict[str, Any]] = None,
    ) -> list[str]:
        """Run quantitative risk checks and return a list of flag messages.

        All checks run against real pipeline artifacts — never placeholders:

        - signal entry/stop come from the research payload and hypothesis;
        - the equity curve is seeded from the measured backtest drawdown;
        - trade count and stop-loss presence are read from the execution
          result, hypothesis JSON, and generated code respectively.
        """
        flags: list[str] = []
        raw_data = research_analysis.get("raw_data", {}) or {}
        symbol = raw_data.get("symbol", "UNKNOWN")
        analysis = research_analysis.get("analysis", "") or ""
        code = generated_code.get("code", "") or ""

        # Real entry price from the research payload.
        raw_price = raw_data.get("price") or raw_data.get("current_price")
        entry_price = raw_price if isinstance(raw_price, (int, float)) else 0.0

        # Real stop-loss level parsed from the research hypothesis JSON.
        # Falls back to a 5 % protective stop only for validator input —
        # a missing hypothesis stop is still flagged below.
        stop_price = _extract_stop_level(analysis, entry_price)

        signal = {
            "symbol": symbol,
            "side": "BUY",  # CodeGen only emits long vectorbt strategies
            "entry": entry_price,
            "stop": (
                stop_price
                if stop_price is not None
                else (entry_price * 0.95 if entry_price > 0 else 0.0)
            ),
            "size": 100,  # default; TradeValidator enforces portfolio-level limits
        }

        # Real portfolio state: seed the equity curve from the measured
        # backtest drawdown so the max-drawdown check evaluates real data.
        # Without an execution result the curve stays empty and the check
        # passes vacuously, as before.
        equity_curve: list[float] = []
        if execution_result:
            max_dd = execution_result.get("max_drawdown")
            if isinstance(max_dd, (int, float)) and max_dd > 0:
                equity_curve = [1.0, 1.0 - float(max_dd)]

        portfolio_state: Dict[str, Any] = {
            "equity_curve": equity_curve,
            "positions": {},
            "returns": None,
            "returns_list": [],
            "capital": 100_000.0,
        }

        validator = TradeValidator()
        approved, reasons = validator.validate(signal, portfolio_state)
        if not approved:
            flags.extend(reasons)

        # Real trade-count check against the pipeline minimum. LOW_SAMPLE is
        # deliberately skipped — critique() already reports it as a serious
        # issue without forcing FAIL, and this must not override that choice.
        if execution_result and execution_result.get("status") == "SUCCESS":
            total_trades = execution_result.get("total_trades")
            min_trades = validator.config.min_trade_count
            if isinstance(total_trades, int) and total_trades < min_trades:
                flags.append(
                    f"Backtest produced {total_trades} trades, "
                    f"below minimum {min_trades}"
                )

        # Real stop-loss presence check across both artifacts.
        if stop_price is None and not _code_has_stop(code):
            flags.append(
                "No explicit stop-loss detected in research hypothesis "
                "or generated code"
            )

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
