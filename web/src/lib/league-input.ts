// Turn whatever the user pasted (an ID, an FPL standings URL, a URL without the scheme...)
// into a classic league ID, or a helpful error.

export type ParseResult =
  | { ok: true; leagueId: number }
  | { ok: false; error: string };

const MAX_ID = 2 ** 31;

function valid(n: number): boolean {
  return Number.isSafeInteger(n) && n > 0 && n <= MAX_ID;
}

export function parseLeagueInput(raw: string): ParseResult {
  const input = raw.trim();
  if (!input) return { ok: false, error: "Paste your league ID or league link." };

  if (/^\d+$/.test(input)) {
    const id = Number(input);
    return valid(id) ? { ok: true, leagueId: id } : { ok: false, error: "That ID looks too long." };
  }

  if (/auto-join/i.test(input)) {
    return {
      ok: false,
      error:
        "That's an invite link. Open your league's standings page instead and copy that link (it has /leagues/<number>/ in it).",
    };
  }

  // FPL URLs: /leagues/{id}/standings/c (classic) or /standings/h (head-to-head)
  const m = input.match(/leagues\/(\d+)(?:\/standings\/([ch]))?/i);
  if (m) {
    if (m[2]?.toLowerCase() === "h") {
      return { ok: false, error: "Head-to-head leagues aren't supported yet, only classic leagues." };
    }
    const id = Number(m[1]);
    if (valid(id)) return { ok: true, leagueId: id };
  }

  return {
    ok: false,
    error: "We couldn't find a league ID in that. It's the number in your league's URL.",
  };
}
