/**
 * Tests for buildWebSocketUrl utility
 */
import { describe, it, expect } from "vitest";
import { buildWebSocketUrl } from "@/tools/hooks/useWebSocket";

describe("buildWebSocketUrl()", () => {
  it("converts https to wss", () => {
    // jsdom defaults to http, so we test the fallback
    const url = buildWebSocketUrl("https://api.example.com", "/ws/chat");
    // In jsdom, window.location.protocol is 'http:' so it should use 'ws:'
    expect(url).toMatch(/^wss?:\/\/api\.example\.com\/ws\/chat$/);
  });

  it("converts http to ws", () => {
    const url = buildWebSocketUrl("http://localhost:8000", "/ws");
    expect(url).toBe("ws://localhost:8000/ws");
  });

  it("appends query parameters", () => {
    const url = buildWebSocketUrl("https://api.example.com", "/ws", {
      token: "abc123",
      device: "dev-1",
    });
    expect(url).toContain("token=abc123");
    expect(url).toContain("device=dev-1");
    expect(url).toContain("?");
  });

  it("returns url without ? when no params", () => {
    const url = buildWebSocketUrl("http://localhost:8000", "/ws");
    expect(url).not.toContain("?");
  });

  it("handles empty params object", () => {
    const url = buildWebSocketUrl("http://localhost:8000", "/ws", {});
    expect(url).not.toContain("?");
  });
});
