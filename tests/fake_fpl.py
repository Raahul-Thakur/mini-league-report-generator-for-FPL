"""Offline fake of FPLClient, with fixtures in the real FPL API's JSON shapes.

The league is designed so every award has a single, known answer:

  rank (last)  entry  team                    GW pts  hit  net  captain -> result
  1 (2)        101    Haaland Globetrotters   70      0    70   Haaland 13x2 = 26
  2 (1)        102    Salah Shakers           55      8    47   Salah 2x2 = 4      bench 12
  3 (6)        103    Palmer Pals             60      0    60   Palmer DNP -> vice Saka 8x2 = 16
  4 (4)        104    Triple Trouble          80      0    80   TC Haaland 13x3 = 39
  5 (5)        105    Bench Boosters          40      0    40   Salah 4 (Bench Boost; bench pts ignored)
  6 (3)        106    Spoon Fed ⚽ 東京       30      4    26   Palmer DNP, vice DNP -> 0; owns Isak (15) alone

Expected: winner 104, spoon 106, best captain 104, worst captain 106,
bench regret 102, biggest hit 102, climber 103 (+3), faller 106 (-3),
differential hero 106 (Isak 15), chips 104 3xc + 105 bboost, template top = GK (100%).
"""
from __future__ import annotations

import copy

from app.fpl_client import FPLNotFound

LEAGUE_ID = 424242
CURRENT_GW = 10

HAALAND, SALAH, PALMER, SAKA, ISAK, COMMON_GK, DNP_VICE = 1, 2, 3, 4, 5, 6, 7

PLAYERS = {
    HAALAND: ("Haaland", 13, 90),
    SALAH: ("M.Salah", 2, 90),
    PALMER: ("Palmer", 0, 0),
    SAKA: ("Saka", 8, 90),
    ISAK: ("Isak", 15, 90),
    COMMON_GK: ("Raya", 6, 90),
    DNP_VICE: ("Benchwarmer", 0, 0),
}


def filler_ids(entry: int, n: int) -> list[int]:
    return [1000 + entry * 20 + i for i in range(n)]


MANAGERS = [
    # entry, team, manager, rank, last_rank, key starters, captain, vice, chip, pts, cost, transfers, bench
    (101, "Haaland Globetrotters", "Alex Example", 1, 2, [HAALAND], HAALAND, COMMON_GK, None, 70, 0, 1, 3),
    (102, "Salah Shakers", "Bea Example", 2, 1, [SALAH], SALAH, COMMON_GK, None, 55, 8, 3, 12),
    (103, "Palmer Pals", "Cal Example", 3, 6, [PALMER, SAKA], PALMER, SAKA, None, 60, 0, 1, 1),
    (104, "Triple Trouble", "Dee Example", 4, 4, [HAALAND], HAALAND, COMMON_GK, "3xc", 80, 0, 0, 2),
    (105, "Bench Boosters", "Eli Example", 5, 5, [SALAH], SALAH, COMMON_GK, "bboost", 40, 0, 0, 20),
    (106, "Spoon Fed ⚽ 東京", "Fay Example", 6, 3, [PALMER, DNP_VICE, ISAK], PALMER, DNP_VICE, None, 30, 4, 2, 0),
]


def _picks(entry, key, captain, vice, chip, pts, cost, transfers, bench_pts):
    starters = [COMMON_GK] + key
    starters += filler_ids(entry, 11 - len(starters))
    bench = filler_ids(entry, 15)[11 - (len(key) + 1):][:4]
    picks = []
    for pos, el in enumerate(starters + bench, start=1):
        if pos <= 11:
            mult = (3 if chip == "3xc" else 2) if el == captain else 1
        else:
            mult = 1 if chip == "bboost" else 0
        picks.append({
            "element": el,
            "position": pos,
            "multiplier": mult,
            "is_captain": el == captain,
            "is_vice_captain": el == vice,
        })
    return {
        "active_chip": chip,
        "automatic_subs": [],
        "entry_history": {
            "event": CURRENT_GW,
            "points": pts,
            "total_points": 500 + pts,
            "rank": 1000,
            "overall_rank": 100000,
            "bank": 5,
            "value": 1000,
            "event_transfers": transfers,
            "event_transfers_cost": cost,
            "points_on_bench": bench_pts,
        },
        "picks": picks,
    }


def build_fixtures(extra_managers: int = 0) -> dict:
    elements = [
        {"id": i, "web_name": name, "element_type": 3, "team": 1}
        for i, (name, _, _) in PLAYERS.items()
    ]
    live = [
        {"id": i, "stats": {"total_points": p, "minutes": m}} for i, (_, p, m) in PLAYERS.items()
    ]
    standings, picks = [], {}
    managers = list(MANAGERS)
    for k in range(extra_managers):
        e = 200 + k
        managers.append((e, f"Extra Team {k}", f"Extra {k}", 7 + k, 7 + k, [], COMMON_GK, HAALAND, None, 20, 0, 0, 0))
    for (e, team, mgr, rank, last, key, cap, vice, chip, pts, cost, tr, bench) in managers:
        standings.append({
            "id": e * 7, "entry": e, "entry_name": team, "player_name": mgr,
            "rank": rank, "last_rank": last, "rank_sort": rank,
            "total": 500 + pts - cost, "event_total": pts - cost,
        })
        picks[e] = _picks(e, key, cap, vice, chip, pts, cost, tr, bench)
        for el in filler_ids(e, 15):
            elements.append({"id": el, "web_name": f"Filler{el}", "element_type": 2, "team": 2})
            live.append({"id": el, "stats": {"total_points": 2, "minutes": 90}})
    events = [
        {"id": gw, "name": f"Gameweek {gw}", "is_current": gw == CURRENT_GW,
         "is_previous": gw == CURRENT_GW - 1, "is_next": gw == CURRENT_GW + 1,
         "finished": gw < CURRENT_GW, "data_checked": gw < CURRENT_GW}
        for gw in range(1, 39)
    ]
    return {
        "bootstrap": {"events": events, "elements": elements, "teams": []},
        "league": {"id": LEAGUE_ID, "name": "Office Legends 🏆", "scoring": "c"},
        "standings": standings,
        "live": {"elements": live},
        "picks": picks,
    }


class FakeFPL:
    """Same async interface as FPLClient; records calls so tests can assert politeness."""

    PAGE_SIZE = 50

    def __init__(self, fixtures: dict | None = None, missing_picks: set[int] = frozenset()):
        self.fx = fixtures or build_fixtures()
        self.missing_picks = set(missing_picks)
        self.calls: list[tuple] = []

    async def bootstrap(self):
        self.calls.append(("bootstrap",))
        return copy.deepcopy(self.fx["bootstrap"])

    async def league_standings(self, league_id, page=1):
        self.calls.append(("standings", league_id, page))
        if league_id != LEAGUE_ID:
            raise FPLNotFound(f"league {league_id}")
        rows = self.fx["standings"]
        start = (page - 1) * self.PAGE_SIZE
        return {
            "league": dict(self.fx["league"]),
            "new_entries": {"has_next": False, "page": 1, "results": []},
            "standings": {
                "has_next": start + self.PAGE_SIZE < len(rows),
                "page": page,
                "results": copy.deepcopy(rows[start:start + self.PAGE_SIZE]),
            },
        }

    async def event_live(self, gw):
        self.calls.append(("live", gw))
        return copy.deepcopy(self.fx["live"])

    async def entry_picks(self, entry_id, gw):
        self.calls.append(("picks", entry_id, gw))
        if entry_id in self.missing_picks or entry_id not in self.fx["picks"]:
            raise FPLNotFound(f"picks {entry_id}")
        return copy.deepcopy(self.fx["picks"][entry_id])

    async def aclose(self):
        pass
