"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { parseLeagueInput } from "@/lib/league-input";

export function LeagueForm() {
  const router = useRouter();
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const parsed = parseLeagueInput(value);
    if (!parsed.ok) {
      setError(parsed.error);
      return;
    }
    setError(null);
    startTransition(() => router.push(`/r/${parsed.leagueId}`));
  }

  return (
    <form onSubmit={submit} noValidate className="w-full">
      <label htmlFor="league" className="mb-2 block text-sm font-semibold text-muted">
        League ID or league link
      </label>
      <div className="flex flex-col gap-3 sm:flex-row">
        <input
          id="league"
          name="league"
          inputMode="url"
          autoComplete="off"
          autoCapitalize="off"
          spellCheck={false}
          placeholder="e.g. 123456 or fantasy.premierleague.com/leagues/…"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? "league-error" : undefined}
          className="min-h-14 w-full rounded-2xl border border-white/10 bg-surface px-4 text-base text-text placeholder:text-muted/70 focus:border-accent focus:outline-none"
        />
        <button
          type="submit"
          disabled={pending}
          className="min-h-14 shrink-0 rounded-2xl bg-primary px-6 font-display text-lg text-bg transition active:scale-[0.98] disabled:opacity-70"
        >
          {pending ? "Loading…" : "Get report"}
        </button>
      </div>
      <p id="league-error" role="alert" className="mt-2 min-h-5 text-sm text-primary">
        {error}
      </p>
    </form>
  );
}
