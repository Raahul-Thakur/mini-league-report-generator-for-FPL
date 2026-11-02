"""Render a Report as a shareable PNG card (Instagram story or square post).

Pure apart from reading the bundled font files: Report in, PNG bytes out.
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

from PIL import Image, ImageDraw, ImageFilter

from app.branding import Brand
from app.models import Report
from app.text import BODY, DISPLAY, HEAVY, LABEL, FontStack, clean, fit

CardFormat = Literal["story", "square"]
SIZES: dict[str, tuple[int, int]] = {"story": (1080, 1920), "square": (1080, 1080)}
DISCLAIMER = "Not affiliated with the Premier League or Fantasy Premier League."
SLOTS = 6


# ---- content -------------------------------------------------------------------

def _join(*parts: str) -> str:
    return " · ".join(p for p in parts if p)


@dataclass(frozen=True)
class Slot:
    icon: str
    label: str
    title: str  # team name
    detail: str  # manager name + context
    stat: str
    unit: str
    tone: Literal["good", "bad"]


def _ordinal(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _minus(n: int) -> str:
    return f"−{abs(n)}"  # true minus sign reads better than a hyphen at display sizes


def award_slots(r: Report) -> list[Slot]:
    """The six awards for the card, in priority order, skipping any that don't apply."""
    out: list[Slot] = []

    def who(m) -> str:
        if not BODY.legible(m.manager_name) or team(m) == m.manager_name:
            return ""  # unreadable, or already shown as the title
        return clean(m.manager_name)

    def team(m) -> str:
        # Fall back when nothing in the team name is drawable with the bundled fonts.
        if DISPLAY.legible(m.team_name):
            return m.team_name
        return m.manager_name if DISPLAY.legible(m.manager_name) else f"Team {m.entry_id}"

    if r.winner:
        out.append(Slot("🏆", "GW WINNER", team(r.winner.manager), who(r.winner.manager),
                        str(r.winner.points), "PTS", "good"))
    if r.wooden_spoon:
        out.append(Slot("🥄", "WOODEN SPOON", team(r.wooden_spoon.manager),
                        who(r.wooden_spoon.manager), str(r.wooden_spoon.points), "PTS", "bad"))
    for cap, icon, label, tone in (
        (r.best_captain, "👑", "BEST CAPTAIN", "good"),
        (r.worst_captain, "🙈", "WORST CAPTAIN", "bad"),
    ):
        if cap:
            tag = " (TC)" if cap.triple_captain else ""
            vice = " · vice stepped in" if cap.used_vice else ""
            out.append(Slot(icon, label, team(cap.manager),
                            _join(who(cap.manager), f"{cap.player_name}{tag}{vice}"),
                            str(cap.points), "PTS", tone))
    if r.bench_regret:
        out.append(Slot("🪑", "BENCH REGRET", team(r.bench_regret.manager),
                        _join(who(r.bench_regret.manager), "left on the bench"),
                        str(r.bench_regret.points), "PTS", "bad"))
    if r.rank_climber:
        c = r.rank_climber
        out.append(Slot("📈", "BIGGEST CLIMBER", team(c.manager),
                        _join(who(c.manager), f"{_ordinal(c.previous_rank)} → {_ordinal(c.rank)}"),
                        f"+{c.places}", "PLACES", "good"))
    # Fillers for awards that didn't happen this week.
    if r.biggest_hit:
        h = r.biggest_hit
        out.append(Slot("💸", "BIGGEST HIT", team(h.manager),
                        _join(who(h.manager), f"{h.transfers} transfers"),
                        _minus(h.cost), "PTS", "bad"))
    if r.differential_hero:
        d = r.differential_hero
        owners = "only owner" if d.owned_by == 1 else f"{d.owned_by} owners"
        out.append(Slot("🎯", "DIFFERENTIAL HERO", team(d.manager),
                        _join(who(d.manager), f"{d.player_name} ({owners})"),
                        str(d.points), "PTS", "good"))
    if r.rank_faller:
        f = r.rank_faller
        out.append(Slot("📉", "BIGGEST FALLER", team(f.manager),
                        _join(who(f.manager), f"{_ordinal(f.previous_rank)} → {_ordinal(f.rank)}"),
                        _minus(f.places), "PLACES", "bad"))
    return out[:SLOTS]


# ---- drawing helpers -----------------------------------------------------------

@dataclass(frozen=True)
class BlockStyle:
    pad: int
    radius: int
    bar: int
    label: int
    title: int
    title_min: int
    detail: int
    detail_min: int
    stat: int
    unit: int


STORY_BLOCK = BlockStyle(pad=34, radius=28, bar=10, label=27, title=58, title_min=36,
                         detail=30, detail_min=24, stat=78, unit=22)
SQUARE_BLOCK = BlockStyle(pad=24, radius=22, bar=8, label=20, title=40, title_min=26,
                          detail=22, detail_min=18, stat=50, unit=16)


@lru_cache(maxsize=8)
def _background(size: tuple[int, int], brand: Brand) -> Image.Image:
    """Dark base with two soft colour glows. Blurred at 1/8 scale for speed."""
    w, h = size
    small = (w // 8, h // 8)
    base = Image.new("RGB", small, brand.rgb("background"))
    glow = Image.new("RGBA", small, (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    sw, sh = small
    g.ellipse((sw * 0.45, -sh * 0.25, sw * 1.35, sh * 0.35), fill=brand.rgb("primary") + (95,))
    g.ellipse((-sw * 0.5, sh * 0.7, sw * 0.5, sh * 1.25), fill=brand.rgb("accent") + (45,))
    glow = glow.filter(ImageFilter.GaussianBlur(min(small) / 5))
    base.paste(glow, (0, 0), glow)
    return base.resize(size, Image.Resampling.BICUBIC)


def _draw_block(img: Image.Image, box: tuple[int, int, int, int], slot: Slot,
                st: BlockStyle, brand: Brand) -> None:
    x0, y0, x1, y1 = box
    d = ImageDraw.Draw(img)
    tone = brand.rgb("accent") if slot.tone == "good" else brand.rgb("primary")
    d.rounded_rectangle(box, radius=st.radius, fill=brand.rgb("surface"))
    d.rounded_rectangle((x0, y0, x0 + st.bar * 2, y1), radius=st.radius, fill=tone)
    d.rectangle((x0 + st.bar, y0, x0 + st.bar * 2 + 2, y1), fill=brand.rgb("surface"))

    left = x0 + st.bar + st.pad
    right = x1 - st.pad
    # Content height: label + gap + title + gap + detail; centre it vertically.
    gap1, gap2 = int(st.label * 0.75), int(st.detail * 0.55)
    content = st.label + gap1 + st.title + gap2 + st.detail
    top = y0 + (y1 - y0 - content) // 2
    label_y = top + st.label
    title_y = label_y + gap1 + st.title
    detail_y = title_y + gap2 + st.detail

    LABEL.draw(d, (left, label_y), f"{slot.icon}  {slot.label}", st.label, tone)

    stat_w = HEAVY.width(slot.stat, st.stat)
    unit_w = LABEL.width(slot.unit, st.unit)
    col = max(stat_w, unit_w)
    HEAVY.draw(d, (right, title_y + st.title * 0.05), slot.stat, st.stat, brand.rgb("text"), anchor="rs")
    LABEL.draw(d, (right, detail_y), slot.unit, st.unit, brand.rgb("muted"), anchor="rs")

    text_w = right - left - col - st.pad
    title, ts = fit(slot.title, DISPLAY, text_w, st.title, st.title_min)
    DISPLAY.draw(d, (left, title_y), title, ts, brand.rgb("text"))
    detail, ds = fit(slot.detail, BODY, text_w, st.detail, st.detail_min)
    BODY.draw(d, (left, detail_y), detail, ds, brand.rgb("muted"))


def _pill(d: ImageDraw.ImageDraw, x: int, baseline: int, text: str, size: int,
          stack: FontStack, fill, color) -> int:
    """Rounded pill whose text sits on `baseline`. Returns the pill's right edge."""
    w = stack.width(text, size)
    padx, pady = size * 0.75, size * 0.45
    top, bottom = baseline - size * 0.92 - pady, baseline + size * 0.2 + pady
    d.rounded_rectangle((x, top, x + w + 2 * padx, bottom), radius=(bottom - top) / 2, fill=fill)
    stack.draw(d, (x + padx, baseline), text, size, color)
    return int(x + w + 2 * padx)


def _subtitle(r: Report) -> str:
    if r.truncated:
        return f"Top {r.managers_analysed} managers"
    n = r.managers_analysed
    return f"{n} manager{'s' if n != 1 else ''}"


def _footer(d: ImageDraw.ImageDraw, w: int, cta_y: int, mark_y: int, disc_y: int,
            sizes: tuple[int, int, int], brand: Brand) -> None:
    cta, mark, disc = sizes
    lead = "Get your league's report → "
    url = clean(brand.site_url)
    total = LABEL.width(lead, cta) + HEAVY.width(url, cta)
    x = (w - total) / 2
    x += LABEL.draw(d, (x, cta_y), lead, cta, brand.rgb("text"))
    HEAVY.draw(d, (x, cta_y), url, cta, brand.rgb("accent"))
    LABEL.draw(d, (w / 2, mark_y), f"{clean(brand.site_name)} • {clean(brand.handle)}",
               mark, brand.rgb("muted"), anchor="ms")
    BODY.draw(d, (w / 2, disc_y), DISCLAIMER, disc, brand.rgb("muted") + (150,), anchor="ms")


def _empty(d: ImageDraw.ImageDraw, w: int, y: int, size: int, brand: Brand) -> None:
    DISPLAY.draw(d, (w / 2, y), "No results yet", size, brand.rgb("text"), anchor="ms")
    BODY.draw(d, (w / 2, y + size * 1.2), "Check back once the gameweek is underway",
              int(size * 0.5), brand.rgb("muted"), anchor="ms")


# ---- layouts --------------------------------------------------------------------

def _render_story(r: Report, brand: Brand) -> Image.Image:
    w, h = SIZES["story"]
    img = _background((w, h), brand).copy()
    d = ImageDraw.Draw(img, "RGBA")
    m = 60  # side margin; content also stays clear of IG's top/bottom overlays

    right = _pill(d, m, 205, f"GAMEWEEK {r.gameweek}", 30, LABEL,
                  brand.rgb("primary"), brand.rgb("background"))
    LABEL.draw(d, (right + 22, 205), _subtitle(r), 28, brand.rgb("muted"))
    name, size = fit(r.league_name, DISPLAY, w - 2 * m, 84, 48)
    DISPLAY.draw(d, (m, 318), name, size, brand.rgb("text"))

    slots = award_slots(r)
    top, block_h, gap = 372, 196, 16
    if slots:
        for i, slot in enumerate(slots):
            y = top + i * (block_h + gap)
            _draw_block(img, (m, y, w - m, y + block_h), slot, STORY_BLOCK, brand)
    else:
        _empty(d, w, 960, 72, brand)

    _footer(d, w, 1700, 1762, 1806, (34, 26, 20), brand)
    return img


def _render_square(r: Report, brand: Brand) -> Image.Image:
    w, h = SIZES["square"]
    img = _background((w, h), brand).copy()
    d = ImageDraw.Draw(img, "RGBA")
    m = 48

    right = _pill(d, m, 82, f"GAMEWEEK {r.gameweek}", 22, LABEL,
                  brand.rgb("primary"), brand.rgb("background"))
    LABEL.draw(d, (right + 16, 82), _subtitle(r), 21, brand.rgb("muted"))
    name, size = fit(r.league_name, DISPLAY, w - 2 * m, 60, 36)
    DISPLAY.draw(d, (m, 160), name, size, brand.rgb("text"))

    slots = award_slots(r)
    top, gap = 192, 16
    tile_w = (w - 2 * m - gap) // 2
    tile_h = 214
    if slots:
        for i, slot in enumerate(slots):
            col, row = i % 2, i // 2
            x = m + col * (tile_w + gap)
            y = top + row * (tile_h + gap)
            _draw_block(img, (x, y, x + tile_w, y + tile_h), slot, SQUARE_BLOCK, brand)
    else:
        _empty(d, w, 560, 56, brand)

    _footer(d, w, 952, 1004, 1040, (26, 20, 16), brand)
    return img


def render_card(report: Report, fmt: CardFormat = "story", brand: Brand | None = None) -> bytes:
    if fmt not in SIZES:
        raise ValueError(f"Unknown card format: {fmt!r}")
    brand = brand or Brand.from_env()
    img = _render_story(report, brand) if fmt == "story" else _render_square(report, brand)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=False, compress_level=6)
    return buf.getvalue()
