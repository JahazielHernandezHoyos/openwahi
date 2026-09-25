/**
 * Tests for token-manager
 * Pure logic tests with localStorage mock (jsdom provides it)
 */
import { describe, it, expect, beforeEach } from "vitest";
import { tokenManager } from "@/tools/auth/token-manager";

const ACCESS_KEY = "fb_id_token";

describe("tokenManager", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  // ── getAccessToken / setAccessToken ──────────────────────────────

  it("returns null when no access token is stored", () => {
    expect(tokenManager.getAccessToken()).toBeNull();
  });

  it("stores and retrieves an access token", () => {
    tokenManager.setAccessToken("firebase-id-token-abc");
    expect(tokenManager.getAccessToken()).toBe("firebase-id-token-abc");
    expect(localStorage.getItem(ACCESS_KEY)).toBe("firebase-id-token-abc");
  });

  // ── clearTokens ──────────────────────────────────────────────────

  it("clears token from localStorage", () => {
    tokenManager.setAccessToken("a");
    tokenManager.clearTokens();

    expect(localStorage.getItem(ACCESS_KEY)).toBeNull();
  });

  // ── hasToken ─────────────────────────────────────────────────────

  it("returns false when no token is stored", () => {
    expect(tokenManager.hasToken()).toBe(false);
  });

  it("returns true when an access token exists", () => {
    tokenManager.setAccessToken("exists");
    expect(tokenManager.hasToken()).toBe(true);
  });

  // ── overwrite behaviour ──────────────────────────────────────────

  it("overwrites existing access token", () => {
    tokenManager.setAccessToken("old");
    tokenManager.setAccessToken("new");
    expect(tokenManager.getAccessToken()).toBe("new");
  });
});
