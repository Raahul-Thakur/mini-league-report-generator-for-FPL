"""Cache interface tests."""
import pytest

from app.cache import Cache, MemoryCache, make_cache


async def test_get_set_and_ttl_expiry():
    c = MemoryCache()
    await c.set("a", {"x": 1}, ttl=60)
    assert await c.get("a") == {"x": 1}
    await c.set("b", b"png", ttl=0)
    assert await c.get("b") is None
    assert await c.get("missing") is None


async def test_evicts_least_recently_used_when_full():
    c = MemoryCache(max_items=2)
    await c.set("a", 1, ttl=60)
    await c.set("b", 2, ttl=60)
    assert await c.get("a") == 1  # touch a, so b is now least recently used
    await c.set("c", 3, ttl=60)
    assert await c.get("b") is None
    assert await c.get("a") == 1 and await c.get("c") == 3
    assert len(c) == 2


async def test_clear():
    c = MemoryCache()
    await c.set("a", 1, ttl=60)
    await c.clear()
    assert await c.get("a") is None


def test_factory():
    assert isinstance(make_cache("memory", max_items=10), Cache)
    with pytest.raises(ValueError, match="Unknown CACHE_BACKEND"):
        make_cache("redis", max_items=10)
