"""HTTP API."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Path, Query, Request, Response
from fastapi.responses import JSONResponse

from app.config import Settings
from app.fpl_client import FPLClient, FPLError
from app.service import (
    GameweekNotStarted,
    InvalidGameweek,
    LeagueNotFound,
    generate_report,
)

DISCLAIMER = "Not affiliated with the Premier League or Fantasy Premier League."


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tests may pre-set app.state.fpl to a fake; only create a real client otherwise.
    owns_client = getattr(app.state, "fpl", None) is None
    if owns_client:
        app.state.fpl = FPLClient(app.state.settings)
    try:
        yield
    finally:
        if owns_client:
            await app.state.fpl.aclose()


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="Mini-League Report API", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings or Settings.from_env()
    app.state.fpl = None

    def error(status: int, code: str, message: str, headers: dict | None = None) -> JSONResponse:
        return JSONResponse({"error": code, "message": message}, status_code=status, headers=headers)

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

    @app.get("/api/health")
    async def health():
        return {"ok": True}

    @app.get("/api/leagues/{league_id}/report")
    async def league_report(
        request: Request,
        response: Response,
        league_id: int = Path(gt=0, le=2**31),
        gw: int | None = Query(default=None, ge=1, le=38),
    ):
        s: Settings = request.app.state.settings
        report = await generate_report(request.app.state.fpl, league_id, gw, s.max_entries)
        response.headers["Cache-Control"] = f"public, max-age={s.ttl_default}"
        return {**report.to_dict(), "max_entries": s.max_entries, "disclaimer": DISCLAIMER}

    return app


app = create_app()
