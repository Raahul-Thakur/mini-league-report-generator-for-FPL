"use client";

import { useRouter } from "next/navigation";
import { useTransition } from "react";

export function RetryButton() {
  const router = useRouter();
  const [pending, start] = useTransition();
  return (
    <button
      type="button"
      onClick={() => start(() => router.refresh())}
      disabled={pending}
      className="min-h-12 rounded-2xl bg-primary px-5 font-semibold text-bg disabled:opacity-60"
    >
      {pending ? "Retrying…" : "Try again"}
    </button>
  );
}
