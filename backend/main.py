"""FastAPI application for the Agentic Quant Sandbox.

Provides REST endpoints for market analysis, backtest code generation,
and a full 3-agent critique pipeline with streaming support.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, AsyncGenerator
from pydantic import BaseModel

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse

from backend.agents.research_agent import ResearchAgent
from backend.agents.codegen_agent import CodeGenAgent
from backend.agents.critic_agent import CriticAgent
from backend.data.fetcher import fetch_market_data
from backend.logging_config import setup_logging
from backend.quant.indicators import calculate_indicators

load_dotenv()
setup_logging()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class AnalyzeRequest(BaseModel):
    symbol: str
    price: float | None = None
    rsi: float | None = None
    macd_line: float | None = None
    macd_signal: float | None = None
    ema20: float | None = None
    ema50: float | None = None
    atr: float | None = None
    volume_trend: str | None = None


class GenerateRequest(BaseModel):
    symbol: str | None = None
    price: float | None = None


class CritiqueRequest(BaseModel):
    symbol: str | None = None
    price: float | None = None


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Agentic Quant Sandbox",
    description=(
        "AI-powered autonomous trading strategy engine -- "
        "multi-agent system with Research, CodeGen, and Critic agents "
        "that analyze markets, write backtests, and validate strategies."
    ),
    version="0.1.0",
)

# Lazy agent singletons -- initialised on first request so that
# tests can patch dependencies (e.g. get_groq_client) beforehand.
_agents: dict[str, ResearchAgent | CodeGenAgent | CriticAgent] = {}


def _get_agents() -> dict[str, ResearchAgent | CodeGenAgent | CriticAgent]:
    if not _agents:
        _agents["research"] = ResearchAgent()
        _agents["codegen"] = CodeGenAgent()
        _agents["critic"] = CriticAgent()
    return _agents


# ---------------------------------------------------------------------------
# Middleware: log every request + duration header
# ---------------------------------------------------------------------------


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    response.headers["X-Request-Duration-Ms"] = str(elapsed_ms)
    logger.info(
        "%s %s -> %s (%d ms)",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


# ---------------------------------------------------------------------------
# Health / status
# ---------------------------------------------------------------------------


@app.get("/")
async def root():
    return {"status": "running", "message": "Agentic Quant Sandbox is live"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


# ---------------------------------------------------------------------------
# Cache management
# ---------------------------------------------------------------------------


@app.post("/cache/clear")
async def clear_cache():
    """Flush the TTL cache for market data fetches."""
    if hasattr(fetch_market_data, "cache_clear"):
        fetch_market_data.cache_clear()
    return {"status": "cache cleared"}


# ---------------------------------------------------------------------------
# /analyze endpoints
# ---------------------------------------------------------------------------


@app.post("/analyze")
async def analyze_market(data: AnalyzeRequest):
    start = time.perf_counter()
    agents = _get_agents()
    result = await agents["research"].analyze(data.model_dump())
    elapsed = int((time.perf_counter() - start) * 1000)
    logger.info("POST /analyze completed in %d ms", elapsed)
    return result


@app.get("/analyze/{symbol}")
async def analyze_market_autonomous(symbol: str):
    """Fully autonomous analysis: fetch data -> indicators -> AI analysis."""
    symbol_upper = symbol.upper()
    start = time.perf_counter()

    try:
        live_data = fetch_market_data(symbol_upper)
    except ValueError:
        raise HTTPException(status_code=404, detail="Symbol not found")
    except Exception:
        logger.exception("Failed to fetch market data for %s", symbol_upper)
        raise HTTPException(status_code=400, detail="Failed to fetch market data")

    try:
        indicators = calculate_indicators(symbol_upper)
    except ValueError:
        raise HTTPException(status_code=404, detail="Symbol not found")
    except Exception:
        logger.exception("Failed to calculate indicators for %s", symbol_upper)
        raise HTTPException(status_code=400, detail="Failed to calculate indicators")

    ema20 = indicators.get("EMA20")
    ema50 = indicators.get("EMA50")
    trend_status = "Unknown"
    if ema20 is not None and ema50 is not None:
        trend_status = (
            "Bullish (EMA20 > EMA50)"
            if ema20 > ema50
            else "Bearish (EMA20 < EMA50)"
        )

    volume_val = live_data.get("volume", 0)

    market_data_payload = {
        "symbol": symbol_upper,
        "price": indicators.get("current_price"),
        "rsi": indicators.get("RSI"),
        "macd": (
            f"Line: {indicators.get('MACD'):.4f}, "
            f"Signal: {indicators.get('MACD_signal'):.4f}"
        ),
        "volume_trend": (
            f"Volume: {volume_val:,} | Trend: {trend_status} | "
            f"EMA20: {ema20:.2f} | EMA50: {ema50:.2f} | "
            f"ATR: {indicators.get('ATR'):.4f}"
        ),
    }

    agents = _get_agents()
    ai_response = await agents["research"].analyze(market_data_payload)
    elapsed = int((time.perf_counter() - start) * 1000)
    logger.info("GET /analyze/%s completed in %d ms", symbol_upper, elapsed)

    return {
        "symbol": symbol_upper,
        "live_indicators": indicators,
        "ai_analysis": ai_response.get("analysis", ""),
    }


# ---------------------------------------------------------------------------
# /generate -- backtest code generation
# ---------------------------------------------------------------------------


@app.post("/generate")
async def generate_backtest(data: GenerateRequest):
    """Research -> CodeGen pipeline (sequential)."""
    start = time.perf_counter()
    agents = _get_agents()
    try:
        research_result = await agents["research"].analyze(data.model_dump())
        generated_code_result = await agents["codegen"].generate(research_result)
        elapsed = int((time.perf_counter() - start) * 1000)
        logger.info("POST /generate completed in %d ms", elapsed)
        return {
            "research_analysis": research_result,
            "generated_code": generated_code_result,
        }
    except Exception:
        logger.exception("Failed to generate backtest")
        raise HTTPException(status_code=500, detail="Pipeline execution failed")


# ---------------------------------------------------------------------------
# /critique -- full 3-agent pipeline (Research -> CodeGen -> Critic)
# ---------------------------------------------------------------------------


@app.post("/critique")
async def critique_strategy(data: CritiqueRequest):
    """Full 3-agent pipeline: research then codegen then critic."""
    start = time.perf_counter()
    agents = _get_agents()
    try:
        research_result = await agents["research"].analyze(data.model_dump())
        generated_code = await agents["codegen"].generate(research_result)
        critique_result = await agents["critic"].critique({
            "research_analysis": research_result,
            "generated_code": generated_code,
        })

        elapsed = int((time.perf_counter() - start) * 1000)
        logger.info("POST /critique completed in %d ms", elapsed)

        return {
            "research_analysis": research_result,
            "generated_code": generated_code,
            "critique": critique_result,
        }
    except Exception:
        logger.exception("Critique pipeline failed")
        raise HTTPException(status_code=500, detail="Pipeline execution failed")


# ---------------------------------------------------------------------------
# /analyze/stream -- streaming pipeline
# ---------------------------------------------------------------------------


def _sse_event(stage: str, status: str, **kwargs: Any) -> str:
    payload: dict[str, Any] = {"stage": stage, "status": status}
    payload.update(kwargs)
    return f"data: {json.dumps(payload)}\n\n"


@app.post("/analyze/stream")
async def analyze_stream(data: CritiqueRequest):
    """Stream the 3-agent pipeline as newline-delimited JSON events."""

    async def event_generator() -> AsyncGenerator[str, None]:
        agents = _get_agents()
        try:
            yield _sse_event("research", "running")
            research_result = await agents["research"].analyze(data.model_dump())
            yield _sse_event("research", "done", result=research_result)

            yield _sse_event("codegen", "running")
            generated_code = await agents["codegen"].generate(research_result)
            yield _sse_event("codegen", "done", result=generated_code)

            yield _sse_event("critic", "running")
            critique_result = await agents["critic"].critique({
                "research_analysis": research_result,
                "generated_code": generated_code,
            })
            yield _sse_event("critic", "done", result=critique_result)

        except Exception:
            logger.exception("Streaming pipeline failed")
            yield _sse_event("error", "failed", message="Pipeline execution failed")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
