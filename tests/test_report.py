"""Report engine tests (pure; fixtures from tests/fake_fpl.py)."""
import copy

from app.report import (
    build_report,
    captain_result,
    effective_multipliers,
    live_stats,
    players_from_bootstrap,
)
from tests.fake_fpl import (
    CURRENT_GW,
    ISAK,
    LEAGUE_ID,
    SAKA,
    build_fixtures,
)


def run(fx=None, latest=True, truncated=False, drop=()):
    fx = fx or build_fixtures()
    picks = {e: p for e, p in fx["picks"].items() if e not in drop}
    return build_report(
        league_id=LEAGUE_ID,
        league_name=fx["league"]["name"],
        gameweek=CURRENT_GW,
        is_latest_gameweek=latest,
        standings=fx["standings"],
        players=players_from_bootstrap(fx["bootstrap"]),
        live=fx["live"],
        picks_by_entry=picks,
        truncated=truncated,
    )


def test_winner_and_wooden_spoon_use_points_after_hits():
    r = run()
    assert r.winner.manager.entry_id == 104 and r.winner.points == 80
    assert r.wooden_spoon.manager.entry_id == 106 and r.wooden_spoon.points == 26


def test_best_captain_is_triple_captain_aware():
    r = run()
    c = r.best_captain
    assert c.manager.entry_id == 104
    assert (c.player_name, c.points, c.multiplier, c.triple_captain) == ("Haaland", 39, 3, True)


def test_worst_captain_when_captain_and_vice_both_blank():
    r = run()
    c = r.worst_captain
    assert c.manager.entry_id == 106 and c.points == 0 and not c.used_vice


def test_vice_captain_fallback():
    fx = build_fixtures()
    stats = live_stats(fx["live"])
    el, pts, mult, used_vice, triple = captain_result(fx["picks"][103], stats)
    assert (el, pts, mult, used_vice, triple) == (SAKA, 16, 2, True, False)


def test_bench_regret_ignores_bench_boost():
    r = run()
    assert r.bench_regret.manager.entry_id == 102 and r.bench_regret.points == 12


def test_biggest_hit():
    r = run()
    assert r.biggest_hit.manager.entry_id == 102
    assert (r.biggest_hit.cost, r.biggest_hit.transfers) == (8, 3)


def test_no_hit_award_when_nobody_took_a_hit():
    fx = build_fixtures()
    for p in fx["picks"].values():
        p["entry_history"]["event_transfers_cost"] = 0
    assert run(fx).biggest_hit is None


def test_rank_movers_on_latest_gameweek():
    r = run()
    assert r.rank_climber.manager.entry_id == 103
    assert (r.rank_climber.previous_rank, r.rank_climber.rank, r.rank_climber.places) == (6, 3, 3)
    assert r.rank_faller.manager.entry_id == 106
    assert (r.rank_faller.previous_rank, r.rank_faller.rank, r.rank_faller.places) == (3, 6, -3)


def test_rank_movers_hidden_for_past_gameweeks():
    r = run(latest=False)
    assert r.rank_climber is None and r.rank_faller is None


def test_new_entrant_without_last_rank_is_not_a_climber():
    fx = build_fixtures()
    fx["standings"][2]["last_rank"] = 0
    assert run(fx).rank_climber.manager.entry_id == 101


def test_differential_hero():
    r = run()
    d = r.differential_hero
    assert d.manager.entry_id == 106
    assert (d.player_name, d.points, d.owned_by) == ("Isak", 15, 1)


def test_chips_played_in_league_order():
    r = run()
    assert [(c.manager.entry_id, c.chip, c.chip_name) for c in r.chips_played] == [
        (104, "3xc", "Triple Captain"),
        (105, "bboost", "Bench Boost"),
    ]


def test_template_ownership():
    r = run()
    top = r.template[0]
    assert (top.player_name, top.owners, top.percent) == ("Raya", 6, 100.0)
    haaland = next(t for t in r.template if t.player_name == "Haaland")
    assert haaland.owners == 2 and haaland.percent == 33.3
    assert len(r.template) == 10


def test_managers_without_picks_are_skipped():
    r = run(drop={104})
    assert r.managers_analysed == 5
    assert r.winner.manager.entry_id == 101


def test_empty_league_gives_empty_awards():
    fx = build_fixtures()
    fx["standings"] = []
    r = run(fx)
    assert r.managers_analysed == 0 and r.winner is None and r.template == []


def test_truncated_flag_and_unknown_total():
    r = run(truncated=True)
    assert r.truncated and r.total_managers is None
    assert run().total_managers == 6


def test_tie_break_favours_higher_league_rank():
    fx = build_fixtures()
    fx["picks"][101]["entry_history"]["points"] = 80  # ties with 104 on 80
    assert run(fx).winner.manager.entry_id == 101


def test_automatic_subs_change_multipliers():
    picks = {
        "picks": [
            {"element": 1, "multiplier": 1, "is_captain": False, "is_vice_captain": False},
            {"element": 2, "multiplier": 0, "is_captain": False, "is_vice_captain": False},
        ],
        "automatic_subs": [{"element_in": 2, "element_out": 1}],
    }
    assert effective_multipliers(picks) == {1: 0, 2: 1}


def test_differential_counts_autosubbed_bench_player():
    fx = build_fixtures()
    # 106 no longer starts Isak; he's on the bench and comes on as an auto-sub.
    picks = fx["picks"][106]["picks"]
    isak = next(p for p in picks if p["element"] == ISAK)
    bench = next(p for p in picks if p["position"] == 12)
    isak["position"], bench["position"] = 12, isak["position"]
    isak["multiplier"], bench["multiplier"] = 0, 1
    fx["picks"][106]["automatic_subs"] = [{"element_in": ISAK, "element_out": bench["element"]}]
    assert run(fx).differential_hero.player_name == "Isak"


def test_report_does_not_mutate_inputs():
    fx = build_fixtures()
    before = copy.deepcopy(fx)
    run(fx)
    assert fx == before


def test_report_serialises_to_dict():
    d = run().to_dict()
    assert d["winner"]["manager"]["team_name"] == "Triple Trouble"
    assert d["best_captain"]["player_name"] == "Haaland"
