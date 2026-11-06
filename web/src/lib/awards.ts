// Turn a report into display-ready award rows. Kept free of React so it can be unit tested.
import type { Report } from "./types";

export interface AwardRow {
  key: string;
  icon: string;
  label: string;
  team: string;
  manager: string;
  detail: string;
  stat: string;
  unit: string;
  tone: "good" | "bad";
}

export function ordinal(n: number): string {
  const s = n % 100 >= 11 && n % 100 <= 13 ? "th" : ({ 1: "st", 2: "nd", 3: "rd" } as Record<number, string>)[n % 10] ?? "th";
  return `${n}${s}`;
}

const MINUS = "−";

export function awardRows(r: Report): AwardRow[] {
  const rows: AwardRow[] = [];
  const base = (m: { team_name: string; manager_name: string }) => ({
    team: m.team_name,
    manager: m.manager_name,
  });

  if (r.winner)
    rows.push({ key: "winner", icon: "🏆", label: "GW winner", ...base(r.winner.manager),
      detail: "Top score this gameweek", stat: String(r.winner.points), unit: "pts", tone: "good" });
  if (r.wooden_spoon)
    rows.push({ key: "spoon", icon: "🥄", label: "Wooden spoon", ...base(r.wooden_spoon.manager),
      detail: "Lowest score, after hits", stat: String(r.wooden_spoon.points), unit: "pts", tone: "bad" });
  for (const [cap, key, icon, label, tone] of [
    [r.best_captain, "best_captain", "👑", "Best captain", "good"],
    [r.worst_captain, "worst_captain", "🙈", "Worst captain", "bad"],
  ] as const) {
    if (!cap) continue;
    const extras = [cap.triple_captain && "Triple Captain", cap.used_vice && "vice stepped in"].filter(Boolean);
    rows.push({ key, icon, label, ...base(cap.manager),
      detail: `${cap.player_name}${extras.length ? ` (${extras.join(", ")})` : ""}`,
      stat: String(cap.points), unit: "pts", tone });
  }
  if (r.bench_regret)
    rows.push({ key: "bench", icon: "🪑", label: "Bench regret", ...base(r.bench_regret.manager),
      detail: "Points left on the bench", stat: String(r.bench_regret.points), unit: "pts", tone: "bad" });
  if (r.rank_climber) {
    const c = r.rank_climber;
    rows.push({ key: "climber", icon: "📈", label: "Biggest climber", ...base(c.manager),
      detail: `${ordinal(c.previous_rank)} → ${ordinal(c.rank)}`, stat: `+${c.places}`,
      unit: c.places === 1 ? "place" : "places", tone: "good" });
  }
  if (r.rank_faller) {
    const f = r.rank_faller;
    const n = Math.abs(f.places);
    rows.push({ key: "faller", icon: "📉", label: "Biggest faller", ...base(f.manager),
      detail: `${ordinal(f.previous_rank)} → ${ordinal(f.rank)}`, stat: `${MINUS}${n}`,
      unit: n === 1 ? "place" : "places", tone: "bad" });
  }
  if (r.biggest_hit) {
    const h = r.biggest_hit;
    rows.push({ key: "hit", icon: "💸", label: "Biggest hit", ...base(h.manager),
      detail: `${h.transfers} transfer${h.transfers === 1 ? "" : "s"}`, stat: `${MINUS}${h.cost}`,
      unit: "pts", tone: "bad" });
  }
  if (r.differential_hero) {
    const d = r.differential_hero;
    rows.push({ key: "differential", icon: "🎯", label: "Differential hero", ...base(d.manager),
      detail: `${d.player_name} (${d.owned_by === 1 ? "only owner" : `${d.owned_by} owners`})`,
      stat: String(d.points), unit: "pts", tone: "good" });
  }
  return rows;
}

export function reportSummary(r: Report): string {
  const parts = [`GW${r.gameweek} in ${r.league_name}`];
  if (r.winner) parts.push(`🏆 ${r.winner.manager.team_name} (${r.winner.points})`);
  if (r.wooden_spoon) parts.push(`🥄 ${r.wooden_spoon.manager.team_name} (${r.wooden_spoon.points})`);
  if (r.best_captain) parts.push(`👑 ${r.best_captain.player_name} (${r.best_captain.points})`);
  return parts.join(" · ");
}
