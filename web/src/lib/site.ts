// Public site settings. Defaults are placeholders; set NEXT_PUBLIC_* env vars in production.
export const site = {
  name: process.env.NEXT_PUBLIC_SITE_NAME || "Mini-League Report",
  handle: process.env.NEXT_PUBLIC_INSTAGRAM_HANDLE || "@your_handle",
  url: (process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000").replace(/\/$/, ""),
  primary: process.env.NEXT_PUBLIC_BRAND_PRIMARY || "#FF5A36",
  accent: process.env.NEXT_PUBLIC_BRAND_ACCENT || "#FFC83D",
  disclaimer: "Not affiliated with the Premier League or Fantasy Premier League.",
};

export function instagramUrl(handle: string): string {
  return `https://www.instagram.com/${handle.replace(/^@/, "")}/`;
}
