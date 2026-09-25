/**
 * Tests for the Axios API client
 * Verifies interceptors: JWT injection, X-API-Key skip, error handling
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import axios from "axios";

// Mock the token manager before importing the client
vi.mock("@/tools/auth/token-manager", () => ({
  tokenManager: {
    getAccessToken: vi.fn(),
    setAccessToken: vi.fn(),
    getRefreshToken: vi.fn(),
    setRefreshToken: vi.fn(),
    clearTokens: vi.fn(),
    hasToken: vi.fn(),
  },
}));

import { apiClient } from "@/tools/api/client";
import { AUTH_UNAUTHORIZED_EVENT } from "@/tools/auth/auth-events";
import { tokenManager } from "@/tools/auth/token-manager";

const mockedTokenManager = vi.mocked(tokenManager);

describe("apiClient", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("is an axios instance with correct baseURL", () => {
    expect(apiClient.defaults.baseURL).toBeDefined();
    expect(typeof apiClient.defaults.baseURL).toBe("string");
  });

  it("has Content-Type application/json by default", () => {
    expect(apiClient.defaults.headers["Content-Type"]).toBe(
      "application/json"
    );
  });

  it("has a 10s timeout", () => {
    expect(apiClient.defaults.timeout).toBe(10000);
  });

  // ── Request interceptor tests ────────────────────────────────────

  it("injects Authorization header when token exists", async () => {
    mockedTokenManager.getAccessToken.mockReturnValue("my-jwt-token");

    // Use the interceptor manually by running the request config through it
    const config = {
      url: "/test",
      headers: axios.defaults.headers as any,
    };

    // Access the request interceptor - it's the first one added
    const interceptors = (apiClient.interceptors.request as any).handlers;
    const requestInterceptor = interceptors[0];

    const result = await requestInterceptor.fulfilled({
      ...config,
      headers: new axios.AxiosHeaders({ "Content-Type": "application/json" }),
    });

    expect(result.headers.get("Authorization")).toBe("Bearer my-jwt-token");
  });

  it("skips JWT when X-API-Key is present", async () => {
    mockedTokenManager.getAccessToken.mockReturnValue("my-jwt-token");

    const interceptors = (apiClient.interceptors.request as any).handlers;
    const requestInterceptor = interceptors[0];

    const result = await requestInterceptor.fulfilled({
      url: "/test",
      headers: new axios.AxiosHeaders({
        "Content-Type": "application/json",
        "X-API-Key": "api-key-123",
      }),
    });

    // Should NOT have Authorization header since X-API-Key is present
    expect(result.headers.has("Authorization")).toBe(false);
    expect(result.headers.get("X-API-Key")).toBe("api-key-123");
  });

  it("proceeds without Authorization when no token", async () => {
    mockedTokenManager.getAccessToken.mockReturnValue(null);

    const interceptors = (apiClient.interceptors.request as any).handlers;
    const requestInterceptor = interceptors[0];

    const result = await requestInterceptor.fulfilled({
      url: "/test",
      headers: new axios.AxiosHeaders({ "Content-Type": "application/json" }),
    });

    expect(result.headers.has("Authorization")).toBe(false);
  });

  it("clears the cached token and announces a 401 to the auth guard", async () => {
    const listener = vi.fn();
    window.addEventListener(AUTH_UNAUTHORIZED_EVENT, listener);
    const responseInterceptor = (apiClient.interceptors.response as any).handlers[0];
    const error = {
      config: {},
      response: { status: 401 },
    };

    await expect(responseInterceptor.rejected(error)).rejects.toBe(error);

    expect(mockedTokenManager.clearTokens).toHaveBeenCalledOnce();
    expect(listener).toHaveBeenCalledOnce();
    window.removeEventListener(AUTH_UNAUTHORIZED_EVENT, listener);
  });
});
