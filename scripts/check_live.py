"""One-off check that live FPL responses have the fields the code relies on.

Run by hand only (never from tests or on a schedule):

    python -m scripts.check_live <league_id> [gw]

Makes ~4 + min(league size, MAX_ENTRIES) requests, through the normal client
(cache + concurrency cap), then builds a real report.
"""
from __future__ import annotations

import asyncio
import json
import sys

from app.config import Settings
from app.fpl_client import FPLClient
from app.service import generate_report, latest_started_gameweek

EXPECTED = {
    "bootstrap.events[]": {"id", "is_current", "finished"},
    "bootstrap.elements[]": {"id", "web_name"},
    "standings": {"league", "standings"},
    "standings.league": {"id", "name"},
    "standings.standings": {"has_next", "results"},
    "standings.results[]": {"entry", "entry_name", "player_name", "rank", "last_rank"},
    "live.elements[]": {"id", "stats"},
    "live.elements[].stats": {"total_points", "minutes"},
    "picks": {"active_chip", "automatic_subs", "entry_history", "picks"},
    "picks.entry_history": {"points", "event_transfers", "event_transfers_cost", "points_on_bench"},
    "picks.picks[]": {"element", "position", "multiplier", "is_captain", "is_vice_captain"},
}


def check(label: str, obj: dict, problems: list[str]) -> None:
    missing = EXPECTED[label] - set(obj)
    status = "OK " if not missing else "BAD"
    print(f"  [{status}] {label}" + (f"  missing: {sorted(missing)}" if missing else ""))
    if missing:
        problems.append(f"{label} missing {sorted(missing)}")


async def main(league_id: int, gw: int | None) -> int:
    client = FPLClient(Settings.from_env())
    problems: list[str] = []
    try:
        boot = await client.bootstrap()
        check("bootstrap.events[]", boot["events"][0], problems)
        check("bootstrap.elements[]", boot["elements"][0], problems)
        latest = latest_started_gameweek(boot["events"])
        gw = gw or latest
        print(f"  latest started GW: {latest}; checking GW {gw}")

        st = await client.league_standings(league_id)
        check("standings", st, problems)
        check("standings.league", st["league"], problems)
        check("standings.standings", st["standings"], problems)
        rows = st["standings"]["results"]
        if rows:
            check("standings.results[]", rows[0], problems)
            print(f"  sample row: {json.dumps(rows[0], ensure_ascii=False)}")
        else:
            print("  (no standings rows yet)")

        live = await client.event_live(gw)
        el = live["elements"][0]
        check("live.elements[]", el, problems)
        check("live.elements[].stats", el["stats"], problems)

        if rows:
            picks = await client.entry_picks(rows[0]["entry"], gw)
            check("picks", picks, problems)
            check("picks.entry_history", picks["entry_history"], problems)
            check("picks.picks[]", picks["picks"][0], problems)
            cap = next(p for p in picks["picks"] if p["is_captain"])
            print(f"  captain pick as served: {cap}  active_chip={picks['active_chip']!r}")

        report = await generate_report(client, league_id, gw, client.settings.max_entries)
        print("\nReport:")
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False)[:4000])
    finally:
        await client.aclose()

    print("\nShape problems:" if problems else "\nAll expected fields present.")
    for p in problems:
        print("  -", p)
    return 1 if problems else 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: python -m scripts.check_live <league_id> [gw]")
    sys.exit(asyncio.run(main(int(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2 else None)))
