export function ReportSkeleton() {
  const block = "animate-pulse rounded-2xl bg-surface";
  return (
    <div aria-busy="true" aria-live="polite" className="pt-6">
      <p className="sr-only">Loading report</p>
      <div className={`${block} h-6 w-28`} />
      <div className={`${block} mt-3 h-10 w-3/4`} />
      <p className="mt-4 text-sm text-muted">
        Crunching your league… bigger leagues can take a few seconds.
      </p>
      <div className="mt-6 grid gap-3 sm:grid-cols-2">
        {Array.from({ length: 6 }, (_, i) => (
          <div key={i} className={`${block} h-28`} />
        ))}
      </div>
    </div>
  );
}
