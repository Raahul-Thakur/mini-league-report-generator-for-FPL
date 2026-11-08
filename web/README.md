# Web: Mini-League Report frontend

Next.js 16 (App Router, TypeScript, Tailwind v4, Cache Components). Mobile-first, since most
visitors arrive from Instagram's in-app browser.

## Pages

| Route | What |
|---|---|
| `/` | Paste a league ID or FPL league URL, plus a "where do I find my league ID?" helper |
| `/r/{leagueId}` | Redirects to the latest gameweek |
| `/r/{leagueId}/{gw}` | Awards, share card preview, save story/post, copy/share link, GW selector. `og:image` is the square card |

`/api/leagues/{id}/report` and `/api/leagues/{id}/card.png` on this site are a route handler
(`src/app/api/leagues/[leagueId]/[resource]/route.ts`) that forwards to the FastAPI backend
(`API_URL`), adding the shared `INTERNAL_API_KEY` and the visitor's IP so the API can rate-limit
per visitor. The browser only ever talks to this site: no CORS, and Open Graph image URLs live
on your domain. `vercel.json` pins server functions to Frankfurt (`fra1`) to sit next to the
API; change it if you host the API elsewhere.

## Develop

```bash
# terminal 1, from the repo root: the API with offline fixture data
python -m scripts.fake_server          # league 424242 (GW 1-10), 500500 = 100-manager league

# terminal 2
cd web
cp .env.example .env.local
npm install
npm run dev                            # http://localhost:3000/r/424242
```

Point `API_URL` at `uvicorn app.main:app` instead to use real FPL data.

## Test

```bash
npm run typecheck
npm run lint
npm test                               # unit tests (Vitest)
PYTHON=$(cd .. && pwd)/.venv/bin/python npm run test:e2e
```

E2E tests (Playwright) start the fake API and a fresh production build themselves, and run in
a desktop and an Instagram-in-app-browser mobile profile. First time locally:
`npx playwright install chromium`. To iterate faster against servers you already started on
ports 8100/3100, set `PW_REUSE=1`. It's off by default because a stale server silently tests
old code.

## Deploy

See the root README's **Deploy** section. On Vercel, set **Root Directory** to `web`.

## Analytics

Set `NEXT_PUBLIC_PLAUSIBLE_DOMAIN` to enable Plausible (cookie-free, no consent banner).
Custom events:

| Event | Props | When |
|---|---|---|
| `report_generated` | `league_id`, `gameweek`, `managers` | a report page is viewed (once per league/GW per tab) |
| `card_downloaded` | `format` (`story`/`square`), `method` (`share`/`download`) | a card is saved or shared |

In Plausible, add both as custom-event goals to see them on the dashboard.

## Saving cards on phones

Instagram's in-app browser often ignores download links, so on touch devices "Save story/post"
opens the native share sheet with the image attached (which has "Save Image"). Desktop gets a
normal download. The preview can also be long-pressed.
