"""TTL-aware caching decorator using cachetools."""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable

from cachetools import TTLCache

logger = logging.getLogger(__name__)


def ttl_cache(maxsize: int = 128, ttl: int = 300) -> Callable:
    """Decorator that caches function results with a TTL.

    Wraps ``cachetools.TTLCache`` so the decorated function's return value
    is cached for *ttl* seconds (default 300 = 5 min).

    Usage::

        @ttl_cache(maxsize=64, ttl=60)
        def fetch_data(symbol: str) -> dict:
            ...
    """

    def decorator(func: Callable) -> Callable:
        cache: TTLCache = TTLCache(maxsize=maxsize, ttl=ttl)

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = (args, tuple(sorted(kwargs.items())))
            if key in cache:
                logger.debug("Cache hit for %s%s", func.__name__, args)
                return cache[key]
            result = func(*args, **kwargs)
            cache[key] = result
            return result

        wrapper.cache = cache  # type: ignore[attr-defined]
        wrapper.cache_clear = cache.clear  # type: ignore[attr-defined]
        return wrapper

    return decorator
