from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
import os
from backend.agents.research_agent import ResearchAgent
from backend.agents.codegen_agent import CodeGenAgent
from backend.agents.critic_agent import CriticAgent
from backend.quant.indicators import calculate_indicators
from backend.data.fetcher import fetch_market_data

load_dotenv()

app = FastAPI(
    title="Agentic Quant Sandbox",
    description="AI-powered autonomous trading strategy engine",
    version="0.1.0"
)

research_agent = ResearchAgent()
codegen_agent = CodeGenAgent()
critic_agent = CriticAgent()

@app.get("/")
async def root():
    return {"status": "running", "message": "Agentic Quant Sandbox is live"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/analyze")
async def analyze_market(data: dict):
    result = await research_agent.analyze(data)
    return result

@app.get("/analyze/{symbol}")
async def analyze_market_autonomous(symbol: str):
    """
    Fully autonomous endpoint that:
    1. Fetches live market data (OHLCV) for the symbol
    2. Calculates technical indicators (RSI, MACD, EMA, ATR)
    3. Runs AI research analysis on indicators to produce trading hypotheses
    """
    symbol_upper = symbol.upper()
    try:
        # Step 1: Fetch live market data
        try:
            live_data = fetch_market_data(symbol_upper)
        except ValueError as ve:
            raise HTTPException(status_code=404, detail=str(ve))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to fetch market data: {str(e)}")

        # Step 2: Calculate technical indicators
        try:
            indicators = calculate_indicators(symbol_upper)
        except ValueError as ve:
            raise HTTPException(status_code=404, detail=str(ve))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to calculate indicators: {str(e)}")

        # Step 3: Map data and calculate volume trend / price comparison for AI prompt
        ema20 = indicators.get("EMA20")
        ema50 = indicators.get("EMA50")
        trend_status = "Unknown"
        if ema20 is not None and ema50 is not None:
            trend_status = "Bullish (EMA20 > EMA50)" if ema20 > ema50 else "Bearish (EMA20 < EMA50)"

        volume_val = live_data.get("volume", 0)

        # Structure research agent inputs matching ResearchAgent expectations
        market_data_payload = {
            "symbol": symbol_upper,
            "price": indicators.get("current_price"),
            "rsi": indicators.get("RSI"),
            "macd": f"Line: {indicators.get('MACD'):.4f}, Signal: {indicators.get('MACD_signal'):.4f}",
            "volume_trend": f"Volume: {volume_val:,} | Trend: {trend_status} | EMA20: {ema20:.2f} | EMA50: {ema50:.2f} | ATR: {indicators.get('ATR'):.4f}"
        }

        # Step 4: Run AI analysis
        ai_response = await research_agent.analyze(market_data_payload)

        # Step 5: Construct and return response
        return {
            "symbol": symbol_upper,
            "live_indicators": indicators,
            "ai_analysis": ai_response.get("analysis", "")
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred during autonomous analysis: {str(e)}"
        )

@app.post("/generate")
async def generate_backtest(data: dict):
    """
    Accepts raw market data, generates a research hypothesis,
    and then automatically creates a runnable vectorbt backtest in Python.
    """
    try:
        # 1. Run qualitative research analysis
        research_result = await research_agent.analyze(data)
        
        # 2. Feed the research output into the Code Generation Agent
        generated_code_result = await codegen_agent.generate(research_result)
        
        # 3. Return combined response
        return {
            "research_analysis": research_result,
            "generated_code": generated_code_result
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate backtest: {str(e)}"
        )

@app.post("/critique")
async def critique_strategy(data: dict):
    """
    Runs the complete three-agent quantitative sandbox pipeline:
    1. ResearchAgent: Evaluates market conditions and forms a strategy hypothesis.
    2. CodeGenAgent: Converts the strategy hypothesis into runnable vectorbt code.
    3. CriticAgent: Reviews both the logic and the code for risk-management flaws, lookahead bias, and overfitting.
    """
    try:
        # Step 1: Formulate research strategy hypothesis
        research_result = await research_agent.analyze(data)

        # Step 2: Write runnable backtest code
        generated_code = await codegen_agent.generate(research_result)

        # Step 3: Audit both findings for risk, leakage, and parameters
        critique_result = await critic_agent.critique({
            "research_analysis": research_result,
            "generated_code": generated_code
        })

        # Step 4: Return full combined pipeline payload
        return {
            "research_analysis": research_result,
            "generated_code": generated_code,
            "critique": critique_result
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline execution failed: {str(e)}"
        )