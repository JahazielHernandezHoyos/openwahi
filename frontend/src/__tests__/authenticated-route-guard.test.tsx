import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const authState = vi.hoisted(() => ({
  loading: true,
  user: null as { uid: string } | null,
}));
const replace = vi.hoisted(() => vi.fn());
const navigationState = vi.hoisted(() => ({ pathname: "/es/dashboard" }));

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => authState,
}));
vi.mock("next/navigation", () => ({
  usePathname: () => navigationState.pathname,
  useRouter: () => ({ replace }),
}));

import {
  AuthenticatedRouteGuard,
  getPrivateRouteLocale,
} from "@/components/auth/AuthenticatedRouteGuard";

describe("AuthenticatedRouteGuard", () => {
  beforeEach(() => {
    authState.loading = true;
    authState.user = null;
    navigationState.pathname = "/es/dashboard";
    replace.mockClear();
  });

  it.each([
    "/es/dashboard",
    "/es/items",
    "/es/whatsapp-devices",
    "/es/whatsapp-chats",
    "/es/ai-assistant",
    "/es/ai-assistant/tools",
    "/es/knowledge-base",
    "/es/developer",
    "/es/admin/super-secret",
  ])("recognizes %s as private", (pathname) => {
    expect(getPrivateRouteLocale(pathname)).toBe("es");
  });

  it.each(["/es", "/es/login"])(
    "keeps %s public",
    (pathname) => {
      expect(getPrivateRouteLocale(pathname)).toBeNull();
    },
  );

  it("does not render private children or redirect while auth is loading", () => {
    render(
      <AuthenticatedRouteGuard>
        <div>private query owner</div>
      </AuthenticatedRouteGuard>,
    );

    expect(screen.queryByText("private query owner")).not.toBeInTheDocument();
    expect(replace).not.toHaveBeenCalled();
  });

  it("does not mount admin hooks before authentication resolves", () => {
    navigationState.pathname = "/es/admin/super-secret";
    const useAdminHook = vi.fn();
    function AdminPage() {
      useAdminHook();
      return <div>admin</div>;
    }

    render(
      <AuthenticatedRouteGuard>
        <AdminPage />
      </AuthenticatedRouteGuard>,
    );

    expect(useAdminHook).not.toHaveBeenCalled();
    expect(screen.queryByText("admin")).not.toBeInTheDocument();
  });

  it("redirects an unauthenticated visitor without rendering private children", () => {
    authState.loading = false;

    render(
      <AuthenticatedRouteGuard>
        <div>private query owner</div>
      </AuthenticatedRouteGuard>,
    );

    expect(screen.queryByText("private query owner")).not.toBeInTheDocument();
    expect(replace).toHaveBeenCalledWith("/es/login");
  });

  it("renders private children only after authentication resolves", () => {
    authState.loading = false;
    authState.user = { uid: "user-1" };

    render(
      <AuthenticatedRouteGuard>
        <div>private query owner</div>
      </AuthenticatedRouteGuard>,
    );

    expect(screen.getByText("private query owner")).toBeInTheDocument();
  });
});
