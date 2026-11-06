"use client";

import { useState, useSyncExternalStore } from "react";
import { track } from "@/lib/analytics";

type Format = "story" | "square";

const noopSubscribe = () => () => {};

function cardSrc(leagueId: number, gw: number, format: Format, download = false) {
  return `/api/leagues/${leagueId}/card.png?gw=${gw}&format=${format}${download ? "&download=true" : ""}`;
}

/** Touch devices get the native share sheet (which has "Save image"); others download. */
function prefersShareSheet(): boolean {
  return (
    typeof navigator !== "undefined" &&
    typeof navigator.canShare === "function" &&
    window.matchMedia?.("(pointer: coarse)").matches
  );
}

export function CardPanel({ leagueId, gameweek, leagueName }: { leagueId: number; gameweek: number; leagueName: string }) {
  const [format, setFormat] = useState<Format>("story");
  const [loaded, setLoaded] = useState<Record<string, boolean>>({});
  const [failed, setFailed] = useState(false);
  const [busy, setBusy] = useState<Format | null>(null);
  const [copied, setCopied] = useState(false);
  // false during SSR, real value after hydration, without a hydration mismatch
  const canShareLink = useSyncExternalStore(
    noopSubscribe,
    () => typeof navigator.share === "function",
    () => false,
  );

  const src = cardSrc(leagueId, gameweek, format);
  const filename = (f: Format) => `league-${leagueId}-gw${gameweek}-${f}.png`;

  async function save(f: Format) {
    setBusy(f);
    try {
      if (prefersShareSheet()) {
        const blob = await (await fetch(cardSrc(leagueId, gameweek, f))).blob();
        const file = new File([blob], filename(f), { type: "image/png" });
        if (navigator.canShare({ files: [file] })) {
          try {
            await navigator.share({ files: [file], title: `${leagueName} · GW${gameweek}` });
            track("card_downloaded", { format: f, method: "share" });
          } catch (e) {
            if ((e as Error).name !== "AbortError") throw e;
          }
          return;
        }
      }
      const a = document.createElement("a");
      a.href = cardSrc(leagueId, gameweek, f, true);
      a.download = filename(f);
      document.body.appendChild(a);
      a.click();
      a.remove();
      track("card_downloaded", { format: f, method: "download" });
    } catch {
      // Fall back to opening the image; the user can long-press / right-click to save.
      window.location.href = cardSrc(leagueId, gameweek, f);
    } finally {
      setBusy(null);
    }
  }

  async function copyLink() {
    const url = window.location.href;
    try {
      await navigator.clipboard.writeText(url);
    } catch {
      window.prompt("Copy this link:", url);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  async function shareLink() {
    try {
      await navigator.share({ url: window.location.href, title: `${leagueName} · GW${gameweek} awards` });
    } catch {
      // cancelled
    }
  }

  const tab = (f: Format, label: string) => (
    <button
      type="button"
      role="tab"
      aria-selected={format === f}
      onClick={() => { setFormat(f); setFailed(false); }}
      className="flex-1 rounded-lg px-3 py-2 text-sm font-semibold text-muted aria-selected:bg-surface-2 aria-selected:text-text"
    >
      {label}
    </button>
  );

  const btn =
    "min-h-12 rounded-2xl px-4 font-semibold transition active:scale-[0.98] disabled:opacity-60";

  return (
    <section aria-labelledby="card-heading" className="rounded-3xl bg-surface/70 p-4 ring-1 ring-white/5">
      <h2 id="card-heading" className="mb-3 font-display text-xl">Share card</h2>

      <div role="tablist" aria-label="Card format" className="mb-3 flex gap-1 rounded-xl bg-bg/60 p-1">
        {tab("story", "Story 9:16")}
        {tab("square", "Post 1:1")}
      </div>

      <div
        className={`relative mx-auto overflow-hidden rounded-2xl bg-surface-2 ${
          format === "story" ? "aspect-[9/16] max-w-[min(100%,22rem)]" : "aspect-square max-w-[min(100%,28rem)]"
        }`}
      >
        {!loaded[src] && !failed && (
          <div className="absolute inset-0 grid animate-pulse place-items-center text-sm text-muted">
            Drawing your card…
          </div>
        )}
        {failed ? (
          <div className="absolute inset-0 grid place-items-center p-6 text-center text-sm text-muted">
            The card couldn&apos;t be drawn right now. Try again in a minute.
          </div>
        ) : (
          // eslint-disable-next-line @next/next/no-img-element -- served by our API, already sized
          <img
            key={src}
            src={src}
            alt={`${format === "story" ? "Story" : "Square"} card for ${leagueName}, gameweek ${gameweek}`}
            onLoad={() => setLoaded((l) => ({ ...l, [src]: true }))}
            onError={() => setFailed(true)}
            className="size-full object-contain"
          />
        )}
      </div>
      <p className="mt-2 text-center text-xs text-muted">Tip: you can also long-press the image to save it.</p>

      <div className="mt-4 grid grid-cols-2 gap-2">
        <button type="button" onClick={() => save("story")} disabled={busy !== null} className={`${btn} bg-primary text-bg`}>
          {busy === "story" ? "Preparing…" : "Save story"}
        </button>
        <button type="button" onClick={() => save("square")} disabled={busy !== null} className={`${btn} bg-accent text-bg`}>
          {busy === "square" ? "Preparing…" : "Save post"}
        </button>
        <button type="button" onClick={copyLink} className={`${btn} bg-surface-2 ${canShareLink ? "" : "col-span-2"}`}>
          {copied ? "Link copied ✓" : "Copy link"}
        </button>
        {canShareLink && (
          <button type="button" onClick={shareLink} className={`${btn} bg-surface-2`}>
            Share link
          </button>
        )}
      </div>
      <p aria-live="polite" className="sr-only">{copied ? "Link copied" : ""}</p>
    </section>
  );
}
