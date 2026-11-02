"""Render sample cards from the offline fixtures into samples/ (no network).

    python -m scripts.render_samples
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

from app.card import render_card
from app.report import build_report, players_from_bootstrap
from tests.fake_fpl import CURRENT_GW, LEAGUE_ID, build_fixtures

OUT = Path(__file__).resolve().parent.parent / "samples"


def sample_report(fx=None, latest=True, league_name=None, truncated=False):
    fx = fx or build_fixtures()
    return build_report(
        league_id=LEAGUE_ID,
        league_name=league_name or fx["league"]["name"],
        gameweek=CURRENT_GW,
        is_latest_gameweek=latest,
        standings=fx["standings"],
        players=players_from_bootstrap(fx["bootstrap"]),
        live=fx["live"],
        picks_by_entry=fx["picks"],
        truncated=truncated,
    )


LONG = ("Absolutely Massive Haaland Hauls FC Of Destiny", "Bartholomew Montgomery-Fitzwilliam")
FILLER = [("Plain Team", "Plain Manager")] * 6

# Entry 104 wins and is best captain, 106 gets the spoon and worst captain,
# 102 gets bench regret and biggest hit. Each variant puts different scripts there.
EDGE_VARIANTS = {
    1: {104: ("👑🔥 Big Chungus XI 🔥👑", "Ελένη Παπαδοπούλου"),
        106: ("東京ドリームス", "山田 太郎"),
        102: ("فريق الأحلام", "محمد صلاح")},
    2: {104: ("ทีมไทย สู้ๆ", "Сергей Иванов"),
        106: ("서울 FC", "김민준"),
        102: ("टीम इंडिया 🇮🇳", "राहुल ठाकुर")},
    # Georgian has no bundled font, so the card falls back to the manager's name.
    3: {104: ("ქართული გუნდი", "Giorgi Beridze"),
        106: LONG,
        102: ("Ⓦⓘⓡⓔⓓ 𝓕𝓪𝓷𝓬𝔂 𝕋𝕖𝕩𝕥", "ｆｕｌｌｗｉｄｔｈ ｎａｍｅ")},
}


def edge_case_report(variant: int):
    """Long, emoji, RTL, Indic, Thai, Greek, Cyrillic, CJK, Hangul and uncovered names.

    Past GW (so no climber) and truncated, to exercise those states too.
    """
    fx = build_fixtures()
    names = EDGE_VARIANTS[variant]
    for row in fx["standings"]:
        row["entry_name"], row["player_name"] = names.get(row["entry"], FILLER[0])
    return sample_report(fx, latest=False, truncated=True,
                         league_name="The Unnecessarily Long Name Of Our Office Fantasy Football League 2026/27 ⚽")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    r = sample_report()
    empty = dataclasses.replace(
        sample_report(), managers_analysed=0, winner=None, wooden_spoon=None, best_captain=None,
        worst_captain=None, bench_regret=None, biggest_hit=None, rank_climber=None,
        rank_faller=None, differential_hero=None, chips_played=[], template=[],
    )
    reports = [("", r), ("empty-", empty)]
    reports += [(f"edge-cases-{v}-", edge_case_report(v)) for v in EDGE_VARIANTS]
    for name, rep in reports:
        for fmt in ("story", "square"):
            path = OUT / f"{name}{fmt}.png"
            path.write_bytes(render_card(rep, fmt))
            print(path.relative_to(OUT.parent))


if __name__ == "__main__":
    main()
