"""Async client for the public FPL API.

Politeness measures:
- TTL cache (app/cache.py interface), so repeat reports don't re-hit FPL
- identical in-flight requests are coalesced into one HTTP call
- a semaphore caps concurrent requests
- retries with exponential backoff on 429 / 5xx / network errors only
"""
from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.cache import Cache, MemoryCache
from app.config import Settings

USER_AGENT = "mini-league-report/0.1 (+unofficial fan tool)"


class FPLError(Exception):
    """FPL API unavailable or returned something unexpected."""


class FPLNotFound(FPLError):
    """FPL returned 404 (unknown league, entry or gameweek)."""


class FPLClient:
    def __init__(
        self,
        settings: Settings | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        backoff_base: float = 0.5,
        cache: Cache | None = None,
    ) -> None:
        self.settings = settings or Settings.from_env()
        self._http = httpx.AsyncClient(
            base_url=self.settings.fpl_base_url,
            timeout=self.settings.fpl_timeout_seconds,
            headers={"User-Agent": USER_AGENT},
            transport=transport,
            follow_redirects=True,
        )
        self._cache: Cache = cache or MemoryCache(self.settings.fpl_cache_max_items)
        self._sem = asyncio.Semaphore(self.settings.fpl_concurrency)
        self._inflight: dict[str, asyncio.Future] = {}
        self._backoff_base = backoff_base

    async def aclose(self) -> None:
        await self._http.aclose()

    # ---- endpoints ---------------------------------------------------------

    async def bootstrap(self) -> dict:
        return await self._get("/bootstrap-static/", ttl=self.settings.ttl_bootstrap)

    async def league_standings(self, league_id: int, page: int = 1) -> dict:
        return await self._get(
            f"/leagues-classic/{league_id}/standings/",
            params={"page_standings": page},
        )

    async def event_live(self, gw: int) -> dict:
        return await self._get(f"/event/{gw}/live/")

    async def entry_picks(self, entry_id: int, gw: int) -> dict:
        return await self._get(f"/entry/{entry_id}/event/{gw}/picks/")

    # ---- plumbing ------------------------------------------------------------

    async def _get(self, path: str, params: dict | None = None, ttl: float | None = None) -> Any:
        key = path + ("?" + "&".join(f"{k}={v}" for k, v in sorted(params.items())) if params else "")
        cached = await self._cache.get(key)
        if cached is not None:
            return cached

        existing = self._inflight.get(key)
        if existing is not None:
            return await asyncio.shield(existing)

        fut: asyncio.Future = asyncio.get_running_loop().create_future()
        self._inflight[key] = fut
        try:
            data = await self._fetch(path, params)
            await self._cache.set(key, data, ttl if ttl is not None else self.settings.ttl_default)
            fut.set_result(data)
            return data
        except BaseException as exc:
            fut.set_exception(exc)
            fut.exception()  # mark retrieved so asyncio doesn't warn when nobody else waits
            raise
        finally:
            self._inflight.pop(key, None)

    async def _fetch(self, path: str, params: dict | None) -> Any:
        attempts = self.settings.fpl_max_retries + 1
        last_exc: Exception | None = None
        for attempt in range(attempts):
            try:
                async with self._sem:
                    resp = await self._http.get(path, params=params)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_exc = exc
            else:
                if resp.status_code == 404:
                    raise FPLNotFound(path)
                if resp.status_code == 429 or resp.status_code >= 500:
                    last_exc = FPLError(f"FPL returned {resp.status_code} for {path}")
                elif resp.status_code >= 400:
                    raise FPLError(f"FPL returned {resp.status_code} for {path}")
                else:
                    try:
                        return resp.json()
                    except ValueError as exc:
                        # FPL serves an HTML page while "the game is being updated".
                        raise FPLError(f"FPL returned non-JSON for {path}") from exc
            if attempt < attempts - 1:
                await asyncio.sleep(self._backoff_base * (2**attempt))
        raise FPLError(f"FPL request failed after {attempts} attempts: {path}") from last_exc
