"""Data models for the sandboxed execution layer.

Defines ``ExecutionStatus`` (enum) and ``ExecutionResult`` (Pydantic model)
consumed by ``executor.execute_backtest``.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Status Enum
# ---------------------------------------------------------------------------


class ExecutionStatus(str, Enum):
    """Represents the outcome of a sandboxed backtest run."""

    SUCCESS = "SUCCESS"
    """Execution completed and all metrics were parsed successfully."""

    LOW_SAMPLE = "LOW_SAMPLE"
    """Execution completed but total_trades < 20 — results are unreliable."""

    TIMEOUT = "TIMEOUT"
    """The subprocess exceeded the configured timeout and was killed."""

    SANITIZER_REJECTED = "SANITIZER_REJECTED"
    """AST analysis detected forbidden imports or function calls."""

    RUNTIME_ERROR = "RUNTIME_ERROR"
    """The subprocess exited with a non-zero return code."""

    PARSE_ERROR = "PARSE_ERROR"
    """The sentinel line was not found in stdout or JSON was malformed."""


# ---------------------------------------------------------------------------
# Execution Result Model
# ---------------------------------------------------------------------------


class ExecutionResult(BaseModel):
    """Structured result returned by ``execute_backtest``."""

    status: ExecutionStatus = Field(..., description="Outcome of the execution.")

    sharpe_ratio: Optional[float] = Field(
        None, description="Annualised Sharpe ratio of the strategy."
    )
    max_drawdown: Optional[float] = Field(
        None, description="Maximum peak-to-trough drawdown (fraction, e.g. 0.15 = 15%)."
    )
    cagr: Optional[float] = Field(
        None, description="Compounded annual growth rate (annualized_return)."
    )
    win_rate: Optional[float] = Field(
        None, description="Fraction of trades that were profitable."
    )
    total_trades: Optional[int] = Field(
        None, description="Total number of closed trades."
    )
    total_return: Optional[float] = Field(
        None, description="Total return over the backtest period (fraction)."
    )
    error_msg: Optional[str] = Field(
        None, description="Error message or stderr output when execution fails."
    )

    class Config:
        use_enum_values = True
