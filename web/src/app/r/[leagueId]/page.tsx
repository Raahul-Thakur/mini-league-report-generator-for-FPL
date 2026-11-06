import { redirect } from "next/navigation";
import { ErrorState } from "@/components/ErrorState";
import { getReport, parseId } from "@/lib/api";

// /r/{leagueId} -> /r/{leagueId}/{latest gameweek}
export default async function LatestReport({ params }: PageProps<"/r/[leagueId]">) {
  const { leagueId: raw } = await params;
  const leagueId = parseId(raw, 2 ** 31);
  if (!leagueId) {
    return <ErrorState code="bad_link" message="League IDs are numbers, like /r/123456." />;
  }
  const result = await getReport(leagueId);
  if (!result.ok) return <ErrorState code={result.code} message={result.message} leagueId={leagueId} />;
  redirect(`/r/${leagueId}/${result.report.gameweek}`);
}
