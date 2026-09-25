import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import en from "../../messages/en.json";
import es from "../../messages/es.json";
import WebhookToolsPage from "@/app/[locale]/ai-assistant/tools/page";

const mocks = vi.hoisted(() => ({
  locale: "es" as "en" | "es",
  useWebhookTools: vi.fn(),
}));

vi.mock("next-intl", () => ({
  useLocale: () => mocks.locale,
  useTranslations:
    (namespace: "AIAssistantTools") =>
    (key: string, values?: Record<string, string>) => {
      const catalog = mocks.locale === "en" ? en : es;
      let value = catalog[namespace][
        key as keyof (typeof catalog)[typeof namespace]
      ];
      for (const [name, replacement] of Object.entries(values ?? {})) {
        value = value.replace(`{${name}}`, replacement);
      }
      return value;
    },
}));

vi.mock("@/components/layout/Header", () => ({ Header: () => null }));
vi.mock("@/modules/ai-assistant/hooks/useWebhookTools", () => ({
  useWebhookTools: mocks.useWebhookTools,
}));

const tool = {
  id: "tool-1",
  user_id: "user-1",
  name: "agendar_demo",
  description: "Schedules a demo",
  webhook_url: "https://hooks.example.test/demo",
  method: "POST",
  headers: {},
  input_schema: { type: "object", properties: {}, required: [] },
  auth_type: null,
  timeout_seconds: 30,
  max_retries: 1,
  is_enabled: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: null,
};

beforeEach(() => {
  mocks.locale = "es";
  mocks.useWebhookTools.mockReturnValue({
    tools: [tool],
    loading: false,
    error: null,
    fetchTools: vi.fn(),
    createTool: vi.fn(),
    updateTool: vi.fn(),
    deleteTool: vi.fn(),
  });
});

describe("AI assistant webhook tools i18n", () => {
  it("keeps the English and Spanish tool catalogs in sync", () => {
    expect(Object.keys(en.AIAssistantTools).sort()).toEqual(
      Object.keys(es.AIAssistantTools).sort(),
    );
    expect(en.AIAssistantTools.title).toBe("Webhook Tools");
    expect(es.AIAssistantTools.title).toBe("Herramientas Webhook");
  });

  it("renders Spanish copy and accessible names for icon-only actions", () => {
    render(<WebhookToolsPage />);

    expect(
      screen.getByRole("heading", { name: "Herramientas Webhook" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Editar agendar_demo" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Eliminar agendar_demo" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Abrir webhook de agendar_demo" }),
    ).toBeInTheDocument();
  });

  it("renders English copy and accessible names for icon-only actions", () => {
    mocks.locale = "en";
    render(<WebhookToolsPage />);

    expect(
      screen.getByRole("heading", { name: "Webhook Tools" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Edit agendar_demo" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Delete agendar_demo" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Open webhook for agendar_demo" }),
    ).toBeInTheDocument();
  });
});
