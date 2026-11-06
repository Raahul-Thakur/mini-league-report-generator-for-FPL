import type { Metadata } from "next";
import { ErrorState } from "@/components/ErrorState";
import { ReportView } from "@/components/ReportView";
import { cardUrl, getReport, parseId } from "@/lib/api";
import { reportSummary } from "@/lib/awards";

async function load(params: PageProps<"/r/[leagueId]/[gw]">["params"]) {
  const { leagueId: rawId, gw: rawGw } = await params;
  const leagueId = parseId(rawId, 2 ** 31);
  const gw = parseId(rawGw, 38);
  if (!leagueId || !gw) return { leagueId, gw, result: null };
  return { leagueId, gw, result: await getReport(leagueId, gw) };
}

export async function generateMetadata({ params }: PageProps<"/r/[leagueId]/[gw]">): Promise<Metadata> {
  const { leagueId, gw, result } = await load(params);
  if (!leagueId || !gw || !result?.ok) return { title: "League report", robots: { index: false } };
  const r = result.report;
  const title = `${r.league_name}: GW${r.gameweek} awards`;
  const description = reportSummary(r);
  const image = {
    url: cardUrl(leagueId, gw, "square"),
    width: 1080,
    height: 1080,
    alt: `Gameweek ${gw} awards card for ${r.league_name}`,
  };
  return {
    title,
    description,
    robots: { index: false }, // private-ish league pages; keep them out of search
    alternates: { canonical: `/r/${leagueId}/${gw}` },
    openGraph: { title, description, url: `/r/${leagueId}/${gw}`, images: [image] },
    twitter: { card: "summary_large_image", title, description, images: [image.url] },
  };
}

export default async function ReportPage({ params }: PageProps<"/r/[leagueId]/[gw]">) {
  const { leagueId, gw, result } = await load(params);
  if (!leagueId || !gw || !result) {
    return <ErrorState code="bad_link" message="Report links look like /r/123456/10 (league, then gameweek 1–38)." />;
  }
  if (!result.ok) return <ErrorState code={result.code} message={result.message} leagueId={leagueId} />;
  return <ReportView report={result.report} />;
}
