"""Risk management engine for the Agentic Quant Sandbox.

Provides position sizing (Kelly, fixed fraction, volatility-adjusted),
risk checking (drawdown, concentration, correlation, VaR, CVaR),
and trade validation that integrates with the CriticAgent.
"""

from __future__ import annotations

import math
import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────


@dataclass
class RiskConfig:
    """Global risk parameters.

    All thresholds are expressed as decimals (0.05 = 5 %) unless noted.
    """

    max_position_pct: float = 0.20
    max_drawdown_pct: float = 0.25
    max_var_1d: float = 0.02
    max_correlation: float = 0.85
    kelly_cap: float = 0.25
    default_confidence: float = 0.95
    min_trade_count: int = 30


# Singleton-ish default; callers can override by passing a custom config.
DEFAULT_CONFIG = RiskConfig()


# ──────────────────────────────────────────────────────────────────────
# Position Sizer
# ──────────────────────────────────────────────────────────────────────


class PositionSizer:
    """Determines how many shares/contracts to trade."""

    @staticmethod
    def kelly_fraction(
        win_rate: float, avg_win: float, avg_loss: float, cap: float = 0.25
    ) -> float:
        """Full Kelly formula, capped at *cap* (default 25 %).

        Parameters
        ----------
        win_rate : float
            Fraction of winning trades (0..1).
        avg_win : float
            Average gross return of winning trades (e.g. 1.05 means +5 %).
        avg_loss : float
            Average gross return of losing trades (e.g. 0.95 means -5 %).
        cap : float
            Maximum fraction of capital to risk.

        Returns
        -------
        float
            Fraction of capital to allocate.
        """
        if win_rate <= 0.0 or win_rate >= 1.0:
            return 0.0
        if avg_loss <= 0 or avg_win <= 0:
            return 0.0

        # R = win / loss (net returns)
        r = (avg_win - 1.0) / (1.0 - avg_loss) if (1.0 - avg_loss) > 0 else 0.0
        kelly = win_rate - (1.0 - win_rate) / r if r > 0 else 0.0
        return max(0.0, min(kelly, cap))

    @staticmethod
    def fixed_fraction(
        capital: float, risk_pct: float, entry: float, stop: float
    ) -> int:
        """Fixed-fraction position sizing.

        Risks *risk_pct* of *capital* on the trade.

        Returns
        -------
        int
            Number of shares / contracts.
        """
        if entry <= 0 or stop <= 0 or capital <= 0 or risk_pct <= 0:
            return 0
        risk_per_share = abs(entry - stop)
        if risk_per_share < 1e-12:
            return 0
        dollars_at_risk = capital * risk_pct
        return max(0, int(dollars_at_risk / risk_per_share))

    @staticmethod
    def volatility_adjusted(
        capital: float, atr: float, risk_pct: float, entry: float
    ) -> int:
        """ATR-based position sizing.

        Uses average true range as a volatility gauge to normalise risk.

        Returns
        -------
        int
            Number of shares / contracts.
        """
        if entry <= 0 or atr <= 0 or capital <= 0 or risk_pct <= 0:
            return 0
        dollars_at_risk = capital * risk_pct
        volatility_risk = atr / entry  # fraction of price
        if volatility_risk < 1e-12:
            return 0
        return max(0, int(dollars_at_risk / (entry * volatility_risk)))


# ──────────────────────────────────────────────────────────────────────
# Risk Checker
# ──────────────────────────────────────────────────────────────────────


class RiskChecker:
    """Performs quantitative risk checks on portfolios and strategies."""

    @staticmethod
    def check_max_drawdown(
        equity_curve: list[float], max_dd_pct: float = 0.25
    ) -> tuple[bool, float]:
        """Check whether drawdown exceeds *max_dd_pct*.

        Returns
        -------
        (is_ok: bool, current_drawdown: float)
        """
        if not equity_curve:
            return True, 0.0
        peak = equity_curve[0]
        max_dd = 0.0
        for val in equity_curve:
            if val > peak:
                peak = val
            dd = (peak - val) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd
        return max_dd <= max_dd_pct, max_dd

    @staticmethod
    def check_position_concentration(
        positions: dict[str, float], max_single_pct: float = 0.20
    ) -> list[str]:
        """Return list of symbol keys whose allocation exceeds *max_single_pct*."""
        total = sum(positions.values()) if positions else 1.0
        if total <= 0:
            total = 1.0
        return [sym for sym, val in positions.items() if (val / total) > max_single_pct]

    @staticmethod
    def check_correlation(
        returns_df: pd.DataFrame, max_corr: float = 0.85
    ) -> list[tuple[str, str, float]]:
        """Return list of (sym_a, sym_b, correlation) for pairs exceeding threshold."""
        if returns_df.shape[1] < 2:
            return []
        corr = returns_df.corr()
        pairs: list[tuple[str, str, float]] = []
        cols = corr.columns.tolist()
        for i, a in enumerate(cols):
            for b in cols[i + 1 :]:
                val = abs(corr.loc[a, b])
                if val > max_corr:
                    pairs.append((a, b, round(val, 4)))
        return pairs

    @staticmethod
    def var_historical(
        returns: list[float], confidence: float = 0.95
    ) -> float:
        """Historical Value-at-Risk.

        Returns the loss (positive number) that is not exceeded at the given
        confidence level.
        """
        if not returns:
            return 0.0
        arr = np.sort(np.array(returns))
        index = max(0, int((1.0 - confidence) * len(arr)))
        return abs(arr[index]) if index < len(arr) else 0.0

    @staticmethod
    def cvar_historical(
        returns: list[float], confidence: float = 0.95
    ) -> float:
        """Conditional VaR (Expected Shortfall).

        Average loss beyond the VaR threshold.
        """
        if not returns:
            return 0.0
        arr = np.sort(np.array(returns))
        index = max(0, int((1.0 - confidence) * len(arr)))
        if index == 0:
            return abs(arr[0])
        tail = arr[:index]
        if len(tail) == 0:
            return 0.0
        return abs(float(np.mean(tail)))


# ──────────────────────────────────────────────────────────────────────
# Trade Validator
# ──────────────────────────────────────────────────────────────────────


class TradeValidator:
    """Validates a trading signal against portfolio state and risk limits."""

    def __init__(self, config: RiskConfig | None = None):
        self.config = config or DEFAULT_CONFIG

    def validate(
        self,
        signal: dict[str, Any],
        portfolio_state: dict[str, Any],
        config: RiskConfig | None = None,
    ) -> tuple[bool, list[str]]:
        """Run all configured risk checks on a proposed signal.

        Parameters
        ----------
        signal : dict
            Must contain at least ``symbol``, ``side`` (``"BUY"`` / ``"SELL"``),
            ``entry``, ``stop``, and ``size``.
        portfolio_state : dict
            Optional keys: ``equity_curve``, ``positions``, ``returns``,
            ``capital``, ``current_drawdown``.
        config : RiskConfig, optional
            Override the instance-level config for this single call.

        Returns
        -------
        (approved: bool, reasons: list[str])
        """
        cfg = config or self.config
        reasons: list[str] = []
        symbol = signal.get("symbol", "UNKNOWN")
        side = signal.get("side", "BUY")

        # ── 1.  Position size limit ────────────────────────────────────
        positions: dict[str, float] = portfolio_state.get("positions", {})
        breaching = RiskChecker.check_position_concentration(
            positions, cfg.max_position_pct
        )
        if symbol in breaching:
            reasons.append(
                f"Position concentration breach for {symbol}: "
                f"exceeds {cfg.max_position_pct:.0%} limit"
            )

        # ── 2.  Drawdown check ────────────────────────────────────────
        equity_curve: list[float] = portfolio_state.get("equity_curve", [])
        dd_ok, current_dd = RiskChecker.check_max_drawdown(
            equity_curve, cfg.max_drawdown_pct
        )
        if not dd_ok:
            reasons.append(
                f"Max drawdown {current_dd:.1%} exceeds limit {cfg.max_drawdown_pct:.0%}"
            )

        # ── 3.  Correlation check ─────────────────────────────────────
        returns_df: pd.DataFrame | None = portfolio_state.get("returns")
        if returns_df is not None and not returns_df.empty:
            high_corr = RiskChecker.check_correlation(returns_df, cfg.max_correlation)
            for a, b, corr_val in high_corr:
                if a == symbol or b == symbol:
                    reasons.append(
                        f"High correlation ({corr_val:.2f}) between {a} and {b} "
                        f"exceeds limit {cfg.max_correlation:.0%}"
                    )

        # ── 4.  VaR budget check ──────────────────────────────────────
        returns_list: list[float] = portfolio_state.get("returns_list", [])
        if returns_list:
            var_val = RiskChecker.var_historical(returns_list, cfg.default_confidence)
            if var_val > cfg.max_var_1d:
                reasons.append(
                    f"1d VaR {var_val:.1%} exceeds budget {cfg.max_var_1d:.0%}"
                )

        # ── 5.  Side sanity (no short if not allowed, etc.) ────────────
        if side not in ("BUY", "SELL"):
            reasons.append(f"Invalid trade side: {side}")

        approved = len(reasons) == 0
        return approved, reasons
