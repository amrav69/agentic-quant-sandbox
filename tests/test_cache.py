"""Tests for the TTL caching layer."""

from __future__ import annotations

import time

from backend.cache import ttl_cache


class TestTtlCache:
    def test_cache_hits_and_misses(self):
        call_count = 0

        @ttl_cache(maxsize=16, ttl=60)
        def fetch(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        assert fetch(1) == 2
        assert call_count == 1
        assert fetch(1) == 2
        assert call_count == 1
        assert fetch(2) == 4
        assert call_count == 2
        assert fetch(1) == 2
        assert call_count == 2

    def test_cache_expiry(self):
        call_count = 0

        @ttl_cache(maxsize=16, ttl=1)
        def fetch(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        fetch(1)
        assert call_count == 1
        fetch(1)
        assert call_count == 1
        time.sleep(1.1)
        fetch(1)
        assert call_count == 2

    def test_cache_maxsize_eviction(self):
        call_count = 0

        @ttl_cache(maxsize=2, ttl=60)
        def fetch(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        fetch(1)
        fetch(2)
        fetch(3)
        # 3rd call should evict oldest (1)
        assert call_count == 3
        fetch(1)
        assert call_count == 4

    def test_cache_clear(self):
        call_count = 0

        @ttl_cache(maxsize=16, ttl=60)
        def fetch(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        fetch(1)
        assert call_count == 1
        fetch.cache_clear()
        fetch(1)
        assert call_count == 2

    def test_cache_different_args(self):
        call_count = 0

        @ttl_cache(maxsize=16, ttl=60)
        def fetch(a: int, b: str) -> str:
            nonlocal call_count
            call_count += 1
            return f"{a}:{b}"

        assert fetch(1, "a") == "1:a"
        assert call_count == 1
        assert fetch(1, "a") == "1:a"
        assert call_count == 1
        assert fetch(1, "b") == "1:b"
        assert call_count == 2

    def test_cache_kwargs(self):
        call_count = 0

        @ttl_cache(maxsize=16, ttl=60)
        def fetch(a: int, b: int = 0) -> int:
            nonlocal call_count
            call_count += 1
            return a + b

        assert fetch(1, b=2) == 3
        assert call_count == 1
        assert fetch(1, b=2) == 3
        assert call_count == 1
    