"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

export function GameweekPicker({
  leagueId,
  gameweek,
  latest,
}: {
  leagueId: number;
  gameweek: number;
  latest: number;
}) {
  const router = useRouter();
  const gws = Array.from({ length: latest }, (_, i) => latest - i);
  const arrow =
    "grid size-11 place-items-center rounded-xl bg-surface text-xl aria-disabled:pointer-events-none aria-disabled:opacity-30";

  return (
    <nav aria-label="Gameweek navigation" className="flex items-center gap-2">
      <Link
        href={`/r/${leagueId}/${gameweek - 1}`}
        aria-label="Previous gameweek"
        aria-disabled={gameweek <= 1}
        tabIndex={gameweek <= 1 ? -1 : undefined}
        className={arrow}
      >
        ‹
      </Link>
      <label className="sr-only" htmlFor="gw-select">Gameweek</label>
      <select
        id="gw-select"
        value={gameweek}
        onChange={(e) => router.push(`/r/${leagueId}/${e.target.value}`)}
        className="h-11 rounded-xl bg-surface px-3 font-semibold"
      >
        {gws.map((gw) => (
          <option key={gw} value={gw}>
            GW {gw}{gw === latest ? " (latest)" : ""}
          </option>
        ))}
      </select>
      <Link
        href={`/r/${leagueId}/${gameweek + 1}`}
        aria-label="Next gameweek"
        aria-disabled={gameweek >= latest}
        tabIndex={gameweek >= latest ? -1 : undefined}
        className={arrow}
      >
        ›
      </Link>
    </nav>
  );
}
