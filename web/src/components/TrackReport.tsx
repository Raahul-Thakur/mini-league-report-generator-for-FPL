"use client";

import { useEffect } from "react";
import { track } from "@/lib/analytics";

// Next keeps recently visited routes mounted (React <Activity>) and re-runs their effects
// when you navigate back, so remember what was already tracked in this tab.
const seen = new Set<string>();

/** Fires report_generated once per league/GW per page load. */
export function TrackReport({ leagueId, gameweek, managers }: { leagueId: number; gameweek: number; managers: number }) {
  useEffect(() => {
    const key = `${leagueId}:${gameweek}`;
    if (seen.has(key)) return;
    seen.add(key);
    track("report_generated", { league_id: leagueId, gameweek, managers });
  }, [leagueId, gameweek, managers]);
  return null;
}
