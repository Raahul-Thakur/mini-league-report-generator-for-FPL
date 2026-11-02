"""FPL client tests, using httpx.MockTransport (no network)."""
import asyncio

import httpx
import pytest

from app.config import Settings
from app.fpl_client import FPLClient, FPLError, FPLNotFound


def make_client(handler, **settings):
    return FPLClient(
        Settings(**settings), transport=httpx.MockTransport(handler), backoff_base=0
    )


async def test_caches_responses():
    calls = []

    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(200, json={"ok": True})

    client = make_client(handler)
    assert await client.event_live(5) == {"ok": True}
    assert await client.event_live(5) == {"ok": True}
    assert calls == ["/api/event/5/live/"]
    await client.aclose()


async def test_coalesces_concurrent_identical_requests():
    calls = 0

    async def handler(request):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.01)
        return httpx.Response(200, json={"n": 1})

    client = make_client(handler)
    results = await asyncio.gather(*(client.event_live(1) for _ in range(10)))
    assert all(r == {"n": 1} for r in results)
    assert calls == 1
    await client.aclose()


async def test_retries_on_5xx_then_succeeds():
    responses = iter([503, 429, 200])

    def handler(request):
        code = next(responses)
        return httpx.Response(code, json={"code": code})

    client = make_client(handler, fpl_max_retries=3)
    assert await client.bootstrap() == {"code": 200}
    await client.aclose()


async def test_gives_up_after_max_retries():
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(503)

    client = make_client(handler, fpl_max_retries=2)
    with pytest.raises(FPLError):
        await client.bootstrap()
    assert calls == 3
    await client.aclose()


async def test_404_raises_not_found_without_retry():
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(404)

    client = make_client(handler)
    with pytest.raises(FPLNotFound):
        await client.league_standings(999)
    assert calls == 1
    await client.aclose()


async def test_non_json_maintenance_page_is_an_error():
    client = make_client(lambda r: httpx.Response(200, text="<html>The game is being updated</html>"))
    with pytest.raises(FPLError):
        await client.bootstrap()
    await client.aclose()


async def test_concurrency_cap_is_respected():
    active = peak = 0

    async def handler(request):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.01)
        active -= 1
        return httpx.Response(200, json={})

    client = make_client(handler, fpl_concurrency=3)
    await asyncio.gather(*(client.entry_picks(i, 1) for i in range(20)))
    assert peak == 3
    await client.aclose()


async def test_standings_page_param_is_part_of_cache_key():
    seen = []

    def handler(request):
        seen.append(request.url.params["page_standings"])
        return httpx.Response(200, json={"page": request.url.params["page_standings"]})

    client = make_client(handler)
    assert (await client.league_standings(1, page=1))["page"] == "1"
    assert (await client.league_standings(1, page=2))["page"] == "2"
    assert seen == ["1", "2"]
    await client.aclose()
