"""Sandboxed backtest executor.

Runs generated strategy code in an isolated subprocess with:
  - AST sanitization (no subprocess spawned for unsafe code)
  - metric injection via stdout sentinel
  - configurable asyncio timeout with process kill
  - LOW_SAMPLE override when trade count < 20

Usage
-----
    result = await execute_backtest(code, timeout=30)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import tempfile
from pathlib import Path

from backend.execution.metric_injector import METRICS_SENTINEL, inject_metrics_extraction
from backend.execution.models import ExecutionResult, ExecutionStatus
from backend.execution.sanitizer import sanitize_code

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_DEFAULT_TIMEOUT: int = int(os.getenv("EXECUTOR_TIMEOUT_SECONDS", "30"))
_LOW_SAMPLE_THRESHOLD: int = 20

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def execute_backtest(
    code: str,
    timeout: int = _DEFAULT_TIMEOUT,
) -> ExecutionResult:
    """Execute a vectorbt strategy in a sandboxed subprocess.

    Parameters
    ----------
    code : str
        Python source code of the generated trading strategy.
    timeout : int
        Maximum wall-clock seconds to allow before killing the process.
        Reads ``EXECUTOR_TIMEOUT_SECONDS`` env var; defaults to 30.

    Returns
    -------
    ExecutionResult
        Always returns a result — never raises.

    Flow
    ----
    1. ``sanitize_code()`` — reject immediately if unsafe (no subprocess).
    2. ``inject_metrics_extraction()`` — append stdout sentinel block.
    3. Write to a NamedTemporaryFile.
    4. ``asyncio.create_subprocess_exec`` with PIPE stdout/stderr.
    5. ``asyncio.wait_for`` with *timeout*; kill process on expiry.
    6. Parse ``__METRICS_JSON__`` from stdout.
    7. Override with ``LOW_SAMPLE`` if ``total_trades < 20``.
    8. Always delete temp file in ``finally``.
    """
    # ── Step 1: Sanitize ──────────────────────────────────────────────────
    is_safe, violation = sanitize_code(code)
    if not is_safe:
        logger.warning("execute_backtest: sanitizer rejected — %s", violation)
        return ExecutionResult(
            status=ExecutionStatus.SANITIZER_REJECTED,
            error_msg=violation,
        )

    # ── Step 2: Inject metrics extraction ────────────────────────────────
    instrumented_code = inject_metrics_extraction(code)

    # ── Step 3: Write temp script ─────────────────────────────────────────
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8",
        ) as tmp:
            tmp.write(instrumented_code)
            tmp_path = Path(tmp.name)

        logger.debug("execute_backtest: temp script written to %s", tmp_path)

        # ── Step 4 & 5: Subprocess + timeout ──────────────────────────────
        try:
            result = await asyncio.wait_for(
                _run_subprocess(tmp_path),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logger.warning("execute_backtest: timeout after %ds", timeout)
            return ExecutionResult(
                status=ExecutionStatus.TIMEOUT,
                error_msg=f"Execution exceeded {timeout}s timeout and was killed.",
            )

        stdout_text, stderr_text, return_code = result

        # ── Step 6: Parse stdout ──────────────────────────────────────────
        if return_code != 0:
            logger.warning("execute_backtest: subprocess exited %d", return_code)
            return ExecutionResult(
                status=ExecutionStatus.RUNTIME_ERROR,
                error_msg=_trim(stderr_text or stdout_text),
            )

        metrics = _parse_metrics(stdout_text)
        if metrics is None:
            logger.warning("execute_backtest: sentinel not found in stdout")
            return ExecutionResult(
                status=ExecutionStatus.PARSE_ERROR,
                error_msg=_trim(stderr_text) or "Metrics sentinel not found in output.",
            )

        # ── Step 7: LOW_SAMPLE override ───────────────────────────────────
        total_trades: int | None = metrics.get("total_trades")
        status = ExecutionStatus.SUCCESS
        if total_trades is not None and total_trades < _LOW_SAMPLE_THRESHOLD:
            status = ExecutionStatus.LOW_SAMPLE
            logger.info(
                "execute_backtest: LOW_SAMPLE (%d trades < %d)",
                total_trades,
                _LOW_SAMPLE_THRESHOLD,
            )

        return ExecutionResult(
            status=status,
            sharpe_ratio=metrics.get("sharpe_ratio"),
            max_drawdown=metrics.get("max_drawdown"),
            cagr=metrics.get("cagr"),
            win_rate=metrics.get("win_rate"),
            total_trades=total_trades,
            total_return=metrics.get("total_return"),
            error_msg=_trim(stderr_text) or None,
        )

    except Exception as exc:
        logger.exception("execute_backtest: unexpected exception")
        return ExecutionResult(
            status=ExecutionStatus.RUNTIME_ERROR,
            error_msg=str(exc),
        )

    finally:
        # ── Step 8: Always clean up temp file ─────────────────────────────
        if tmp_path is not None and tmp_path.exists():
            try:
                tmp_path.unlink()
                logger.debug("execute_backtest: deleted temp file %s", tmp_path)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


async def _run_subprocess(
    script_path: Path,
) -> tuple[str, str, int]:
    """Spawn *script_path* in a subprocess and return (stdout, stderr, returncode).

    The caller is responsible for applying a timeout via ``asyncio.wait_for``.
    """
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        str(script_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_bytes, stderr_bytes = await proc.communicate()
    return (
        stdout_bytes.decode("utf-8", errors="replace"),
        stderr_bytes.decode("utf-8", errors="replace"),
        proc.returncode or 0,
    )


def _parse_metrics(stdout: str) -> dict | None:
    """Extract the JSON metrics dict from *stdout*.

    Returns ``None`` if the sentinel line is not present or JSON is malformed.
    """
    for line in stdout.splitlines():
        if line.startswith(METRICS_SENTINEL):
            payload = line[len(METRICS_SENTINEL):]
            try:
                data = json.loads(payload)
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                return None
    return None


def _trim(text: str, max_chars: int = 2000) -> str:
    """Truncate *text* to *max_chars* to avoid bloating the result model."""
    if not text:
        return ""
    text = text.strip()
    return text if len(text) <= max_chars else text[:max_chars] + "\n... (truncated)"
