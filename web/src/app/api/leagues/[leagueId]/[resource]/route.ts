// Proxy for the two public API endpoints the browser needs:
//   /api/leagues/{id}/report      and      /api/leagues/{id}/card.png
// Adds the internal key and visitor IP; passes through status and caching headers.
import type { NextRequest } from "next/server";
import { API_URL, upstreamHeaders } from "@/lib/upstream";

const RESOURCES = new Set(["report", "card.png"]);
const ALLOWED_QUERY = ["gw", "format", "download"];
const PASS_HEADERS = ["content-type", "cache-control", "content-disposition", "retry-after"];

function json(status: number, error: string, message: string) {
  return Response.json({ error, message }, { status, headers: { "Cache-Control": "no-store" } });
}

export async function GET(
  request: NextRequest,
  { params }: RouteContext<"/api/leagues/[leagueId]/[resource]">,
) {
  const { leagueId, resource } = await params;
  if (!/^\d{1,10}$/.test(leagueId) || !RESOURCES.has(resource)) {
    return json(404, "not_found", "Not found.");
  }

  const query = new URLSearchParams();
  for (const k of ALLOWED_QUERY) {
    const v = request.nextUrl.searchParams.get(k);
    if (v !== null) query.set(k, v);
  }
  const qs = query.size ? `?${query}` : "";

  let upstream: Response;
  try {
    upstream = await fetch(`${API_URL}/api/leagues/${leagueId}/${resource}${qs}`, {
      headers: upstreamHeaders(request.headers),
      cache: "no-store",
      signal: AbortSignal.timeout(60_000),
    });
  } catch {
    return json(502, "api_unreachable", "Our server didn't respond. Please try again in a moment.");
  }

  const headers = new Headers();
  for (const h of PASS_HEADERS) {
    const v = upstream.headers.get(h);
    if (v) headers.set(h, v);
  }
  if (!upstream.ok) headers.set("Cache-Control", "no-store"); // never CDN-cache errors
  return new Response(upstream.body, { status: upstream.status, headers });
}
