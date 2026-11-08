import type { NextConfig } from "next";

// The FastAPI backend (API_URL) is reached through src/app/api/leagues/[leagueId]/[resource]/route.ts,
// which adds the internal key and the visitor's IP. The browser never calls it directly.

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
