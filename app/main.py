"""HTTP API."""
from __future__ import annotations

import ipaddress
import secrets
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, Path, Query, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

from app.branding import Brand
from app.cache import Cache, make_cache
from app.card import render_card
from app.config import Settings
from app.fpl_client import FPLClient, FPLError
from app.service import (
    GameweekNotStarted,
    InvalidGameweek,
    LeagueNotFound,
    generate_report,
)

DISCLAIMER = "Not affiliated with the Premier League or Fantasy Premier League."
PROTECTED_PREFIX = "/api/leagues/"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tests may pre-set app.state.fpl to a fake; only create a real client otherwise.
    owns_client = getattr(app.state, "fpl", None) is None
    if owns_client:
        s: Settings = app.state.settings
        app.state.fpl = FPLClient(
            s, cache=make_cache(s.cache_backend, max_items=s.fpl_cache_max_items)
        )
    try:
        yield
    finally:
        if owns_client:
            await app.state.fpl.aclose()


def _has_internal_key(request: Request, settings: Settings) -> bool:
    given = request.headers.get("x-internal-key", "")
    return bool(settings.internal_api_key) and secrets.compare_digest(
        given.encode(), settings.internal_api_key.encode()
    )


def client_ip(request: Request) -> str:
    """Who to rate-limit.

    The website calls this API server-side, so the TCP peer is the website's server.
    It passes the visitor's IP in X-Client-IP, which is trusted only alongside a valid
    X-Internal-Key; anything else is keyed on the direct peer address.
    """
    settings: Settings = request.app.state.settings
    if _has_internal_key(request, settings):
        forwarded = request.headers.get("x-client-ip", "").strip()
        try:
            return str(ipaddress.ip_address(forwarded))
        except ValueError:
            pass
    return request.client.host if request.client else "unknown"


def create_app(settings: Settings | None = None) -> FastAPI:
    s = settings or Settings.from_env()
    app = FastAPI(title="Mini-League Report API", version="0.1.0", lifespan=lifespan)
    app.state.settings = s
    app.state.brand = Brand.from_env()
    app.state.fpl = None
    app.state.card_cache = make_cache(s.cache_backend, max_items=s.card_cache_max_items)
    limiter = Limiter(key_func=client_ip, storage_uri=s.rate_limit_storage_uri)
    app.state.limiter = limiter

    def error(status: int, code: str, message: str, headers: dict | None = None) -> JSONResponse:
        return JSONResponse({"error": code, "message": message}, status_code=status, headers=headers)

    if s.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(s.cors_origins),
            allow_methods=["GET"],
            allow_headers=[],
            max_age=3600,
        )

    @app.middleware("http")
    async def require_internal_key(request: Request, call_next):
        # When a key is configured, only the website (which holds it) may call the API.
        if (
            s.internal_api_key
            and request.url.path.startswith(PROTECTED_PREFIX)
            and request.method != "OPTIONS"
            and not _has_internal_key(request, s)
        ):
            return error(403, "forbidden", "This API is only available through the website.")
        return await call_next(request)

    @app.exception_handler(RateLimitExceeded)
    async def _rate_limited(request: Request, exc: RateLimitExceeded):
        return error(
            429,
            "rate_limited",
            "Too many requests. Please wait a minute and try again.",
            headers={"Retry-After": "60"},
        )

    @app.exception_handler(LeagueNotFound)
    async def _not_found(request: Request, exc: LeagueNotFound):
        return error(404, "league_not_found", "We couldn't find a classic league with that ID.")

    @app.exception_handler(InvalidGameweek)
    async def _bad_gw(request: Request, exc: InvalidGameweek):
        return error(422, "invalid_gameweek", str(exc))

    @app.exception_handler(GameweekNotStarted)
    async def _not_started(request: Request, exc: GameweekNotStarted):
        return error(409, "gameweek_not_started", str(exc))

    @app.exception_handler(FPLError)
    async def _upstream(request: Request, exc: FPLError):
        return error(
            503,
            "fpl_unavailable",
            "The FPL API is unavailable or updating. Please try again in a few minutes.",
            headers={"Retry-After": "120"},
        )

    def limited(limit: str):
        """Apply a rate limit unless it's configured as empty."""
        return limiter.limit(limit) if limit else (lambda f: f)

    def cache_control(ttl: int) -> str:
        # s-maxage lets a CDN in front (e.g. Vercel) serve repeats without reaching us.
        return f"public, max-age={ttl}, s-maxage={ttl}"

    @app.get("/api/health")
    async def health():
        return {"ok": True}

    @app.get("/api/leagues/{league_id}/report")
    @limited(s.rate_limit_report)
    async def league_report(
        request: Request,
        response: Response,
        league_id: int = Path(gt=0, le=2**31),
        gw: int | None = Query(default=None, ge=1, le=38),
    ):
        report = await generate_report(request.app.state.fpl, league_id, gw, s.max_entries)
        response.headers["Cache-Control"] = cache_control(s.ttl_default)
        return {**report.to_dict(), "max_entries": s.max_entries, "disclaimer": DISCLAIMER}

    @app.get("/api/leagues/{league_id}/card.png", response_class=Response,
             responses={200: {"content": {"image/png": {}}}})
    @limited(s.rate_limit_card)
    async def league_card(
        request: Request,
        league_id: int = Path(gt=0, le=2**31),
        gw: int | None = Query(default=None, ge=1, le=38),
        format: Literal["story", "square"] = Query(default="story"),
        download: bool = Query(default=False),
    ):
        cache: Cache = request.app.state.card_cache
        key = f"card:{league_id}:{gw or 'latest'}:{format}"
        cached = await cache.get(key)
        if cached is None:
            report = await generate_report(request.app.state.fpl, league_id, gw, s.max_entries)
            png = await run_in_threadpool(render_card, report, format, request.app.state.brand)
            cached = (png, report.gameweek)
            await cache.set(key, cached, s.ttl_card)
        png, resolved_gw = cached
        filename = f"league-{league_id}-gw{resolved_gw}-{format}.png"
        disposition = "attachment" if download else "inline"
        return Response(
            png,
            media_type="image/png",
            headers={
                "Cache-Control": cache_control(s.ttl_card),
                "Content-Disposition": f'{disposition}; filename="{filename}"',
            },
        )

    return app


app = create_app()
