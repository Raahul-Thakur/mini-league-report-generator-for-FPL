import Script from "next/script";

// Plausible, only when NEXT_PUBLIC_PLAUSIBLE_DOMAIN is set. Cookie-free, so no consent banner.
export function Analytics() {
  const domain = process.env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN;
  if (!domain) return null;
  const src = process.env.NEXT_PUBLIC_PLAUSIBLE_SRC || "https://plausible.io/js/script.js";
  return (
    <>
      <Script defer data-domain={domain} src={src} strategy="afterInteractive" />
      {/* Queue events fired before the script loads */}
      <Script id="plausible-queue" strategy="afterInteractive">
        {"window.plausible=window.plausible||function(){(window.plausible.q=window.plausible.q||[]).push(arguments)}"}
      </Script>
    </>
  );
}
