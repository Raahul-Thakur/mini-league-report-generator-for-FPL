// How the website talks to the FastAPI backend (server-side only).
//
// Every call carries the shared INTERNAL_API_KEY and the visitor's IP, so the API can
// rate-limit per visitor even though all requests come from this site's servers.

export const API_URL = (process.env.API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");

/**
 * The visitor's IP. On Vercel, x-real-ip / x-forwarded-for are set by the platform
 * (client-supplied values are overwritten), so they can be trusted there. If you
 * self-host behind another proxy, make sure it sets them the same way.
 */
export function visitorIp(headers: Headers): string {
  const real = headers.get("x-real-ip")?.trim();
  if (real) return real;
  const forwarded = headers.get("x-forwarded-for")?.split(",")[0]?.trim();
  return forwarded || "127.0.0.1";
}

export function upstreamHeaders(incoming: Headers): Record<string, string> {
  const h: Record<string, string> = { "X-Client-IP": visitorIp(incoming) };
  const key = process.env.INTERNAL_API_KEY;
  if (key) h["X-Internal-Key"] = key;
  return h;
}
