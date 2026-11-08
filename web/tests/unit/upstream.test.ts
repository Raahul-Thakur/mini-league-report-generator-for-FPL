import { afterEach, describe, expect, it, vi } from "vitest";
import { upstreamHeaders, visitorIp } from "@/lib/upstream";

afterEach(() => vi.unstubAllEnvs());

describe("visitorIp", () => {
  it("prefers x-real-ip", () => {
    expect(visitorIp(new Headers({ "x-real-ip": "203.0.113.9", "x-forwarded-for": "1.1.1.1" }))).toBe("203.0.113.9");
  });
  it("falls back to the first x-forwarded-for entry", () => {
    expect(visitorIp(new Headers({ "x-forwarded-for": "198.51.100.4, 10.0.0.1" }))).toBe("198.51.100.4");
  });
  it("defaults to localhost in development", () => {
    expect(visitorIp(new Headers())).toBe("127.0.0.1");
  });
});

describe("upstreamHeaders", () => {
  it("sends the internal key only when configured", () => {
    vi.stubEnv("INTERNAL_API_KEY", "");
    expect(upstreamHeaders(new Headers({ "x-real-ip": "203.0.113.9" }))).toEqual({ "X-Client-IP": "203.0.113.9" });
    vi.stubEnv("INTERNAL_API_KEY", "k3y");
    expect(upstreamHeaders(new Headers())).toEqual({ "X-Client-IP": "127.0.0.1", "X-Internal-Key": "k3y" });
  });
});
