"""Cache interface used by the FPL client and the card endpoint.

Callers only see the async `Cache` protocol, so a shared backend (e.g. Redis) can be
added later by writing one class and extending `make_cache`, without touching callers.

Values must be JSON-like data or bytes, or tuples of those, so they'd serialise
cleanly to an external store.
"""
from __future__ import annotations

import time
from collections import OrderedDict
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Cache(Protocol):
    async def get(self, key: str) -> Any | None:
        """The cached value, or None if missing or expired."""

    async def set(self, key: str, value: Any, ttl: float) -> None:
        """Store value for ttl seconds."""

    async def clear(self) -> None:
        """Remove everything (used by tests and admin tooling)."""


class MemoryCache:
    """In-process TTL cache with a size cap (least recently used entries go first).

    Per process: with several workers or instances each has its own copy. Fine for one
    small instance; switch to a shared backend before scaling out.
    """

    def __init__(self, max_items: int = 5000) -> None:
        self.max_items = max_items
        self._data: OrderedDict[str, tuple[float, Any]] = OrderedDict()

    async def get(self, key: str) -> Any | None:
        item = self._data.get(key)
        if item is None:
            return None
        expires, value = item
        if time.monotonic() >= expires:
            self._data.pop(key, None)
            return None
        self._data.move_to_end(key)
        return value

    async def set(self, key: str, value: Any, ttl: float) -> None:
        self._data[key] = (time.monotonic() + ttl, value)
        self._data.move_to_end(key)
        while len(self._data) > self.max_items:
            self._data.popitem(last=False)

    async def clear(self) -> None:
        self._data.clear()

    def __len__(self) -> int:
        return len(self._data)


def make_cache(backend: str, *, max_items: int) -> Cache:
    """Build a cache from config. Only "memory" exists today.

    To add Redis: implement the Cache protocol (e.g. with redis.asyncio, pickling or
    JSON-encoding values), add a branch here, and set CACHE_BACKEND=redis + REDIS_URL.
    """
    if backend == "memory":
        return MemoryCache(max_items=max_items)
    raise ValueError(f"Unknown CACHE_BACKEND {backend!r} (supported: memory)")
