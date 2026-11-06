# Mini-League Report Generator

A free tool that turns a Fantasy Premier League classic mini-league into a gameweek
report: winner, wooden spoon, best and worst captain, bench regret, biggest hit, rank
movers, differential hero, chips played and template ownership.

> Not affiliated with the Premier League or Fantasy Premier League.

## Layout

```
app/
  config.py       settings from env vars
  fpl_client.py   async FPL API client: TTL cache, request coalescing, retries, concurrency cap
  report.py       pure report engine (no I/O): FPL JSON in, Report out
  models.py       report dataclasses
  service.py      fetches FPL data for a report, then calls report.py
  main.py         FastAPI app
  card.py         renders a Report to a story/square PNG (Pillow)
  text.py         font fallback per character, fit/shrink/ellipsis
  branding.py     card colours, site name, handle, URL
  assets/fonts/   bundled OFL fonts (see "Fonts" below)
web/              Next.js frontend (see web/README.md)
scripts/
  check_live.py      one-off, hand-run check of live FPL response shapes
  fake_server.py     runs the API against offline fixture data (frontend dev + e2e tests)
  render_samples.py  writes sample cards to samples/ from offline fixtures
  build_fonts.py     regenerates app/assets/fonts from Google Fonts sources
samples/          example cards, including edge cases (long, emoji, RTL, CJK names)
tests/            fully offline (FakeFPL + httpx.MockTransport)
```

## Run locally

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
pytest
uvicorn app.main:app --reload
# http://localhost:8000/api/leagues/<league_id>/report?gw=<gw>
```

Frontend: see [web/README.md](web/README.md). Quick start:
`python -m scripts.fake_server` in one terminal, `cd web && npm install && npm run dev` in another,
then open http://localhost:3000/r/424242.

Check the live API shapes (makes a handful of real requests, run it by hand):

```bash
python -m scripts.check_live <league_id> [gw]
```

## API

`GET /api/leagues/{league_id}/report?gw=N`, where `gw` is optional and defaults to
the latest started gameweek.

| Status | `error`                | When |
|--------|------------------------|------|
| 200    |                        | report JSON (see `app/models.py`) plus `max_entries` and `disclaimer` |
| 404    | `league_not_found`     | no classic league with that ID |
| 409    | `gameweek_not_started` | GW in the future, or pre-season |
| 422    | `invalid_gameweek`     | GW outside 1–38 |
| 503    | `fpl_unavailable`      | FPL down or updating (`Retry-After: 120`) |

`GET /api/leagues/{league_id}/card.png?gw=N&format=story|square&download=true`

- `story` is 1080×1920 (default), `square` is 1080×1080
- `download=true` sends `Content-Disposition: attachment`
- rendered cards are cached in memory for `TTL_CARD` seconds, keyed by (league, gw, format)
- errors are the same JSON as the report endpoint

Leagues larger than `MAX_ENTRIES` are analysed for the top `MAX_ENTRIES` managers only,
with `truncated: true` and `total_managers: null`. FPL doesn't expose a league's size,
and we don't page through huge leagues just to count them.

## Award rules

| Award | Rule |
|---|---|
| GW winner / wooden spoon | GW points minus transfer hits |
| Best / worst captain | captain points ×2 (×3 Triple Captain); vice-captain takes over if the captain played 0 minutes; 0 if neither played |
| Bench regret | most `points_on_bench` (0 when Bench Boost is active) |
| Biggest hit | largest transfer cost; omitted if nobody took a hit |
| Rank climber / faller | biggest move in league rank, **latest GW only** (FPL only exposes `last_rank` for the latest GW) |
| Differential hero | best return (incl. multiplier, auto-subs applied) from a player owned by ≤20% of analysed managers (at least 1) |
| Chips played | each manager's active chip |
| Template | 10 most-owned players across analysed managers' 15-man squads |

Ties go to the manager higher in the league table.

## Environment variables

| Var | Default | Purpose |
|---|---|---|
| `MAX_ENTRIES` | `50` | free-tier cap on managers analysed per league |
| `FPL_CONCURRENCY` | `5` | max concurrent requests to FPL |
| `FPL_MAX_RETRIES` | `3` | retries on 429/5xx/network errors |
| `TTL_BOOTSTRAP` | `3600` | cache seconds for player/GW metadata |
| `TTL_DEFAULT` | `300` | cache seconds for everything else |
| `FPL_BASE_URL` | `https://fantasy.premierleague.com/api` | upstream base URL |
| `TTL_CARD` | `300` | cache seconds for rendered cards |
| `BRAND_SITE_NAME` | `Mini-League Report` | card watermark |
| `BRAND_HANDLE` | `@your_handle` | card watermark |
| `BRAND_SITE_URL` | `yoursite.com` | card call to action |
| `BRAND_PRIMARY` | `#FF5A36` | card primary colour (GW pill, "bad" awards) |
| `BRAND_ACCENT` | `#FFC83D` | card accent colour ("good" awards, URL) |

## Fonts

All bundled fonts are under the SIL Open Font License (licences in `app/assets/fonts/`):
Space Grotesk (headings), Inter (body, Latin/Greek/Cyrillic), Noto Sans Arabic, Hebrew,
Devanagari and Thai, Noto Emoji (monochrome), and Noto Sans SC/KR **subset** to common
characters (GB2312 level 1, JIS level 1 kanji, kana, KS X 1001 Hangul) to keep the fonts
at about 6 MB in total.

Names are drawn character by character with the first font that has a glyph. Stylised
Unicode ("𝓕𝓪𝓷𝓬𝔂") is folded to plain letters. Characters no font covers (e.g. Georgian,
rare CJK) are dropped rather than shown as boxes, and if nothing readable is left, the card
shows the manager's name (or "Team <id>") instead. Long names shrink, then get an ellipsis.

Arabic and Indic shaping needs Pillow's libraqm layout engine (bundled in the Pillow
wheels; on slim Docker images also install `libfribidi0`).

## Being polite to FPL

Responses are cached, identical in-flight requests are merged, concurrency is capped, and
retries back off exponentially. Nothing polls. A report costs at most
1 + ⌈MAX_ENTRIES/50⌉ + 1 + MAX_ENTRIES requests on a cold cache, and none on a warm one.
