import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import en from "../../messages/en.json";
import es from "../../messages/es.json";
import LocaleNotFound from "@/app/[locale]/not-found";

const state = vi.hoisted(() => ({ locale: "en" as "en" | "es" }));

vi.mock("next-intl", () => ({
  useLocale: () => state.locale,
  useTranslations: (namespace: "notFound") => (key: "message" | "cta") => {
    const catalog = state.locale === "en" ? en : es;
    return catalog[namespace][key];
  },
}));

beforeEach(() => {
  state.locale = "en";
});

describe("localized 404", () => {
  it("renders English copy and links back to the English homepage", () => {
    render(<LocaleNotFound />);

    expect(screen.getByText("Page not found")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to home" })).toHaveAttribute(
      "href",
      "/en",
    );
  });

  it("renders Spanish copy and links back to the Spanish homepage", () => {
    state.locale = "es";
    render(<LocaleNotFound />);

    expect(screen.getByText("Página no encontrada")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Volver al inicio" })).toHaveAttribute(
      "href",
      "/es",
    );
  });
});
