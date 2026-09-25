/**
 * Tests for useAuth hook and AuthContext
 * Verifies context contract, error on missing provider
 */
import { beforeEach, describe, it, expect, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

const authControl = vi.hoisted(() => ({
  callback: undefined as ((user: any) => Promise<void>) | undefined,
}));

const defaultUser = {
  uid: "u1",
  email: "test@test.com",
  getIdToken: vi.fn().mockResolvedValue("jwt-abc"),
};

// Mock Firebase config
vi.mock("@/config/firebase", () => ({
  auth: {},
  app: {},
}));

// Mock Firebase Auth
vi.mock("firebase/auth", () => ({
  getAuth: vi.fn(() => ({ currentUser: null })),
  onAuthStateChanged: vi.fn((auth, callback) => {
    // Simulate a signed-in user
    callback({ uid: "u1", email: "test@test.com", getIdToken: vi.fn().mockResolvedValue("jwt-abc") });
    return vi.fn(); // unsubscribe
  }),
  onIdTokenChanged: vi.fn((auth, callback) => {
    authControl.callback = callback;
    return vi.fn(); // unsubscribe
  }),
  getRedirectResult: vi.fn().mockResolvedValue(null),
  signInWithRedirect: vi.fn().mockResolvedValue(undefined),
  signOut: vi.fn().mockResolvedValue(undefined),
  GoogleAuthProvider: class MockGoogleAuthProvider {},
}));

// Mock email whitelist
vi.mock("@/lib/email-whitelist", () => ({
  isEmailAllowed: vi.fn().mockReturnValue(true),
}));

// Mock token manager
vi.mock("@/tools/auth/token-manager", () => ({
  tokenManager: {
    getAccessToken: vi.fn(),
    setAccessToken: vi.fn(),
    clearTokens: vi.fn(),
    hasToken: vi.fn(),
  },
}));

import { AuthProvider, useAuth } from "@/context/AuthContext";
import { AUTH_UNAUTHORIZED_EVENT } from "@/tools/auth/auth-events";
import { tokenManager } from "@/tools/auth/token-manager";

function createHarness() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>{children}</AuthProvider>
    </QueryClientProvider>
  );
  return { queryClient, wrapper };
}

async function authenticate() {
  await act(async () => {
    await authControl.callback?.(defaultUser);
  });
}

describe("useAuth", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    defaultUser.getIdToken.mockResolvedValue("jwt-abc");
  });

  it("throws when used outside AuthProvider", () => {
    // Suppress React error boundary console noise
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});

    expect(() => {
      renderHook(() => useAuth());
    }).toThrow("useAuth must be used within an AuthProvider");

    spy.mockRestore();
  });

  it("provides auth context when inside AuthProvider", async () => {
    const { wrapper } = createHarness();

    const { result } = renderHook(() => useAuth(), { wrapper });
    await authenticate();

    expect(typeof result.current.signInWithGoogle).toBe("function");
    expect(typeof result.current.signOut).toBe("function");
  });

  it("exposes user after auth state loads", async () => {
    const { wrapper } = createHarness();

    const { result } = renderHook(() => useAuth(), { wrapper });
    await authenticate();

    // Wait for auth state to load
    await vi.waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.user).toBeTruthy();
    expect(result.current.user?.email).toBe("test@test.com");
  });

  it("keeps cached data when the same uid refreshes its token", async () => {
    const { queryClient, wrapper } = createHarness();
    const { result } = renderHook(() => useAuth(), { wrapper });
    await authenticate();
    await vi.waitFor(() => expect(result.current.loading).toBe(false));
    queryClient.setQueryData(["private"], "u1-data");

    await act(async () => {
      authControl.callback?.({
        ...defaultUser,
        getIdToken: vi.fn().mockResolvedValue("jwt-refreshed"),
      });
    });

    expect(queryClient.getQueryData(["private"])).toBe("u1-data");
    expect(result.current.idToken).toBe("jwt-refreshed");
  });

  it("cancels and clears cached data when the uid changes", async () => {
    const { queryClient, wrapper } = createHarness();
    const cancelQueries = vi.spyOn(queryClient, "cancelQueries");
    const { result } = renderHook(() => useAuth(), { wrapper });
    await authenticate();
    await vi.waitFor(() => expect(result.current.user?.uid).toBe("u1"));
    queryClient.setQueryData(["private"], "u1-data");

    await act(async () => {
      authControl.callback?.({
        uid: "u2",
        email: "other@test.com",
        getIdToken: vi.fn().mockResolvedValue("jwt-u2"),
      });
    });

    expect(cancelQueries).toHaveBeenCalled();
    expect(queryClient.getQueryData(["private"])).toBeUndefined();
    expect(result.current.user?.uid).toBe("u2");
  });

  it("cancels and clears cached data on logout and 401", async () => {
    const { queryClient, wrapper } = createHarness();
    const cancelQueries = vi.spyOn(queryClient, "cancelQueries");
    const { result } = renderHook(() => useAuth(), { wrapper });
    await authenticate();
    await vi.waitFor(() => expect(result.current.user?.uid).toBe("u1"));

    queryClient.setQueryData(["private"], "logout-data");
    await act(async () => authControl.callback?.(null));
    expect(queryClient.getQueryData(["private"])).toBeUndefined();

    queryClient.setQueryData(["private"], "401-data");
    await act(async () => window.dispatchEvent(new Event(AUTH_UNAUTHORIZED_EVENT)));
    await vi.waitFor(() =>
      expect(queryClient.getQueryData(["private"])).toBeUndefined(),
    );

    expect(cancelQueries).toHaveBeenCalledTimes(2);
    expect(result.current.user).toBeNull();
  });

  it("does not restore a stale token result after logout", async () => {
    const { wrapper } = createHarness();
    const { result } = renderHook(() => useAuth(), { wrapper });
    await authenticate();
    await vi.waitFor(() => expect(result.current.user?.uid).toBe("u1"));
    let resolveToken!: (token: string) => void;
    const deferredToken = new Promise<string>((resolve) => {
      resolveToken = resolve;
    });

    act(() => {
      authControl.callback?.({
        ...defaultUser,
        getIdToken: vi.fn(() => deferredToken),
      });
      authControl.callback?.(null);
    });
    await act(async () => resolveToken("stale-token"));

    expect(result.current.user).toBeNull();
    expect(result.current.idToken).toBeNull();
    expect(tokenManager.setAccessToken).not.toHaveBeenCalledWith("stale-token");
  });
});
