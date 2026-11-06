import { describe, expect, it } from "vitest";
import { parseLeagueInput } from "@/lib/league-input";

const ok = (leagueId: number) => ({ ok: true, leagueId });

describe("parseLeagueInput", () => {
  it.each([
    ["123456", 123456],
    ["  987654  ", 987654],
    ["https://fantasy.premierleague.com/leagues/123456/standings/c", 123456],
    ["fantasy.premierleague.com/leagues/314/standings/c?page_standings=2", 314],
    ["http://fantasy.premierleague.com/leagues/42/standings/c/", 42],
    ["https://fantasy.premierleague.com/leagues/777", 777],
    ["Check out our league! https://fantasy.premierleague.com/leagues/1234/standings/c", 1234],
  ])("accepts %s", (input, id) => {
    expect(parseLeagueInput(input)).toEqual(ok(id));
  });

  it("rejects empty input", () => {
    expect(parseLeagueInput("   ").ok).toBe(false);
  });

  it("explains invite links", () => {
    const r = parseLeagueInput("https://fantasy.premierleague.com/leagues/auto-join/ab12cd");
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.error).toMatch(/invite link/);
  });

  it("rejects head-to-head leagues", () => {
    const r = parseLeagueInput("https://fantasy.premierleague.com/leagues/555/standings/h");
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.error).toMatch(/Head-to-head/);
  });

  it.each(["0", "99999999999", "hello", "https://example.com/team/123", "-5", "12.5"])(
    "rejects %s",
    (input) => {
      expect(parseLeagueInput(input).ok).toBe(false);
    },
  );
});
