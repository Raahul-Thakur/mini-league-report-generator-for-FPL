"""Card rendering tests (offline; renders from FakeFPL fixtures)."""
import dataclasses
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.branding import Brand
from app.card import SIZES, award_slots, render_card
from app.config import Settings
from app.main import create_app
from app.text import BODY, DISPLAY, ELLIPSIS, clusters, fit
from scripts.render_samples import EDGE_VARIANTS, edge_case_report, sample_report
from tests.fake_fpl import CURRENT_GW, LEAGUE_ID, FakeFPL

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def open_png(data: bytes) -> Image.Image:
    assert data.startswith(PNG_MAGIC)
    return Image.open(io.BytesIO(data))


# ---- rendering ---------------------------------------------------------------------

@pytest.mark.parametrize("fmt,size", [("story", (1080, 1920)), ("square", (1080, 1080))])
def test_card_dimensions(fmt, size):
    img = open_png(render_card(sample_report(), fmt))
    assert img.size == size == SIZES[fmt]
    assert img.mode == "RGB"


@pytest.mark.parametrize("variant", sorted(EDGE_VARIANTS))
@pytest.mark.parametrize("fmt", ["story", "square"])
def test_edge_case_names_render(variant, fmt):
    img = open_png(render_card(edge_case_report(variant), fmt))
    assert img.size == SIZES[fmt]


def test_empty_report_renders():
    empty = dataclasses.replace(
        sample_report(), managers_analysed=0, winner=None, wooden_spoon=None,
        best_captain=None, worst_captain=None, bench_regret=None, biggest_hit=None,
        rank_climber=None, rank_faller=None, differential_hero=None,
    )
    assert award_slots(empty) == []
    assert open_png(render_card(empty, "square")).size == (1080, 1080)


def test_unknown_format_rejected():
    with pytest.raises(ValueError):
        render_card(sample_report(), "landscape")


def test_brand_colour_is_used():
    brand = Brand(primary="#00FF00")
    img = open_png(render_card(sample_report(), "square", brand))
    # The GAMEWEEK pill is filled with the primary colour.
    assert img.getpixel((60, 75)) == (0, 255, 0)


# ---- what goes on the card ------------------------------------------------------------

def test_latest_gw_slots():
    labels = [s.label for s in award_slots(sample_report())]
    assert labels == ["GW WINNER", "WOODEN SPOON", "BEST CAPTAIN", "WORST CAPTAIN",
                      "BENCH REGRET", "BIGGEST CLIMBER"]


def test_past_gw_fills_climber_slot_with_biggest_hit():
    labels = [s.label for s in award_slots(sample_report(latest=False))]
    assert "BIGGEST CLIMBER" not in labels and labels[-1] == "BIGGEST HIT"


def test_slot_details():
    slots = {s.label: s for s in award_slots(sample_report())}
    assert slots["BEST CAPTAIN"].detail == "Dee Example · Haaland (TC)"
    assert slots["BEST CAPTAIN"].stat == "39"
    assert slots["BIGGEST CLIMBER"].detail == "Cal Example · 6th → 3rd"
    assert slots["BIGGEST CLIMBER"].stat == "+3"


def test_undrawable_team_name_falls_back_to_manager():
    slots = award_slots(edge_case_report(3))
    assert slots[0].title == "Giorgi Beridze"  # Georgian team name has no bundled font
    assert slots[0].detail == ""  # not repeated underneath


# ---- text helpers ------------------------------------------------------------------------

def test_fit_shrinks_before_truncating():
    text, size = fit("Medium Length Team", DISPLAY, 420, 60, 30)
    assert text == "Medium Length Team" and 30 <= size < 60


def test_fit_truncates_with_ellipsis_at_min_size():
    text, size = fit("A" * 80, DISPLAY, 300, 60, 30)
    assert size == 30 and text.endswith(ELLIPSIS)
    assert DISPLAY.width(text, size) <= 300


def test_truncation_never_splits_an_emoji_sequence():
    family = "👨‍👩‍👧"
    text, _ = fit(("Team " + family) * 10, DISPLAY, 260, 40, 40)
    body = text.removesuffix(ELLIPSIS).rstrip()
    assert not body.endswith("‍") and not body.endswith("👨")


def test_clusters_keep_flags_and_combining_marks_together():
    assert clusters("🇧🇷é") == ["🇧🇷", "é"]


def test_fallback_fonts_per_script():
    def fonts(text):
        return [DISPLAY.files[i] for _, i in DISPLAY.runs(text)]

    assert fonts("فريق") == ["NotoSansArabic-Bold.ttf"]
    assert fonts("東京") == ["NotoSansCJK-Bold-subset.ttf"]
    assert fonts("서울") == ["NotoSansKR-Bold-subset.ttf"]
    assert fonts("Москва") == ["Inter-ExtraBold.ttf"]
    assert fonts("⚽") == ["NotoEmoji-Bold.ttf"]


def test_space_between_rtl_and_latin_uses_primary_font():
    runs = BODY.runs("محمد صلاح · left")
    assert runs[0] == ("محمد صلاح", BODY.files.index("NotoSansArabic-Regular.ttf"))
    assert runs[1][0].startswith(" ")


def test_uncovered_characters_dropped_and_stylised_text_folded():
    assert BODY.runs("ქართული") == []
    assert not BODY.legible("ქართული")
    assert "".join(r for r, _ in BODY.runs("𝓕𝓪𝓷𝓬𝔂")) == "Fancy"


# ---- endpoint ------------------------------------------------------------------------------

def client_for(fake=None, **settings):
    app = create_app(Settings(**settings))
    app.state.fpl = fake or FakeFPL()
    return TestClient(app), app.state.fpl


@pytest.mark.parametrize("fmt,size", [("story", (1080, 1920)), ("square", (1080, 1080))])
def test_card_endpoint(fmt, size):
    tc, _ = client_for()
    with tc:
        r = tc.get(f"/api/leagues/{LEAGUE_ID}/card.png?format={fmt}")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    assert open_png(r.content).size == size
    assert r.headers["content-disposition"] == (
        f'inline; filename="league-{LEAGUE_ID}-gw{CURRENT_GW}-{fmt}.png"'
    )


def test_card_endpoint_defaults_to_story_and_supports_download():
    tc, _ = client_for()
    with tc:
        r = tc.get(f"/api/leagues/{LEAGUE_ID}/card.png?download=true")
    assert open_png(r.content).size == (1080, 1920)
    assert r.headers["content-disposition"].startswith("attachment;")


def test_card_is_cached_per_league_gw_format():
    tc, fake = client_for()
    with tc:
        first = tc.get(f"/api/leagues/{LEAGUE_ID}/card.png?gw={CURRENT_GW}&format=square")
        n = len(fake.calls)
        second = tc.get(f"/api/leagues/{LEAGUE_ID}/card.png?gw={CURRENT_GW}&format=square")
        assert len(fake.calls) == n  # served from cache, FPL not touched
        assert second.content == first.content
        tc.get(f"/api/leagues/{LEAGUE_ID}/card.png?gw={CURRENT_GW}&format=story")
        assert len(fake.calls) > n  # different format is a different cache entry


def test_card_cache_expires():
    tc, fake = client_for(ttl_card=0)
    with tc:
        tc.get(f"/api/leagues/{LEAGUE_ID}/card.png")
        n = len(fake.calls)
        tc.get(f"/api/leagues/{LEAGUE_ID}/card.png")
        assert len(fake.calls) > n


def test_card_endpoint_errors():
    tc, _ = client_for()
    with tc:
        assert tc.get(f"/api/leagues/{LEAGUE_ID}/card.png?format=landscape").status_code == 422
        r = tc.get("/api/leagues/1/card.png")
        assert r.status_code == 404 and r.json()["error"] == "league_not_found"
        assert tc.get(f"/api/leagues/{LEAGUE_ID}/card.png?gw={CURRENT_GW + 1}").status_code == 409
