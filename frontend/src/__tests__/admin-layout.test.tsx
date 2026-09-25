import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const state = vi.hoisted(() => ({
  auth: { user: null as { uid: string } | null, loading: false },
  currentUser: { data: undefined as { is_admin: boolean } | undefined, isPending: true },
  locale: "en",
}));
const notFound = vi.hoisted(() =>
  vi.fn(() => {
    throw new Error("NEXT_NOT_FOUND");
  }),
);
const redirect = vi.hoisted(() =>
  vi.fn((url: string) => {
    throw new Error(`NEXT_REDIRECT ${url}`);
  }),
);

vi.mock("@/context/AuthContext", () => ({ useAuth: () => state.auth }));
vi.mock("@/modules/admin/hooks/useAdmin", () => ({
  useCurrentUser: () => state.currentUser,
}));
vi.mock("@/tools/hooks/useMounted", () => ({ useMounted: () => true }));
vi.mock("next-intl", () => ({ useLocale: () => state.locale }));
vi.mock("next/navigation", () => ({ notFound, redirect }));

import AdminLayout from "@/app/[locale]/admin/layout";

const renderLayout = () =>
  render(
    <AdminLayout>
      <div>admin panel</div>
    </AdminLayout>,
  );

describe("AdminLayout", () => {
  beforeEach(() => {
    state.auth = { user: { uid: "user-1" }, loading: false };
    state.currentUser = { data: undefined, isPending: true };
    state.locale = "en";
    notFound.mockClear();
    redirect.mockClear();
  });

  it("redirects anonymous visitors to the login page of the current locale", () => {
    state.auth.user = null;
    state.locale = "es";

    expect(renderLayout).toThrow("NEXT_REDIRECT /es/login");
  });

  it("renders nothing while /auth/me is loading", () => {
    renderLayout();

    expect(screen.queryByText("admin panel")).not.toBeInTheDocument();
    expect(notFound).not.toHaveBeenCalled();
  });

  it("hides the panel from signed-in users who are not admins", () => {
    state.currentUser = { data: { is_admin: false }, isPending: false };

    expect(renderLayout).toThrow("NEXT_NOT_FOUND");
  });

  it("hides the panel when /auth/me fails", () => {
    state.currentUser = { data: undefined, isPending: false };

    expect(renderLayout).toThrow("NEXT_NOT_FOUND");
  });

  it("renders the panel for admins", () => {
    state.currentUser = { data: { is_admin: true }, isPending: false };

    renderLayout();

    expect(screen.getByText("admin panel")).toBeInTheDocument();
  });
});
