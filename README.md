# Agentic Quant Sandbox

![Python](https://img.shields.io/badge/python-3.13-blue?logo=python&logoColor=white)
![Rust](https://img.shields.io/badge/rust-stable-orange?logo=rust&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.11x-009688?logo=fastapi&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)
![CI](https://img.shields.io/badge/CI-passing-brightgreen?logo=github-actions&logoColor=white)

Autonomous multi-agent AI system for quantitative trading research, backtest generation, and institutional-grade strategy validation.

---

## What It Does

- Fetches live market data and calculates RSI, MACD, EMA, and ATR for any ticker, then classifies the current market regime using a dedicated research agent.
- Generates vectorbt-compatible Python backtest code from the research agent's output using a code generation agent.
- Validates the generated strategy against structural failure modes — lookahead bias, overfitting, regime fragility, and inadequate risk management — using a critic agent.

---

## Architecture

```
                    ┌─────────────────────┐
                    │   Market Data        │
                    │  (yfinance / 1m bars)│
                    └────────┬────────────┘
                             │
                    ┌────────▼────────────┐
                    │   Research Agent     │
                    │  RSI / MACD / EMA   │
                    │  Regime + Hypothesis │
                    └────────┬────────────┘
                             │
                    ┌────────▼────────────┐
                    │   CodeGen Agent      │
                    │  vectorbt backtest  │
                    └────────┬────────────┘
                             │
                    ┌────────▼────────────┐
                    │   Critic Agent       │
                    │  Structural audit   │
                    └────────┬────────────┘
                             │
                    ┌────────▼────────────┐
                    │   Verdict + Issues   │
                    │  PASS / FAIL + fixes │
                    └─────────────────────┘

┌──────────────────────────────────────────┐
│         FastAPI Backend (:8000)          │
│   /analyze/{symbol}  /critique  /stream  │
└──────────────────┬───────────────────────┘
                   │ HTTP / SSE
┌──────────────────▼───────────────────────┐
│         Ratatui TUI  (aqs-tui)           │
│   Analysis · CodeGen · Critic · History  │
└──────────────────────────────────────────┘
```

---

## Agent Pipeline

| Agent | Role | Output Format |
|---|---|---|
| **ResearchAgent** | Fetches live indicators, classifies market regime, proposes trade hypothesis with entry, stop-loss, and invalidation conditions | JSON — `regime`, `regime_label`, `indicator_reading`, `trade_hypothesis`, `confidence` |
| **CodeGenAgent** | Translates the research output into executable vectorbt backtest code | JSON — `code` (Python string), `based_on` (research summary) |
| **CriticAgent** | Audits the generated strategy against a fixed rubric of 12 failure categories | JSON — `verdict` (PASS/FAIL), `issues[]` with severity, `suggestions[]` |

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.13, FastAPI, uvicorn |
| **Agents** | LangChain, Groq (LLaMA 3), async LLM inference |
| **Market Data** | yfinance (1m candles, auto-fallback from 1d → 5d) |
| **Indicators** | pandas-ta — RSI (14), MACD (12/26/9), EMA (20/50), ATR (14) |
| **API** | REST + Server-Sent Events (SSE) streaming pipeline |
| **Python TUI** | Textual (legacy, `tui.py`) |
| **Rust TUI** | Ratatui + crossterm + tokio + reqwest (`rust/aqs-tui`) |
| **Rust Core** | quant-core — SMA, EMA, RSI, ATR in safe Rust (`rust/quant-core`) |
| **Testing** | pytest, pytest-asyncio, hypothesis (property tests), criterion (Rust benchmarks) |

---

## Getting Started

### Prerequisites

- Python 3.13
- Rust stable toolchain (`rustup install stable`)
- A Groq API key — [console.groq.com](https://console.groq.com)

### Clone and Setup

```bash
git clone https://github.com/amrav69/agentic-quant-sandbox.git
cd agentic-quant-sandbox

# Create virtual environment and install dependencies
python -m venv venv
.\venv\Scripts\activate        # Windows
# source venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
pip install -r requirements-dev.txt   # for testing
```

### Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

```env
GROQ_API_KEY=your_groq_api_key_here
```

All available configuration options are documented in [`.env.example`](.env.example).

### Run Backend

```bash
.\venv\Scripts\uvicorn.exe backend.main:app --reload   # Windows
# uvicorn backend.main:app --reload                    # macOS/Linux
```

The API will be available at `http://127.0.0.1:8000`.

Key endpoints:

```
GET  /health
GET  /analyze/{symbol}        # full autonomous analysis
POST /critique                # research → codegen → critic pipeline
POST /analyze/stream          # SSE streaming pipeline
```

### Run TUI

**Rust TUI** (primary):

```bash
cd rust/aqs-tui
cargo build --release
.\target\release\aqs-tui.exe   # Windows
# ./target/release/aqs-tui     # macOS/Linux
```

**Python TUI** (legacy):

```bash
.\venv\Scripts\python.exe tui.py   # Windows
# python tui.py                    # macOS/Linux
```

The TUI connects to the backend at `http://127.0.0.1:8000`. Start the backend before the TUI.

---

## Project Structure

```
agentic-quant-sandbox/
├── backend/
│   ├── main.py                 # FastAPI app, route definitions
│   ├── llm_client.py           # Groq client initialization
│   ├── cache.py                # TTL cache decorator
│   ├── logging_config.py       # Structured logging setup
│   ├── agents/
│   │   ├── research_agent.py   # Market regime analysis + indicator auto-fetch
│   │   ├── codegen_agent.py    # vectorbt backtest generation
│   │   └── critic_agent.py     # Strategy structural audit
│   ├── data/
│   │   └── fetcher.py          # yfinance data fetch with TTL caching
│   ├── quant/
│   │   ├── indicators.py       # RSI, MACD, EMA, ATR via pandas-ta
│   │   └── market_context.py   # Multi-timeframe context
│   └── risk/                   # Position sizing, VaR, Kelly criterion
├── rust/
│   ├── Cargo.toml              # Workspace definition
│   ├── aqs-tui/
│   │   └── src/main.rs         # Ratatui terminal UI (~1800 lines)
│   ├── quant-core/
│   │   └── src/                # Rust indicator implementations
│   └── feed-ingestor/          # Real-time feed ingestion (WIP)
├── tests/
│   ├── conftest.py
│   ├── test_agents.py
│   ├── test_api.py
│   ├── test_api_edge_cases.py
│   ├── test_indicators_unit.py
│   ├── test_market_context.py
│   ├── test_risk_engine.py
│   ├── test_property.py        # hypothesis property-based tests
│   └── benchmarks/
├── tui.py                      # Textual-based Python TUI (legacy)
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
└── Makefile
```

---

## Running Tests

### Python

```bash
# Run full test suite
.\venv\Scripts\pytest.exe tests/ -v

# With coverage report
.\venv\Scripts\pytest.exe tests/ --cov=backend --cov-report=term-missing

# Property-based tests only
.\venv\Scripts\pytest.exe tests/test_property.py -v
```

### Rust

```bash
# Unit and integration tests for all crates
cd rust
cargo test --workspace

# Criterion benchmarks (quant-core)
cd rust/quant-core
cargo bench
```

---

## Contributing

Open a pull request against `main`. Ensure `pytest` and `cargo test --workspace` both pass before submitting. ⚙️

---

## License

MIT — see [`LICENSE`](LICENSE).
