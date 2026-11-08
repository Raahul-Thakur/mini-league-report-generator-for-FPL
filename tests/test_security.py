"""Internal key, rate limiting and CORS (offline)."""
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from tests.fake_fpl import LEAGUE_ID, FakeFPL

KEY = "s3cret-key"
REPORT = f"/api/leagues/{LEAGUE_ID}/report"
CARD = f"/api/leagues/{LEAGUE_ID}/card.png?format=square"


def client_for(**settings) -> TestClient:
    app = create_app(Settings(**settings))
    app.state.fpl = FakeFPL()
    return TestClient(app)


def site(ip: str = "203.0.113.7", key: str = KEY) -> dict:
    """Headers the website sends."""
    return {"X-Internal-Key": key, "X-Client-IP": ip}


# ---- internal key ------------------------------------------------------------------

def test_no_key_configured_means_open_api():
    with client_for() as tc:
        assert tc.get(REPORT).status_code == 200


def test_key_required_when_configured():
    with client_for(internal_api_key=KEY) as tc:
        r = tc.get(REPORT)
        assert r.status_code == 403 and r.json()["error"] == "forbidden"
        assert tc.get(CARD, headers={"X-Internal-Key": "wrong"}).status_code == 403
        assert tc.get(REPORT, headers=site()).status_code == 200
        assert tc.get(CARD, headers=site()).status_code == 200


def test_health_stays_open_for_platform_checks():
    with client_for(internal_api_key=KEY) as tc:
        assert tc.get("/api/health").status_code == 200


# ---- rate limiting ------------------------------------------------------------------

def test_rate_limit_returns_friendly_429():
    with client_for(rate_limit_report="2/minute") as tc:
        assert [tc.get(REPORT).status_code for _ in range(3)] == [200, 200, 429]
        r = tc.get(REPORT)
        assert r.json()["error"] == "rate_limited" and r.headers["retry-after"] == "60"


def test_limits_are_per_visitor_ip_when_the_site_vouches_for_it():
    with client_for(internal_api_key=KEY, rate_limit_report="2/minute") as tc:
        for _ in range(2):
            assert tc.get(REPORT, headers=site("198.51.100.1")).status_code == 200
        assert tc.get(REPORT, headers=site("198.51.100.1")).status_code == 429
        # A different visitor behind the same website server is unaffected
        assert tc.get(REPORT, headers=site("198.51.100.2")).status_code == 200


def test_client_ip_header_ignored_without_valid_key():
    # Without the key, X-Client-IP can't be used to dodge the limit.
    with client_for(rate_limit_report="2/minute") as tc:
        codes = [tc.get(REPORT, headers={"X-Client-IP": f"10.0.0.{i}"}).status_code for i in range(3)]
        assert codes == [200, 200, 429]


def test_garbage_client_ip_falls_back_to_peer():
    with client_for(internal_api_key=KEY, rate_limit_report="1/minute") as tc:
        assert tc.get(REPORT, headers=site("not-an-ip")).status_code == 200
        assert tc.get(REPORT, headers=site("also-not-an-ip")).status_code == 429


def test_report_and_card_have_separate_limits():
    with client_for(rate_limit_report="1/minute", rate_limit_card="5/minute") as tc:
        assert tc.get(REPORT).status_code == 200
        assert tc.get(REPORT).status_code == 429
        assert tc.get(CARD).status_code == 200


def test_empty_limit_disables_rate_limiting():
    with client_for(rate_limit_report="") as tc:
        assert all(tc.get(REPORT).status_code == 200 for _ in range(40))


def test_responses_are_cdn_cacheable():
    with client_for() as tc:
        assert "s-maxage=300" in tc.get(REPORT).headers["cache-control"]
        assert "s-maxage=300" in tc.get(CARD).headers["cache-control"]


# ---- CORS ---------------------------------------------------------------------------

def test_no_cors_headers_by_default():
    with client_for() as tc:
        r = tc.get(REPORT, headers={"Origin": "https://evil.example"})
        assert "access-control-allow-origin" not in r.headers


def test_cors_allows_only_configured_origins():
    with client_for(cors_origins=("https://myleague.app",)) as tc:
        ok = tc.get(REPORT, headers={"Origin": "https://myleague.app"})
        assert ok.headers["access-control-allow-origin"] == "https://myleague.app"
        other = tc.get(REPORT, headers={"Origin": "https://evil.example"})
        assert "access-control-allow-origin" not in other.headers


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://a.app/, https://b.app")
    monkeypatch.setenv("INTERNAL_API_KEY", "k")
    monkeypatch.setenv("RATE_LIMIT_REPORT", "")
    s = Settings.from_env()
    assert s.cors_origins == ("https://a.app", "https://b.app")
    assert s.internal_api_key == "k" and s.rate_limit_report == ""
