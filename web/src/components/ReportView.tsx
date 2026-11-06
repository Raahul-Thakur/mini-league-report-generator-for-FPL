import Link from "next/link";
import { awardRows } from "@/lib/awards";
import type { Report } from "@/lib/types";
import { CardPanel } from "./CardPanel";
import { GameweekPicker } from "./GameweekPicker";
import { TrackReport } from "./TrackReport";

export function ReportView({ report: r }: { report: Report }) {
  const rows = awardRows(r);
  const latest = r.latest_gameweek ?? r.gameweek;

  return (
    <article className="pt-6">
      <TrackReport leagueId={r.league_id} gameweek={r.gameweek} managers={r.managers_analysed} />

      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <p className="inline-block rounded-full bg-primary px-3 py-1 text-xs font-bold tracking-wide text-bg">
            GAMEWEEK {r.gameweek}
          </p>
          <h1 className="mt-2 break-words font-display text-3xl leading-tight sm:text-4xl">{r.league_name}</h1>
          <p className="mt-1 text-sm text-muted">
            {r.truncated
              ? `Top ${r.managers_analysed} managers`
              : `${r.managers_analysed} manager${r.managers_analysed === 1 ? "" : "s"}`}
          </p>
        </div>
        <GameweekPicker leagueId={r.league_id} gameweek={r.gameweek} latest={latest} />
      </header>

      {r.truncated && (
        <p role="status" className="mt-4 rounded-2xl bg-accent/10 p-3 text-sm text-accent ring-1 ring-accent/30">
          <b>Big league!</b> Free reports cover the top {r.max_entries} managers by league rank, so
          awards are for them only.
        </p>
      )}

      {rows.length === 0 ? (
        <p className="mt-8 rounded-3xl bg-surface/70 p-6 text-center text-muted">
          No results yet for this gameweek. Check back once games are underway.
        </p>
      ) : (
        <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_22rem]">
          {/* First on phones (sharing is the point), sidebar on desktop */}
          <div className="lg:col-start-2 lg:row-span-2 lg:row-start-1">
            <div className="lg:sticky lg:top-4">
              <CardPanel leagueId={r.league_id} gameweek={r.gameweek} leagueName={r.league_name} />
            </div>
          </div>

          <section aria-labelledby="awards-heading" className="lg:col-start-1 lg:row-start-1">
            <h2 id="awards-heading" className="sr-only">Awards</h2>
            <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
              {rows.map((a) => (
                <li
                  key={a.key}
                  className={`relative overflow-hidden rounded-2xl bg-surface p-4 pl-5 ring-1 ring-white/5 before:absolute before:inset-y-0 before:left-0 before:w-1.5 ${
                    a.tone === "good" ? "before:bg-accent" : "before:bg-primary"
                  }`}
                >
                  <p className={`text-xs font-bold tracking-wide uppercase ${a.tone === "good" ? "text-accent" : "text-primary"}`}>
                    <span aria-hidden>{a.icon}</span> {a.label}
                  </p>
                  <div className="mt-1 flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate font-display text-xl">{a.team}</p>
                      <p className="truncate text-sm text-muted">{a.manager}</p>
                      <p className="mt-1 text-sm text-muted">{a.detail}</p>
                    </div>
                    <p className="shrink-0 text-right">
                      <span className="block font-display text-3xl leading-none">{a.stat}</span>
                      <span className="text-xs font-semibold text-muted uppercase">{a.unit}</span>
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          </section>

          <div className="grid gap-6 sm:grid-cols-2 lg:col-start-1 lg:grid-cols-1">
            <section aria-labelledby="chips-heading" className="rounded-3xl bg-surface/70 p-4 ring-1 ring-white/5">
              <h2 id="chips-heading" className="font-display text-xl">Chips played</h2>
              {r.chips_played.length ? (
                <ul className="mt-3 space-y-2 text-sm">
                  {r.chips_played.map((c) => (
                    <li key={c.manager.entry_id} className="flex justify-between gap-3">
                      <span className="truncate">{c.manager.team_name}</span>
                      <span className="shrink-0 font-semibold text-accent">{c.chip_name}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-3 text-sm text-muted">Nobody played a chip this gameweek.</p>
              )}
            </section>

            <section aria-labelledby="template-heading" className="rounded-3xl bg-surface/70 p-4 ring-1 ring-white/5">
              <h2 id="template-heading" className="font-display text-xl">League template</h2>
              <p className="text-xs text-muted">Most-owned players in this league</p>
              <ul className="mt-3 space-y-2 text-sm">
                {r.template.map((t) => (
                  <li key={t.player_name}>
                    <div className="flex justify-between gap-3">
                      <span className="truncate">{t.player_name}</span>
                      <span className="shrink-0 tabular-nums text-muted">{Math.round(t.percent)}%</span>
                    </div>
                    <div className="mt-1 h-1.5 rounded-full bg-surface-2">
                      <div className="h-full rounded-full bg-primary" style={{ width: `${t.percent}%` }} />
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          </div>
        </div>
      )}

      <p className="mt-10 text-center">
        <Link href="/" className="font-semibold text-accent underline underline-offset-4">
          Get a report for another league →
        </Link>
      </p>
    </article>
  );
}
