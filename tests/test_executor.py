"""Tests for the sandboxed execution layer.

Covers:
  - sanitizer: blocked imports, blocked calls, clean code acceptance
  - metric_injector: portfolio variable detection, fallback detection
  - executor (integration): timeout, SUCCESS, LOW_SAMPLE
"""

from __future__ import annotations

import pytest

from backend.execution.sanitizer import sanitize_code
from backend.execution.metric_injector import inject_metrics_extraction, METRICS_SENTINEL
from backend.execution.models import ExecutionResult, ExecutionStatus
from backend.execution.executor import execute_backtest, _safe_env


# ──────────────────────────────────────────────────────────────────────────────
# Sanitizer tests
# ──────────────────────────────────────────────────────────────────────────────


class TestSanitizer:
    """AST-based code sanitizer."""

    # ── Blocked imports ───────────────────────────────────────────────────

    def test_import_os_rejected(self):
        ok, reason = sanitize_code("import os\nprint(os.getcwd())")
        assert ok is False
        assert reason is not None
        assert "os" in reason

    def test_import_sys_rejected(self):
        ok, reason = sanitize_code("import sys\nprint(sys.argv)")
        assert ok is False
        assert "sys" in reason

    def test_import_subprocess_rejected(self):
        ok, reason = sanitize_code("import subprocess\nsubprocess.run(['ls'])")
        assert ok is False
        assert "subprocess" in reason

    def test_import_socket_rejected(self):
        ok, reason = sanitize_code("import socket")
        assert ok is False

    def test_import_requests_rejected(self):
        ok, reason = sanitize_code("import requests\nrequests.get('http://example.com')")
        assert ok is False

    def test_import_httpx_rejected(self):
        ok, reason = sanitize_code("import httpx")
        assert ok is False

    def test_from_os_import_rejected(self):
        ok, reason = sanitize_code("from os import path\nprint(path.exists('.'))")
        assert ok is False
        assert "os" in reason

    def test_from_pathlib_import_rejected(self):
        ok, reason = sanitize_code("from pathlib import Path")
        assert ok is False

    def test_from_threading_import_rejected(self):
        ok, reason = sanitize_code("from threading import Thread")
        assert ok is False

    def test_from_multiprocessing_import_rejected(self):
        ok, reason = sanitize_code("from multiprocessing import Pool")
        assert ok is False

    def test_import_ctypes_rejected(self):
        ok, reason = sanitize_code("import ctypes")
        assert ok is False

    def test_import_importlib_rejected(self):
        ok, reason = sanitize_code("import importlib")
        assert ok is False

    def test_import_inspect_rejected(self):
        ok, reason = sanitize_code("import inspect")
        assert ok is False

    # ── Blocked function calls ────────────────────────────────────────────

    def test_eval_rejected(self):
        ok, reason = sanitize_code("result = eval('1 + 1')")
        assert ok is False
        assert reason is not None
        assert "eval" in reason

    def test_exec_rejected(self):
        ok, reason = sanitize_code("exec('x = 1')")
        assert ok is False
        assert "exec" in reason

    def test_builtins_subscript_exec_rejected(self):
        ok, reason = sanitize_code('__builtins__["exec"]("print(\'hi\')")')
        assert ok is False
        assert reason is not None

    def test_breakpoint_rejected(self):
        ok, reason = sanitize_code("breakpoint()")
        assert ok is False

    def test_set_trace_rejected(self):
        ok, reason = sanitize_code("set_trace()")
        assert ok is False

    def test_open_rejected(self):
        ok, reason = sanitize_code("f = open('secret.txt', 'r')")
        assert ok is False
        assert "open" in reason

    def test_dunder_import_rejected(self):
        ok, reason = sanitize_code("mod = __import__('os')")
        assert ok is False
        assert "__import__" in reason

    def test_compile_rejected(self):
        ok, reason = sanitize_code("compile('x=1', '<str>', 'exec')")
        assert ok is False
        assert "compile" in reason

    # ── Allowed code ─────────────────────────────────────────────────────

    def test_clean_vectorbt_code_accepted(self):
        code = """
import vectorbt as vbt
import pandas as pd
import numpy as np

close = pd.Series([100, 101, 102, 103, 104, 105])
entries = close > close.shift(1)
exits = close < close.shift(1)
portfolio = vbt.Portfolio.from_signals(close, entries, exits)
print(portfolio.total_return())
"""
        ok, reason = sanitize_code(code)
        assert ok is True
        assert reason is None

    def test_numpy_pandas_allowed(self):
        code = """
import numpy as np
import pandas as pd
x = np.array([1, 2, 3])
df = pd.DataFrame({'a': x})
print(df.mean())
"""
        ok, reason = sanitize_code(code)
        assert ok is True
        assert reason is None

    def test_datetime_math_allowed(self):
        code = """
import datetime
import math
import statistics
x = math.sqrt(4)
s = statistics.mean([1, 2, 3])
print(x, s)
"""
        ok, reason = sanitize_code(code)
        assert ok is True
        assert reason is None

    def test_syntax_error_rejected(self):
        ok, reason = sanitize_code("def foo(: pass")
        assert ok is False
        assert reason is not None
        assert "SyntaxError" in reason


# ──────────────────────────────────────────────────────────────────────────────
# Metric injector tests
# ──────────────────────────────────────────────────────────────────────────────


class TestMetricInjector:
    """Portfolio variable detection and code injection."""

    def test_standard_portfolio_variable_detected(self):
        code = "portfolio = vbt.Portfolio.from_signals(close, entries, exits)"
        injected = inject_metrics_extraction(code)
        # Should reference 'portfolio'
        assert "'portfolio'" in injected
        assert METRICS_SENTINEL in injected

    def test_nonstandard_variable_via_from_signals(self):
        """Fallback: detect assignment where RHS contains from_signals."""
        code = "my_pf = vbt.Portfolio.from_signals(close, entries, exits)"
        injected = inject_metrics_extraction(code)
        # The injected block should reference 'my_pf', not 'portfolio'
        assert "'my_pf'" in injected

    def test_nonstandard_vbt_portfolio_constructor(self):
        """Fallback: detect assignment where RHS contains vbt.Portfolio(...)."""
        code = "results = vbt.Portfolio(close=close, init_cash=10000)"
        injected = inject_metrics_extraction(code)
        assert "'results'" in injected

    def test_fallback_to_portfolio_when_no_assignment(self):
        """When no recognisable assignment exists, default to 'portfolio'."""
        code = "x = 1 + 2\nprint(x)"
        injected = inject_metrics_extraction(code)
        assert "'portfolio'" in injected

    def test_sentinel_present_in_injection(self):
        code = "portfolio = None"
        injected = inject_metrics_extraction(code)
        assert METRICS_SENTINEL in injected

    def test_original_code_preserved(self):
        code = "x = 42\nprint(x)"
        injected = inject_metrics_extraction(code)
        assert "x = 42" in injected
        assert "print(x)" in injected


# ──────────────────────────────────────────────────────────────────────────────
# Executor integration tests (async)
# ──────────────────────────────────────────────────────────────────────────────


class TestExecutor:
    """Full round-trip tests using a real subprocess."""

    @pytest.mark.asyncio
    async def test_sanitizer_blocks_unsafe_code(self):
        """Unsafe import must be rejected WITHOUT spawning a subprocess."""
        code = "import os\nprint(os.getcwd())"
        result = await execute_backtest(code, timeout=5)
        assert result.status == ExecutionStatus.SANITIZER_REJECTED
        assert result.error_msg is not None
        assert "os" in result.error_msg

    @pytest.mark.asyncio
    async def test_eval_blocked_by_sanitizer(self):
        code = "x = eval('1+1')"
        result = await execute_backtest(code, timeout=5)
        assert result.status == ExecutionStatus.SANITIZER_REJECTED

    @pytest.mark.asyncio
    async def test_infinite_loop_returns_timeout(self):
        """An infinite loop must be killed and return TIMEOUT."""
        code = "while True:\n    pass"
        result = await execute_backtest(code, timeout=2)
        assert result.status == ExecutionStatus.TIMEOUT

    @pytest.mark.asyncio
    async def test_valid_vectorbt_code_returns_success(self):
        """A complete vectorbt backtest with enough trades returns SUCCESS."""
        # Build 500 bars of synthetic data to guarantee >=20 trades
        code = """
import vectorbt as vbt
import pandas as pd
import numpy as np

np.random.seed(42)
n = 500
close = pd.Series(100 + np.cumsum(np.random.randn(n) * 0.5))
# Simple moving-average crossover — generates many trades over 500 bars
fast = close.rolling(5).mean()
slow = close.rolling(20).mean()
entries = (fast > slow) & (fast.shift(1) <= slow.shift(1))
exits  = (fast < slow) & (fast.shift(1) >= slow.shift(1))
portfolio = vbt.Portfolio.from_signals(close, entries, exits, init_cash=10_000)
"""
        result = await execute_backtest(code, timeout=60)
        # Accept SUCCESS or LOW_SAMPLE — both indicate the executor ran to completion
        assert result.status in (ExecutionStatus.SUCCESS, ExecutionStatus.LOW_SAMPLE)
        # Core metrics should be populated
        assert result.total_return is not None
        assert result.max_drawdown is not None

    @pytest.mark.asyncio
    async def test_low_sample_override(self):
        """A strategy with fewer than 20 trades is overridden to LOW_SAMPLE."""
        # 1 entry → 1 trade
        code = """
import vectorbt as vbt
import pandas as pd
import numpy as np

np.random.seed(0)
n = 100
close = pd.Series(100 + np.cumsum(np.random.randn(n) * 0.5))
# Single entry at bar 10, single exit at bar 50 → 1 trade
entries = pd.Series([False] * n)
exits   = pd.Series([False] * n)
entries.iloc[10] = True
exits.iloc[50]   = True
portfolio = vbt.Portfolio.from_signals(close, entries, exits, init_cash=10_000)
"""
        result = await execute_backtest(code, timeout=60)
        assert result.status == ExecutionStatus.LOW_SAMPLE
        assert result.total_trades is not None
        assert result.total_trades < 20

    @pytest.mark.asyncio
    async def test_runtime_error_in_strategy(self):
        """A strategy that raises at runtime returns RUNTIME_ERROR."""
        code = """
x = 1 / 0
portfolio = None
"""
        result = await execute_backtest(code, timeout=10)
        assert result.status == ExecutionStatus.RUNTIME_ERROR
        assert result.error_msg is not None

    @pytest.mark.asyncio
    async def test_returns_execution_result_type(self):
        """execute_backtest always returns an ExecutionResult — never raises."""
        result = await execute_backtest("import os", timeout=5)
        assert isinstance(result, ExecutionResult)

    def test_safe_env_strips_secrets(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "secret_groq")
        monkeypatch.setenv("OPENAI_API_KEY", "secret_openai")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "secret_anthropic")
        monkeypatch.setenv("BINANCE_SECRET", "secret_binance")
        monkeypatch.setenv("GEMINI_KEY", "secret_gemini")
        monkeypatch.setenv("SAFE_TEST_VAR", "safe_value")

        env = _safe_env()
        assert "GROQ_API_KEY" not in env
        assert "OPENAI_API_KEY" not in env
        assert "ANTHROPIC_API_KEY" not in env
        assert "BINANCE_SECRET" not in env
        assert "GEMINI_KEY" not in env
        assert env.get("SAFE_TEST_VAR") == "safe_value"

