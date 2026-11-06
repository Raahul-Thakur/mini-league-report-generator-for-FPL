import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import Link from "next/link";
import type { CSSProperties } from "react";
import { Analytics } from "@/components/Analytics";
import { instagramUrl, site } from "@/lib/site";
import "./globals.css";

const spaceGrotesk = localFont({
  src: "./fonts/SpaceGrotesk-Bold.ttf",
  weight: "700",
  variable: "--font-space-grotesk",
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL(site.url),
  title: { default: `${site.name}: your FPL mini-league, wrapped`, template: `%s · ${site.name}` },
  description:
    "Free gameweek awards for your Fantasy Premier League mini-league: winner, wooden spoon, best and worst captain, bench regret and more, as shareable story cards.",
  openGraph: { siteName: site.name, type: "website" },
};

export const viewport: Viewport = {
  themeColor: "#0e1116",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  const brand = { "--primary": site.primary, "--accent": site.accent } as CSSProperties;
  return (
    <html lang="en" className={`${spaceGrotesk.variable} h-full antialiased`} style={brand}>
      <body className="min-h-full flex flex-col font-sans">
        <header className="mx-auto w-full max-w-3xl px-4 pt-4 sm:pt-6">
          <Link href="/" className="font-display text-lg tracking-tight">
            <span className="text-primary">●</span> {site.name}
          </Link>
        </header>
        <main className="mx-auto w-full max-w-3xl flex-1 px-4 pb-12">{children}</main>
        <footer className="mx-auto w-full max-w-3xl px-4 pb-8 text-center text-xs text-muted">
          <p>
            Made by{" "}
            <a className="underline underline-offset-2" href={instagramUrl(site.handle)} rel="noopener">
              {site.handle}
            </a>{" "}
            · Data from the public FPL API
          </p>
          <p className="mt-1">{site.disclaimer}</p>
        </footer>
        <Analytics />
      </body>
    </html>
  );
}
