"""Fetch everything a report needs from FPL, then hand it to the pure engine.

The number of upstream calls per report is bounded: 1 bootstrap, ceil(MAX_ENTRIES/50)
standings pages, 1 live, and 1 picks call per analysed manager. All go through the
client's cache and concurrency cap. Nothing here loops or polls.
"""
from __future__ import annotations

import asyncio
from typing import Protocol

from app.fpl_client import FPLError, FPLNotFound
from app.models import Report
from app.report import build_report, players_from_bootstrap

TOTAL_GAMEWEEKS = 38


class ReportError(Exception):
    """Base class for errors the API turns into user-facing messages."""


class LeagueNotFound(ReportError):
    pass


class InvalidGameweek(ReportError):
    pass


class GameweekNotStarted(ReportError):
    pass


class FPLSource(Protocol):
    async def bootstrap(self) -> dict: ...
    async def league_standings(self, league_id: int, page: int = 1) -> dict: ...
    async def event_live(self, gw: int) -> dict: ...
    async def entry_picks(self, entry_id: int, gw: int) -> dict: ...


def latest_started_gameweek(events: list[dict]) -> int | None:
    """The current GW, or the last finished one if FPL has no current GW flagged."""
    current = next((e["id"] for e in events if e.get("is_current")), None)
    if current is not None:
        return current
    finished = [e["id"] for e in events if e.get("finished")]
    return max(finished) if finished else None


async def fetch_standings(
    client: FPLSource, league_id: int, max_entries: int
) -> tuple[dict, list[dict], bool]:
    """(league info, first max_entries standings rows, truncated)."""
    rows: list[dict] = []
    page = 1
    try:
        while True:
            data = await client.league_standings(league_id, page=page)
            st = data.get("standings") or {}
            rows.extend(st.get("results") or [])
            has_next = bool(st.get("has_next"))
            if not has_next or len(rows) >= max_entries:
                break
            page += 1
    except FPLNotFound as exc:
        raise LeagueNotFound(f"League {league_id} not found") from exc
    truncated = has_next or len(rows) > max_entries
    return data.get("league") or {}, rows[:max_entries], truncated


async def _picks_or_none(client: FPLSource, entry_id: int, gw: int) -> dict | None:
    try:
        return await client.entry_picks(entry_id, gw)
    except FPLNotFound:
        return None  # e.g. the manager joined FPL after this gameweek


async def generate_report(
    client: FPLSource, league_id: int, gw: int | None, max_entries: int
) -> Report:
    bootstrap = await client.bootstrap()
    latest = latest_started_gameweek(bootstrap.get("events") or [])
    if latest is None:
        raise GameweekNotStarted("The season hasn't started yet")
    if gw is None:
        gw = latest
    if not 1 <= gw <= TOTAL_GAMEWEEKS:
        raise InvalidGameweek(f"Gameweek must be between 1 and {TOTAL_GAMEWEEKS}")
    if gw > latest:
        raise GameweekNotStarted(f"Gameweek {gw} hasn't started yet (latest is {latest})")

    league, rows, truncated = await fetch_standings(client, league_id, max_entries)

    entry_ids = [int(r["entry"]) for r in rows]
    live, *picks = await asyncio.gather(
        client.event_live(gw), *(_picks_or_none(client, e, gw) for e in entry_ids)
    )
    picks_by_entry = {e: p for e, p in zip(entry_ids, picks) if p is not None}

    return build_report(
        league_id=league_id,
        league_name=str(league.get("name") or f"League {league_id}"),
        gameweek=gw,
        is_latest_gameweek=gw == latest,
        standings=rows,
        players=players_from_bootstrap(bootstrap),
        live=live,
        picks_by_entry=picks_by_entry,
        truncated=truncated,
        latest_gameweek=latest,
    )


__all__ = [
    "FPLError",
    "GameweekNotStarted",
    "InvalidGameweek",
    "LeagueNotFound",
    "ReportError",
    "generate_report",
]
