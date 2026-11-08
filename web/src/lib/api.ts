// Server-side access to the backend API. Never imported by client components.
import { headers } from "next/headers";
import { cache } from "react";
import type { ApiErrorCode, ReportResult } from "./types";
import { API_URL, upstreamHeaders } from "./upstream";

const FALLBACK_MESSAGES: Record<ApiErrorCode, string> = {
  league_not_found: "We couldn't find a classic league with that ID.",
  gameweek_not_started: "That gameweek hasn't started yet.",
  invalid_gameweek: "That isn't a valid gameweek.",
  fpl_unavailable: "The FPL API is busy or updating. Please try again in a few minutes.",
  rate_limited: "You're going a bit fast. Please wait a minute and try again.",
  api_unreachable: "Our server didn't respond. Please try again in a moment.",
  unknown: "Something went wrong building this report.",
};

function asCode(value: unknown): ApiErrorCode {
  return typeof value === "string" && value in FALLBACK_MESSAGES
    ? (value as ApiErrorCode)
    : "unknown";
}

// React's cache() dedupes the call between generateMetadata and the page in one request.
export const getReport = cache(async (leagueId: number, gw?: number): Promise<ReportResult> => {
  const url = `${API_URL}/api/leagues/${leagueId}/report${gw ? `?gw=${gw}` : ""}`;
  let res: Response;
  try {
    res = await fetch(url, {
      headers: upstreamHeaders(await headers()),
      cache: "no-store",
      signal: AbortSignal.timeout(60_000),
    });
  } catch {
    return { ok: false, code: "api_unreachable", message: FALLBACK_MESSAGES.api_unreachable };
  }
  if (res.ok) return { ok: true, report: await res.json() };

  let body: { error?: unknown; message?: unknown } = {};
  try {
    body = await res.json();
  } catch {
    // non-JSON error (e.g. a proxy page)
  }
  const code = res.status === 422 ? "invalid_gameweek" : asCode(body.error);
  const message =
    code !== "unknown" && code !== "invalid_gameweek" && typeof body.message === "string"
      ? body.message
      : FALLBACK_MESSAGES[code];
  return { ok: false, code, message };
});

export function cardUrl(leagueId: number, gw: number, format: "story" | "square", download = false) {
  return `/api/leagues/${leagueId}/card.png?gw=${gw}&format=${format}${download ? "&download=true" : ""}`;
}

export function parseId(value: string, max: number): number | null {
  if (!/^\d{1,10}$/.test(value)) return null;
  const n = Number(value);
  return n >= 1 && n <= max ? n : null;
}
