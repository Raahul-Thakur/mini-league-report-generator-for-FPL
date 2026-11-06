import Link from "next/link";

export default function NotFound() {
  return (
    <div className="mt-16 text-center">
      <h1 className="font-display text-3xl">Page not found</h1>
      <p className="mt-2 text-muted">That page doesn&apos;t exist.</p>
      <Link href="/" className="mt-6 inline-block rounded-2xl bg-primary px-5 py-3 font-semibold text-bg">
        Get a league report
      </Link>
    </div>
  );
}
