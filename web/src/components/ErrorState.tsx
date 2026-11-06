import Link from "next/link";
import type { ApiErrorCode } from "@/lib/types";
import { RetryButton } from "./RetryButton";

const TITLES: Record<ApiErrorCode | "bad_link", string> = {
  league_not_found: "We couldn't find that league",
  gameweek_not_started: "That gameweek hasn't started",
  invalid_gameweek: "That gameweek doesn't exist",
  fpl_unavailable: "FPL is busy right now",
  api_unreachable: "We're having trouble",
  unknown: "Something went wrong",
  bad_link: "That link doesn't look right",
};

const RETRYABLE = new Set(["fpl_unavailable", "api_unreachable", "unknown"]);

export function ErrorState({
  code,
  message,
  leagueId,
}: {
  code: ApiErrorCode | "bad_link";
  message: string;
  leagueId?: number;
}) {
  return (
    <div role="alert" className="mt-10 rounded-3xl bg-surface/70 p-6 text-center ring-1 ring-white/5">
      <p className="text-4xl" aria-hidden>
        {code === "fpl_unavailable" ? "⏳" : "🤔"}
      </p>
      <h1 className="mt-3 font-display text-2xl">{TITLES[code]}</h1>
      <p className="mx-auto mt-2 max-w-md text-muted">{message}</p>
      {code === "league_not_found" && (
        <p className="mx-auto mt-2 max-w-md text-sm text-muted">
          Check the number, and make sure it&apos;s a classic league (not head-to-head).
        </p>
      )}
      <div className="mt-6 flex flex-wrap justify-center gap-2">
        {RETRYABLE.has(code) && <RetryButton />}
        {code === "gameweek_not_started" && leagueId && (
          <Link href={`/r/${leagueId}`} className="min-h-12 rounded-2xl bg-primary px-5 py-3 font-semibold text-bg">
            Latest gameweek
          </Link>
        )}
        <Link href="/" className="min-h-12 rounded-2xl bg-surface-2 px-5 py-3 font-semibold">
          Try another league
        </Link>
      </div>
    </div>
  );
}
