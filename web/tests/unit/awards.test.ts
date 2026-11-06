import { describe, expect, it } from "vitest";
import { parseId } from "@/lib/api";
import { awardRows, ordinal, reportSummary } from "@/lib/awards";
import type { Report } from "@/lib/types";

const m = (id: number, team: string) => ({ entry_id: id, team_name: team, manager_name: `Mgr ${id}` });

const base: Report = {
  league_id: 1, league_name: "Test League", gameweek: 10, is_latest_gameweek: true,
  latest_gameweek: 10, managers_analysed: 3, total_managers: 3, truncated: false, max_entries: 50,
  winner: { manager: m(1, "Alpha"), points: 80 },
  wooden_spoon: { manager: m(2, "Beta"), points: 20 },
  best_captain: { manager: m(1, "Alpha"), player_name: "Haaland", points: 39, multiplier: 3, used_vice: false, triple_captain: true },
  worst_captain: { manager: m(2, "Beta"), player_name: "Saka", points: 16, multiplier: 2, used_vice: true, triple_captain: false },
  bench_regret: null,
  biggest_hit: { manager: m(3, "Gamma"), cost: 8, transfers: 3 },
  rank_climber: { manager: m(3, "Gamma"), previous_rank: 3, rank: 1, places: 2 },
  rank_faller: { manager: m(2, "Beta"), previous_rank: 2, rank: 3, places: -1 },
  differential_hero: { manager: m(3, "Gamma"), player_name: "Isak", points: 15, owned_by: 1 },
  chips_played: [], template: [], disclaimer: "",
};

describe("awardRows", () => {
  it("lists awards in order and skips missing ones", () => {
    expect(awardRows(base).map((a) => a.key)).toEqual([
      "winner", "spoon", "best_captain", "worst_captain", "climber", "faller", "hit", "differential",
    ]);
  });

  it("formats captain extras, rank moves and hits", () => {
    const rows = Object.fromEntries(awardRows(base).map((a) => [a.key, a]));
    expect(rows.best_captain.detail).toBe("Haaland (Triple Captain)");
    expect(rows.worst_captain.detail).toBe("Saka (vice stepped in)");
    expect(rows.climber).toMatchObject({ stat: "+2", unit: "places", detail: "3rd → 1st" });
    expect(rows.faller).toMatchObject({ stat: "−1", unit: "place" });
    expect(rows.hit).toMatchObject({ stat: "−8", detail: "3 transfers" });
    expect(rows.differential.detail).toBe("Isak (only owner)");
  });

  it("handles an empty report", () => {
    const empty = { ...base, winner: null, wooden_spoon: null, best_captain: null, worst_captain: null,
      biggest_hit: null, rank_climber: null, rank_faller: null, differential_hero: null };
    expect(awardRows(empty)).toEqual([]);
  });
});

describe("helpers", () => {
  it.each([[1, "1st"], [2, "2nd"], [3, "3rd"], [4, "4th"], [11, "11th"], [12, "12th"], [13, "13th"], [21, "21st"], [112, "112th"]])(
    "ordinal(%i) = %s", (n, s) => expect(ordinal(n)).toBe(s),
  );

  it("summarises for link previews", () => {
    expect(reportSummary(base)).toBe("GW10 in Test League · 🏆 Alpha (80) · 🥄 Beta (20) · 👑 Haaland (39)");
  });

  it("parses route ids strictly", () => {
    expect(parseId("10", 38)).toBe(10);
    expect(parseId("39", 38)).toBeNull();
    expect(parseId("0", 38)).toBeNull();
    expect(parseId("1e3", 38)).toBeNull();
    expect(parseId("abc", 38)).toBeNull();
  });
});
