# =============================================================================
# Stage 1: Build Rust crates
# =============================================================================
FROM rust:1.75-slim AS rust-builder

WORKDIR /build
COPY rust/ ./rust/
COPY Cargo.toml ./

RUN apt-get update && apt-get install -y pkg-config libssl-dev && rm -rf /var/lib/apt/lists/*
RUN cargo build --workspace --release && \
    cp rust/target/release/feed-ingestor /usr/local/bin/feed-ingestor

# =============================================================================
# Stage 2: Python dependencies
# =============================================================================
FROM python:3.11-slim AS python-base

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# =============================================================================
# Stage 3: Final image
# =============================================================================
FROM python:3.11-slim

WORKDIR /app

# Copy Python source (not tests -- they're dev-only)
COPY backend/ ./backend/

# Copy compiled Rust binary
COPY --from=rust-builder /usr/local/bin/feed-ingestor /usr/local/bin/feed-ingestor

# Copy Python dependencies
COPY --from=python-base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
