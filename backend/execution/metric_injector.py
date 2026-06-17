"""Metric injection utilities for the sandboxed execution layer.

Appends vectorbt metric extraction code to a generated strategy script so
the executor can parse performance numbers from stdout without touching the
strategy logic itself.
"""

from __future__ import annotations

import ast
import logging
import textwrap

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sentinel used by the executor to locate the metrics line in stdout
# ---------------------------------------------------------------------------

METRICS_SENTINEL = "__METRICS_JSON__"

# ---------------------------------------------------------------------------
# Metric extraction snippet template
# ---------------------------------------------------------------------------

_EXTRACT_TEMPLATE = """

# ── Injected metric extraction (do not edit) ─────────────────────────────
import json as _json

def _extract_vbt_metrics(_pf):
    \"\"\"Pull key performance metrics from a vectorbt Portfolio object.\"\"\"
    _m = {{}}
    try:
        _m["sharpe_ratio"] = float(_pf.sharpe_ratio())
    except Exception:
        _m["sharpe_ratio"] = None
    try:
        _m["max_drawdown"] = float(_pf.max_drawdown())
    except Exception:
        _m["max_drawdown"] = None
    try:
        _m["cagr"] = float(_pf.annualized_return())
    except Exception:
        _m["cagr"] = None
    try:
        _m["win_rate"] = float(_pf.trades.win_rate())
    except Exception:
        _m["win_rate"] = None
    try:
        _m["total_trades"] = int(_pf.trades.count())
    except Exception:
        _m["total_trades"] = None
    try:
        _m["total_return"] = float(_pf.total_return())
    except Exception:
        _m["total_return"] = None
    return _m

try:
    _portfolio_var = {portfolio_var!r}
    _pf_obj = locals().get(_portfolio_var) or globals().get(_portfolio_var)
    if _pf_obj is None:
        raise NameError(f"Portfolio variable '{{_portfolio_var}}' not found")
    _metrics = _extract_vbt_metrics(_pf_obj)
    print("{sentinel}" + _json.dumps(_metrics))
except Exception as _exc:
    print("{sentinel}" + _json.dumps({{
        "sharpe_ratio": None,
        "max_drawdown": None,
        "cagr": None,
        "win_rate": None,
        "total_trades": None,
        "total_return": None,
        "_extraction_error": str(_exc),
    }}))
# ─────────────────────────────────────────────────────────────────────────
"""

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def inject_metrics_extraction(code: str) -> str:
    """Append vectorbt metric extraction logic to *code*.

    Detection strategy
    ------------------
    1. **Primary**: look for an assignment target named exactly ``portfolio``.
    2. **Fallback**: scan AST for the first assignment whose right-hand side
       contains a ``from_signals`` or ``vbt.Portfolio`` call and use that
       variable name.
    3. If nothing is found, default to ``"portfolio"`` (extraction will fail
       gracefully and emit null metrics).

    The injected code prints exactly one line to stdout matching::

        __METRICS_JSON__{...json...}

    Parameters
    ----------
    code : str
        Strategy source code (already sanitizer-approved).

    Returns
    -------
    str
        Original code with the extraction block appended.
    """
    portfolio_var = _detect_portfolio_variable(code)
    logger.debug("inject_metrics_extraction: detected portfolio var = %r", portfolio_var)

    snippet = _EXTRACT_TEMPLATE.format(
        portfolio_var=portfolio_var,
        sentinel=METRICS_SENTINEL,
    )
    return code + textwrap.dedent(snippet)


# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------


def _detect_portfolio_variable(code: str) -> str:
    """Return the name of the portfolio variable in *code*.

    Falls back to ``"portfolio"`` if detection fails.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return "portfolio"

    # Pass 1: look for a target named exactly "portfolio"
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "portfolio":
                    return "portfolio"

    # Pass 2: find first assignment whose RHS contains from_signals / vbt.Portfolio
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            rhs_str = ast.unparse(node.value)
            if "from_signals" in rhs_str or "vbt.Portfolio" in rhs_str:
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        return target.id

    # Default fallback
    return "portfolio"
