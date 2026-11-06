// Plausible custom events. No-ops when analytics isn't configured or is blocked.
declare global {
  interface Window {
    plausible?: (event: string, options?: { props?: Record<string, string | number> }) => void;
  }
}

export type AnalyticsEvent = "report_generated" | "card_downloaded";

export function track(event: AnalyticsEvent, props?: Record<string, string | number>): void {
  try {
    window.plausible?.(event, props ? { props } : undefined);
  } catch {
    // never let analytics break the page
  }
}
