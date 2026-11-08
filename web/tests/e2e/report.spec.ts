import { expect, test, type Page } from "@playwright/test";

const LEAGUE = 424242; // fixture league, latest GW 10
const BIG = 500500; // 100-manager fixture league

/** Record Plausible events without loading Plausible. */
async function stubAnalytics(page: Page) {
  await page.addInitScript(() => {
    (window as unknown as { __events: unknown[] }).__events = [];
    window.plausible = (event: string, opts?: unknown) =>
      (window as unknown as { __events: unknown[] }).__events.push({ event, opts });
  });
}
const events = (page: Page) =>
  page.evaluate(() => (window as unknown as { __events: { event: string; opts?: { props?: Record<string, unknown> } }[] }).__events);

async function noHorizontalScroll(page: Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
}

test("paste an FPL league URL and get the latest report", async ({ page }) => {
  await stubAnalytics(page);
  await page.goto("/");
  await noHorizontalScroll(page);
  await page.getByLabel("League ID or league link").fill(
    `https://fantasy.premierleague.com/leagues/${LEAGUE}/standings/c`,
  );
  await page.getByRole("button", { name: "Get report" }).click();
  await page.waitForURL(`**/r/${LEAGUE}/10`);

  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Office Legends 🏆");
  const awards = page.getByRole("region", { name: "Awards" });
  await expect(awards.getByText("Triple Trouble").first()).toBeVisible();
  await expect(awards.getByText("Biggest climber")).toBeVisible();

  const card = page.getByRole("img", { name: /Story card for Office Legends/ });
  await expect(card).toBeVisible();
  await expect.poll(() => card.evaluate((i: HTMLImageElement) => i.naturalWidth)).toBe(1080);
  await expect(page.getByText("Drawing your card…")).toBeHidden();
  await noHorizontalScroll(page);

  await expect.poll(() => events(page)).toContainEqual({
    event: "report_generated",
    opts: { props: { league_id: LEAGUE, gameweek: 10, managers: 6 } },
  });
});

test("card preview overlay clears even if the image loads before hydration", async ({ page }) => {
  // Slow JS (as on a cheap phone in an in-app browser) so the server-rendered <img>
  // finishes loading before React attaches onLoad.
  await page.route("**/_next/static/chunks/**", async (route) => {
    await new Promise((r) => setTimeout(r, 1500));
    await route.continue();
  });
  await page.goto(`/r/${LEAGUE}/10`);
  const card = page.getByRole("img", { name: /Story card/ });
  await expect.poll(() => card.evaluate((i: HTMLImageElement) => i.naturalWidth)).toBe(1080);
  await expect(page.getByText("Drawing your card…")).toBeHidden({ timeout: 10_000 });
});

test("helper and validation on the landing page", async ({ page }) => {
  await page.goto("/");
  await page.getByText("Where do I find my league ID?").click();
  await expect(page.getByText(/Leagues & Cups/)).toBeVisible();

  const input = page.getByLabel("League ID or league link");
  await input.fill("https://fantasy.premierleague.com/leagues/auto-join/abc123");
  await page.getByRole("button", { name: "Get report" }).click();
  await expect(page.locator("#league-error")).toContainText("invite link");
  await expect(page).toHaveURL(/\/$/);

  await input.fill("not a league");
  await page.getByRole("button", { name: "Get report" }).click();
  await expect(page.locator("#league-error")).toContainText("couldn't find a league ID");
});

test("gameweek selector switches gameweeks", async ({ page }) => {
  await page.goto(`/r/${LEAGUE}/10`);
  await expect(page.getByRole("link", { name: "Next gameweek" })).toHaveAttribute("aria-disabled", "true");
  await page.getByRole("combobox", { name: "Gameweek" }).selectOption("9");
  await page.waitForURL(`**/r/${LEAGUE}/9`);
  await expect(page.getByText("GAMEWEEK 9")).toBeVisible();
  // Rank movers only exist for the latest gameweek
  await expect(page.getByRole("region", { name: "Awards" }).getByText("Biggest climber")).toHaveCount(0);
  await page.getByRole("link", { name: "Next gameweek" }).click();
  await page.waitForURL(`**/r/${LEAGUE}/10`);
});

test("share card: switch format, download and copy link", async ({ page, context }, info) => {
  test.skip(info.project.name !== "desktop", "downloads use the share sheet on touch devices");
  await stubAnalytics(page);
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await page.goto(`/r/${LEAGUE}/10`);

  await page.getByRole("tab", { name: "Post 1:1" }).click();
  const square = page.getByRole("img", { name: /Square card/ });
  await expect.poll(() => square.evaluate((i: HTMLImageElement) => i.naturalHeight)).toBe(1080);

  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: "Save story" }).click(),
  ]);
  expect(download.suggestedFilename()).toBe(`league-${LEAGUE}-gw10-story.png`);
  await expect.poll(() => events(page)).toContainEqual({
    event: "card_downloaded",
    opts: { props: { format: "story", method: "download" } },
  });

  await page.getByRole("button", { name: "Copy link" }).click();
  await expect(page.getByRole("button", { name: "Link copied ✓" })).toBeVisible();
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(page.url());
});

test("on phones the share card comes before the awards", async ({ page }, info) => {
  test.skip(info.project.name !== "instagram-mobile", "mobile layout only");
  await page.goto(`/r/${LEAGUE}/10`);
  const cardTop = (await page.getByRole("heading", { name: "Share card" }).boundingBox())!.y;
  const awardsTop = (await page.getByRole("region", { name: "Awards" }).boundingBox())!.y;
  expect(cardTop).toBeLessThan(awardsTop);
  await noHorizontalScroll(page);
});

test("big league shows the top-50 notice", async ({ page }) => {
  await page.goto(`/r/${BIG}`);
  await page.waitForURL(`**/r/${BIG}/10`);
  await expect(page.getByText("Big league!")).toBeVisible();
  await expect(page.getByText("Top 50 managers", { exact: true })).toBeVisible();
});

test("unknown league shows a helpful error", async ({ page }) => {
  await page.goto("/r/1/10");
  await expect(page.getByRole("heading", { name: "We couldn't find that league" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Try another league" })).toBeVisible();
});

test("future gameweek offers a link to the latest", async ({ page }) => {
  await page.goto(`/r/${LEAGUE}/20`);
  await expect(page.getByRole("heading", { name: "That gameweek hasn't started" })).toBeVisible();
  await page.getByRole("link", { name: "Latest gameweek" }).click();
  await page.waitForURL(`**/r/${LEAGUE}/10`);
});

test("malformed report links", async ({ page }) => {
  await page.goto("/r/abc/1");
  await expect(page.getByRole("heading", { name: "That link doesn't look right" })).toBeVisible();
  await page.goto(`/r/${LEAGUE}/99`);
  await expect(page.getByRole("heading", { name: "That link doesn't look right" })).toBeVisible();
});

test("link previews get the square card as og:image", async ({ request }) => {
  const html = await (
    await request.get(`/r/${LEAGUE}/10`, { headers: { "User-Agent": "WhatsApp/2.23.20.0 A" } })
  ).text();
  const head = html.split("</head>")[0];
  expect(head).toContain('property="og:title" content="Office Legends 🏆: GW10 awards"');
  const image = head.match(/property="og:image" content="([^"]+)"/)?.[1].replace(/&amp;/g, "&");
  expect(image).toMatch(new RegExp(`^https?://.+/api/leagues/${LEAGUE}/card\\.png\\?gw=10&format=square$`));
  const img = await request.get(new URL(image!).pathname + new URL(image!).search);
  expect(img.headers()["content-type"]).toBe("image/png");
});

test("footer disclaimer is on every page", async ({ page }) => {
  for (const path of ["/", `/r/${LEAGUE}/10`, "/r/1/10"]) {
    await page.goto(path);
    await expect(
      page.getByRole("contentinfo").getByText("Not affiliated with the Premier League or Fantasy Premier League."),
    ).toBeVisible();
  }
});

test("API is only reachable through the site", async ({ request }) => {
  // Direct call without the internal key is refused...
  const direct = await request.get(`http://127.0.0.1:8100/api/leagues/${LEAGUE}/report`);
  expect(direct.status()).toBe(403);
  // ...while the site's proxy adds it.
  const proxied = await request.get(`/api/leagues/${LEAGUE}/report?gw=10`);
  expect(proxied.status()).toBe(200);
  expect((await proxied.json()).league_name).toBe("Office Legends 🏆");
});

test("proxy only forwards the public endpoints", async ({ request }) => {
  expect((await request.get(`/api/leagues/${LEAGUE}/secret`)).status()).toBe(404);
  expect((await request.get(`/api/leagues/abc/report`)).status()).toBe(404);
  const missing = await request.get(`/api/leagues/1/report`);
  expect(missing.status()).toBe(404);
  expect((await missing.json()).error).toBe("league_not_found");
  expect(missing.headers()["cache-control"]).toBe("no-store");
  const card = await request.get(`/api/leagues/${LEAGUE}/card.png?gw=10&format=square&download=true`);
  expect(card.headers()["content-type"]).toBe("image/png");
  expect(card.headers()["content-disposition"]).toMatch(/^attachment;/);
});
