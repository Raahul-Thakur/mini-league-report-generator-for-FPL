"""API + service tests, with FakeFPL injected (no network)."""
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.fpl_client import FPLError
from app.main import create_app
from tests.fake_fpl import CURRENT_GW, LEAGUE_ID, FakeFPL, build_fixtures


def client_for(fake=None, **settings):
    app = create_app(Settings(**settings))
    app.state.fpl = fake or FakeFPL()
    return TestClient(app), app.state.fpl


def test_report_defaults_to_current_gameweek():
    tc, _ = client_for()
    with tc:
        r = tc.get(f"/api/leagues/{LEAGUE_ID}/report")
    assert r.status_code == 200
    body = r.json()
    assert body["gameweek"] == CURRENT_GW and body["is_latest_gameweek"] is True
    assert body["latest_gameweek"] == CURRENT_GW
    assert body["league_name"] == "Office Legends 🏆"
    assert body["winner"]["manager"]["entry_id"] == 104
    assert body["truncated"] is False and body["total_managers"] == 6
    assert "Not affiliated" in body["disclaimer"]
    assert "max-age" in r.headers["cache-control"]


def test_past_gameweek_hides_rank_movers():
    tc, _ = client_for()
    with tc:
        body = tc.get(f"/api/leagues/{LEAGUE_ID}/report?gw={CURRENT_GW - 1}").json()
    assert body["is_latest_gameweek"] is False
    assert body["latest_gameweek"] == CURRENT_GW
    assert body["rank_climber"] is None and body["rank_faller"] is None


def test_unknown_league_is_404():
    tc, _ = client_for()
    with tc:
        r = tc.get("/api/leagues/1/report")
    assert r.status_code == 404 and r.json()["error"] == "league_not_found"


def test_future_gameweek_is_409():
    tc, _ = client_for()
    with tc:
        r = tc.get(f"/api/leagues/{LEAGUE_ID}/report?gw={CURRENT_GW + 1}")
    assert r.status_code == 409 and r.json()["error"] == "gameweek_not_started"


@pytest.mark.parametrize("q", ["gw=0", "gw=39", "gw=abc"])
def test_bad_gameweek_is_422(q):
    tc, _ = client_for()
    with tc:
        assert tc.get(f"/api/leagues/{LEAGUE_ID}/report?{q}").status_code == 422


def test_preseason_is_409():
    fx = build_fixtures()
    for e in fx["bootstrap"]["events"]:
        e["is_current"] = e["finished"] = False
    tc, _ = client_for(FakeFPL(fx))
    with tc:
        assert tc.get(f"/api/leagues/{LEAGUE_ID}/report").status_code == 409


def test_big_league_is_capped_and_flagged():
    fake = FakeFPL(build_fixtures(extra_managers=94))  # 100 managers, 2 pages
    tc, _ = client_for(fake, max_entries=50)
    with tc:
        body = tc.get(f"/api/leagues/{LEAGUE_ID}/report").json()
    assert body["truncated"] is True and body["total_managers"] is None
    assert body["managers_analysed"] == 50 and body["max_entries"] == 50
    picks_calls = [c for c in fake.calls if c[0] == "picks"]
    assert len(picks_calls) == 50
    assert [c for c in fake.calls if c[0] == "standings"] == [("standings", LEAGUE_ID, 1)]


def test_league_exactly_at_cap_is_not_truncated():
    fake = FakeFPL(build_fixtures(extra_managers=44))  # exactly 50
    tc, _ = client_for(fake, max_entries=50)
    with tc:
        body = tc.get(f"/api/leagues/{LEAGUE_ID}/report").json()
    assert body["truncated"] is False and body["total_managers"] == 50


def test_cap_above_page_size_fetches_more_pages():
    fake = FakeFPL(build_fixtures(extra_managers=94))
    tc, _ = client_for(fake, max_entries=75)
    with tc:
        body = tc.get(f"/api/leagues/{LEAGUE_ID}/report").json()
    assert body["managers_analysed"] == 75 and body["truncated"] is True
    assert [c[2] for c in fake.calls if c[0] == "standings"] == [1, 2]


def test_missing_picks_are_skipped():
    tc, _ = client_for(FakeFPL(missing_picks={104}))
    with tc:
        body = tc.get(f"/api/leagues/{LEAGUE_ID}/report").json()
    assert body["managers_analysed"] == 5 and body["winner"]["manager"]["entry_id"] == 101


def test_fpl_outage_is_503_with_retry_after():
    class Down(FakeFPL):
        async def bootstrap(self):
            raise FPLError("down")

    tc, _ = client_for(Down())
    with tc:
        r = tc.get(f"/api/leagues/{LEAGUE_ID}/report")
    assert r.status_code == 503 and r.headers["retry-after"] == "120"


def test_health():
    tc, _ = client_for()
    with tc:
        assert tc.get("/api/health").json() == {"ok": True}
