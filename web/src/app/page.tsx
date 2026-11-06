import { LeagueForm } from "@/components/LeagueForm";

export default function Home() {
  return (
    <div className="pt-8 sm:pt-14">
      <section>
        <p className="mb-3 inline-block rounded-full bg-primary/15 px-3 py-1 text-xs font-bold tracking-wide text-primary">
          FREE · NO SIGN-UP
        </p>
        <h1 className="font-display text-4xl leading-[1.05] tracking-tight sm:text-6xl">
          Your mini-league&apos;s gameweek, <span className="text-accent">wrapped.</span>
        </h1>
        <p className="mt-4 max-w-xl text-lg text-muted">
          Winner, wooden spoon, best and worst captain, bench regret and more, as a card made
          for your group chat and Instagram story.
        </p>
      </section>

      <section className="mt-8 rounded-3xl bg-surface/70 p-4 ring-1 ring-white/5 sm:p-6">
        <LeagueForm />
        <details className="group mt-2 rounded-2xl bg-bg/50 p-4 text-sm">
          <summary className="cursor-pointer list-none font-semibold text-text marker:hidden">
            <span className="mr-1 inline-block transition group-open:rotate-90">›</span>
            Where do I find my league ID?
          </summary>
          <ol className="mt-3 list-decimal space-y-2 pl-5 text-muted">
            <li>
              Open <strong className="text-text">fantasy.premierleague.com</strong> in your browser
              (the FPL app doesn&apos;t show the ID) and sign in.
            </li>
            <li>
              Go to <strong className="text-text">Leagues &amp; Cups</strong> and tap your league.
            </li>
            <li>
              Copy the page link. It looks like{" "}
              <code className="rounded bg-surface-2 px-1 text-text">…/leagues/<b>123456</b>/standings/c</code>.
              Paste the whole link, or just the number.
            </li>
          </ol>
          <p className="mt-3 text-muted">
            Classic leagues only. Free reports cover up to the top 50 managers.
          </p>
        </details>
      </section>

      <section className="mt-12 grid items-center gap-8 sm:grid-cols-2">
        <div>
          <h2 className="font-display text-2xl">What you get</h2>
          <ul className="mt-4 space-y-3 text-muted">
            <li>🏆 <b className="text-text">GW winner</b> and 🥄 <b className="text-text">wooden spoon</b>, after hits</li>
            <li>👑 <b className="text-text">Best</b> and 🙈 <b className="text-text">worst captain</b>, Triple Captain aware</li>
            <li>🪑 <b className="text-text">Bench regret</b>, 💸 <b className="text-text">biggest hit</b>, 📈 <b className="text-text">climbers</b></li>
            <li>🎯 <b className="text-text">Differential hero</b>, chips played and the league template</li>
            <li>📲 Story and post-sized cards to share</li>
          </ul>
        </div>
        {/* eslint-disable-next-line @next/next/no-img-element -- static example image */}
        <img
          src="/example-card.png"
          alt="Example report card for a sample league"
          width={1080}
          height={1080}
          loading="lazy"
          className="w-full rounded-3xl shadow-2xl shadow-black/50 ring-1 ring-white/10"
        />
      </section>
    </div>
  );
}
