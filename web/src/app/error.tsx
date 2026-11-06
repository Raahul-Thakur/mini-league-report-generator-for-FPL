"use client";

import Link from "next/link";

export default function Error({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div role="alert" className="mt-16 text-center">
      <h1 className="font-display text-3xl">Something went wrong</h1>
      <p className="mt-2 text-muted">Please try again. If it keeps happening, FPL may be updating.</p>
      <div className="mt-6 flex justify-center gap-2">
        <button type="button" onClick={reset} className="rounded-2xl bg-primary px-5 py-3 font-semibold text-bg">
          Try again
        </button>
        <Link href="/" className="rounded-2xl bg-surface-2 px-5 py-3 font-semibold">Home</Link>
      </div>
    </div>
  );
}
