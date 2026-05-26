.PHONY: install dev test build lint fmt docker-up docker-down clean

install:
	pip install -r requirements.txt -r requirements-dev.txt
	cp -n .env.example .env 2>/dev/null || true
	@echo "--- Rust ---"
	cargo build --workspace

dev:
	@echo "Start the API server (http://localhost:8000)"
	uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

test:
	@echo "--- Python ---"
	pytest --tb=short -q
	@echo ""
	@echo "--- Rust ---"
	cargo test --workspace

build:
	cargo build --workspace --release

lint:
	@echo "--- Python (ruff) ---"
	ruff check .
	@echo ""
	@echo "--- Rust (clippy) ---"
	cargo clippy --workspace -- -D warnings

fmt:
	@echo "--- Python (ruff format) ---"
	ruff format .
	@echo ""
	@echo "--- Rust ---"
	cargo fmt --all

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

clean:
	rm -rf .venv __pycache__ **/__pycache__ .pytest_cache
	cargo clean
