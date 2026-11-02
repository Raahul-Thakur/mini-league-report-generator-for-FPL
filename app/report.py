"""Pure mini-league report engine.

No I/O: every function takes data already fetched from the FPL API (in the API's own
JSON shapes) and returns plain values. All fetching lives in app/service.py.

Inputs to build_report:
- standings: rows from leagues-classic/{id}/standings/ -> standings.results
- players: {element_id: display name} from bootstrap-static elements
- live: event/{gw}/live/ response
- picks_by_entry: {entry_id: entry/{id}/event/{gw}/picks/ response}
"""
from __future__ import annotations

from collections import Counter
from typing import Callable, Iterable, Mapping, TypeVar

from app.models import (
    BenchAward,
    CaptainAward,
    ChipPlay,
    DifferentialAward,
    HitAward,
    ManagerRef,
    Ownership,
    PointsAward,
    RankMoveAward,
    Report,
)

DIFFERENTIAL_MAX_SHARE = 0.20
TEMPLATE_SIZE = 10

CHIP_NAMES = {
    "wildcard": "Wildcard",
    "freehit": "Free Hit",
    "bboost": "Bench Boost",
    "3xc": "Triple Captain",
    "manager": "Assistant Manager",
}

T = TypeVar("T")


# ---- small helpers -----------------------------------------------------------

def players_from_bootstrap(bootstrap: Mapping) -> dict[int, str]:
    return {el["id"]: el.get("web_name") or f"#{el['id']}" for el in bootstrap.get("elements", [])}


def live_stats(live: Mapping) -> dict[int, tuple[int, int]]:
    """{element_id: (total_points, minutes)} from an event/{gw}/live/ response."""
    out: dict[int, tuple[int, int]] = {}
    for el in live.get("elements", []):
        stats = el.get("stats") or {}
        out[el["id"]] = (int(stats.get("total_points") or 0), int(stats.get("minutes") or 0))
    return out


def manager_ref(row: Mapping) -> ManagerRef:
    return ManagerRef(
        entry_id=int(row["entry"]),
        team_name=str(row.get("entry_name") or ""),
        manager_name=str(row.get("player_name") or ""),
    )


def effective_multipliers(picks: Mapping) -> dict[int, int]:
    """Multiplier per element after automatic substitutions.

    The picks endpoint lists the manager's original selection; automatic_subs says who
    actually came on. A subbed-off starter scores nothing, the sub scores x1.
    """
    mult = {p["element"]: int(p.get("multiplier", 0)) for p in picks.get("picks", [])}
    for sub in picks.get("automatic_subs", []) or []:
        out_id, in_id = sub.get("element_out"), sub.get("element_in")
        if out_id in mult and in_id in mult:
            mult[in_id] = max(mult[in_id], 1)
            mult[out_id] = 0
    return mult


def _best(items: Iterable[T], key: Callable[[T], tuple]) -> T | None:
    items = list(items)
    return max(items, key=key) if items else None


# ---- individual awards ---------------------------------------------------------

def net_points(picks: Mapping) -> int:
    eh = picks.get("entry_history") or {}
    return int(eh.get("points") or 0) - int(eh.get("event_transfers_cost") or 0)


def captain_result(
    picks: Mapping, stats: Mapping[int, tuple[int, int]]
) -> tuple[int | None, int, int, bool, bool]:
    """(element_id_that_scored, points, multiplier, used_vice, triple_captain).

    Captain's points x2 (x3 with Triple Captain). If the captain played 0 minutes the
    vice-captain takes the multiplier; if neither played, the armband scores 0.
    """
    triple = picks.get("active_chip") == "3xc"
    mult = 3 if triple else 2
    cap = next((p["element"] for p in picks.get("picks", []) if p.get("is_captain")), None)
    vice = next((p["element"] for p in picks.get("picks", []) if p.get("is_vice_captain")), None)

    def played(el: int | None) -> bool:
        return el is not None and stats.get(el, (0, 0))[1] > 0

    if played(cap):
        return cap, stats[cap][0] * mult, mult, False, triple
    if played(vice):
        return vice, stats[vice][0] * mult, mult, True, triple
    return cap, 0, mult, False, triple


# ---- the report ------------------------------------------------------------------

def build_report(
    *,
    league_id: int,
    league_name: str,
    gameweek: int,
    is_latest_gameweek: bool,
    standings: list[Mapping],
    players: Mapping[int, str],
    live: Mapping,
    picks_by_entry: Mapping[int, Mapping],
    truncated: bool = False,
) -> Report:
    stats = live_stats(live)
    # Managers without picks for this GW (e.g. joined FPL later) are skipped.
    rows = [r for r in standings if int(r["entry"]) in picks_by_entry]
    refs = {int(r["entry"]): manager_ref(r) for r in rows}
    league_rank = {int(r["entry"]): int(r.get("rank") or 0) for r in rows}

    def name(el: int | None) -> str:
        return players.get(el, f"#{el}") if el is not None else "?"

    # Tie-breaks favour the manager higher in the league table (lower rank number).
    def by_rank(entry: int) -> int:
        return -league_rank.get(entry, 10**9)

    # Winner / wooden spoon
    pts = {e: net_points(picks_by_entry[e]) for e in refs}
    win = _best(pts, key=lambda e: (pts[e], by_rank(e)))
    spoon = _best(pts, key=lambda e: (-pts[e], -by_rank(e)))

    # Captains
    caps = {e: captain_result(picks_by_entry[e], stats) for e in refs}

    def cap_award(e: int | None) -> CaptainAward | None:
        if e is None:
            return None
        el, p, m, vice, triple = caps[e]
        return CaptainAward(refs[e], name(el), p, m, vice, triple)

    best_cap = _best(caps, key=lambda e: (caps[e][1], by_rank(e)))
    worst_cap = _best(caps, key=lambda e: (-caps[e][1], -by_rank(e)))

    # Bench regret (Bench Boost means nothing was left on the bench)
    def bench(e: int) -> int:
        p = picks_by_entry[e]
        if p.get("active_chip") == "bboost":
            return 0
        return int((p.get("entry_history") or {}).get("points_on_bench") or 0)

    bench_e = _best((e for e in refs if bench(e) > 0), key=lambda e: (bench(e), by_rank(e)))

    # Biggest hit
    def hit(e: int) -> tuple[int, int]:
        eh = picks_by_entry[e].get("entry_history") or {}
        return int(eh.get("event_transfers_cost") or 0), int(eh.get("event_transfers") or 0)

    hit_e = _best((e for e in refs if hit(e)[0] > 0), key=lambda e: (hit(e)[0], by_rank(e)))

    # Rank movers (standings rank/last_rank only describe the latest GW)
    climber = faller = None
    if is_latest_gameweek:
        moves = {
            int(r["entry"]): int(r["last_rank"]) - int(r["rank"])
            for r in rows
            if r.get("last_rank") and r.get("rank")
        }
        up = _best((e for e in moves if moves[e] > 0), key=lambda e: (moves[e], by_rank(e)))
        down = _best((e for e in moves if moves[e] < 0), key=lambda e: (-moves[e], by_rank(e)))
        if up is not None:
            climber = RankMoveAward(refs[up], league_rank[up] + moves[up], league_rank[up], moves[up])
        if down is not None:
            faller = RankMoveAward(refs[down], league_rank[down] + moves[down], league_rank[down], moves[down])

    # Ownership across analysed managers (full 15-man squads)
    owners: Counter[int] = Counter()
    for e in refs:
        owners.update({p["element"] for p in picks_by_entry[e].get("picks", [])})
    n = len(refs)

    # Differential hero: best return from a player owned by <=20% of the league
    # (at least "only you" in small leagues).
    max_owners = max(1, int(n * DIFFERENTIAL_MAX_SHARE))
    diff_candidates: list[tuple[int, int, int]] = []  # (points, entry, element)
    for e in refs:
        for el, m in effective_multipliers(picks_by_entry[e]).items():
            if m > 0 and owners[el] <= max_owners:
                p = stats.get(el, (0, 0))[0] * m
                if p > 0:
                    diff_candidates.append((p, e, el))
    diff = _best(diff_candidates, key=lambda c: (c[0], -owners[c[2]], by_rank(c[1])))
    differential = (
        DifferentialAward(refs[diff[1]], name(diff[2]), diff[0], owners[diff[2]]) if diff else None
    )

    # Chips
    chips = [
        ChipPlay(refs[e], chip, CHIP_NAMES.get(chip, chip))
        for e in sorted(refs, key=lambda e: league_rank.get(e, 0))
        if (chip := picks_by_entry[e].get("active_chip"))
    ]

    # Template
    template = [
        Ownership(name(el), c, round(100 * c / n, 1))
        for el, c in sorted(owners.items(), key=lambda kv: (-kv[1], name(kv[0])))[:TEMPLATE_SIZE]
    ] if n else []

    return Report(
        league_id=league_id,
        league_name=league_name,
        gameweek=gameweek,
        is_latest_gameweek=is_latest_gameweek,
        managers_analysed=n,
        total_managers=None if truncated else len(standings),
        truncated=truncated,
        winner=PointsAward(refs[win], pts[win]) if win is not None else None,
        wooden_spoon=PointsAward(refs[spoon], pts[spoon]) if spoon is not None else None,
        best_captain=cap_award(best_cap),
        worst_captain=cap_award(worst_cap),
        bench_regret=BenchAward(refs[bench_e], bench(bench_e)) if bench_e is not None else None,
        biggest_hit=HitAward(refs[hit_e], *hit(hit_e)) if hit_e is not None else None,
        rank_climber=climber,
        rank_faller=faller,
        differential_hero=differential,
        chips_played=chips,
        template=template,
    )
