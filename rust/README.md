# quant-core

Fast, panic-free Rust technical indicator library powering the Agentic Quant Sandbox.

## Crates

- **quant-core** — Pure Rust technical indicators (SMA, EMA, RSI, MACD, Bollinger Bands)
  via the `ta` crate. Exposes a C FFI interface and an optional Python binding.
- **feed-ingestor** — Async WebSocket market data consumer that streams
  real-time ticks to stdout as JSON Lines for the Python layer.

## Running

```bash
# Build everything
cargo build --workspace

# Run all tests
cargo test --workspace

# Run clippy
cargo clippy --workspace -- -D warnings
```

## quant-core

### Available indicators

| Function | Description |
|----------|-------------|
| `sma(data, period)` | Simple Moving Average |
| `ema(data, period)` | Exponential Moving Average |
| `rsi(data, period)` | Relative Strength Index (14 default) |
| `macd(data, fast, slow, signal)` | MACD line + signal + histogram |
| `bollinger_bands(data, period, std_dev)` | Upper / middle / lower bands |
| `atr(high, low, close, period)` | Average True Range, Wilder's smoothing (pandas-ta parity) |
| `highest(data, period)` | Rolling maximum |
| `lowest(data, period)` | Rolling minimum |

All functions return `Result<Vec<f64>, QuantError>` and are panic-free.

### FFI

```c
int calc_rsi(const double* prices, size_t len, size_t period,
             double* out, size_t* out_len);
```

Returns 0 on success, negative on error.

### Python (optional)

```bash
cargo build --features python
```

## feed-ingestor

```bash
WS_URL=wss://your-provider.com SYMBOLS=AAPL,TSLA,BTC-USD cargo run --bin feed-ingestor
```

Flags: `--dry-run`, `--provider polygon|alpaca`
