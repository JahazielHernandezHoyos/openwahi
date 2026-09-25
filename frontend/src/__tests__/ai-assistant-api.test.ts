/**
 * Tests for aiAssistantApi service
 */
import { describe, it, expect, beforeEach, vi } from "vitest";

vi.mock("@/tools/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

import { aiAssistantApi } from "@/modules/ai-assistant/services/aiAssistantApi";
import {
  AI_SANDBOX_TIMEOUT_MS,
  resolveAISandboxTimeoutMs,
} from "@/modules/ai-assistant/config";
import { apiClient } from "@/tools/api/client";

const mockedClient = vi.mocked(apiClient, { deep: true });

describe("aiAssistantApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("getProviders fetches /ai-assistant/providers", async () => {
    mockedClient.get.mockResolvedValue({ data: ["groq", "openai"] });

    const result = await aiAssistantApi.getProviders();

    expect(mockedClient.get).toHaveBeenCalledWith("/ai-assistant/providers");
    expect(result).toEqual(["groq", "openai"]);
  });

  it("getProviderModels fetches models for a provider", async () => {
    mockedClient.get.mockResolvedValue({
      data: ["llama-3-70b", "mixtral-8x7b"],
    });

    const result = await aiAssistantApi.getProviderModels("groq");

    expect(mockedClient.get).toHaveBeenCalledWith(
      "/ai-assistant/providers/groq/models"
    );
    expect(result).toHaveLength(2);
  });

  it("createConfig posts to device configs endpoint", async () => {
    const config = { name: "Bot", provider: "groq", model: "llama-3-70b" };
    mockedClient.post.mockResolvedValue({
      data: { id: "c1", ...config },
    });

    const result = await aiAssistantApi.createConfig("d1", config as any);

    expect(mockedClient.post).toHaveBeenCalledWith(
      "/ai-assistant/devices/d1/configs",
      config
    );
    expect(result.id).toBe("c1");
  });

  it("listConfigs fetches configs for a device", async () => {
    mockedClient.get.mockResolvedValue({ data: [{ id: "c1" }] });

    const result = await aiAssistantApi.listConfigs("d1");

    expect(mockedClient.get).toHaveBeenCalledWith(
      "/ai-assistant/devices/d1/configs"
    );
    expect(result).toHaveLength(1);
  });

  it("getConfig fetches a specific config", async () => {
    mockedClient.get.mockResolvedValue({ data: { id: "c1", name: "Bot" } });

    const result = await aiAssistantApi.getConfig("c1");

    expect(mockedClient.get).toHaveBeenCalledWith(
      "/ai-assistant/configs/c1"
    );
    expect(result.name).toBe("Bot");
  });

  it("updateConfig patches a config", async () => {
    const updates = { name: "Updated Bot" };
    mockedClient.patch.mockResolvedValue({
      data: { id: "c1", ...updates },
    });

    const result = await aiAssistantApi.updateConfig("c1", updates as any);

    expect(mockedClient.patch).toHaveBeenCalledWith(
      "/ai-assistant/configs/c1",
      updates
    );
    expect(result.name).toBe("Updated Bot");
  });

  it("toggleConfig posts with enabled param", async () => {
    const response = {
      success: true,
      message: "enabled",
      config: { id: "c1" },
    };
    mockedClient.post.mockResolvedValue({ data: response });

    const result = await aiAssistantApi.toggleConfig("c1", true);

    expect(mockedClient.post).toHaveBeenCalledWith(
      "/ai-assistant/configs/c1/toggle",
      null,
      { params: { enabled: true } }
    );
    expect(result.success).toBe(true);
  });

  it("deleteConfig calls DELETE on config", async () => {
    mockedClient.delete.mockResolvedValue({});

    await aiAssistantApi.deleteConfig("c1");

    expect(mockedClient.delete).toHaveBeenCalledWith(
      "/ai-assistant/configs/c1"
    );
  });

  it("testConfig posts test message", async () => {
    const request = { message: "Hello", phone: "+1234" };
    const response = { response: "Hi there!", tokens_used: 50 };
    mockedClient.post.mockResolvedValue({ data: response });

    const result = await aiAssistantApi.testConfig("c1", request as any);

    expect(mockedClient.post).toHaveBeenCalledWith(
      "/ai-assistant/configs/c1/test",
      request,
      { timeout: 60000 }
    );
    expect(result.response).toBe("Hi there!");
  });

  it("uses a CPU-friendly configurable timeout for sandbox tests", () => {
    expect(AI_SANDBOX_TIMEOUT_MS).toBe(60000);
    expect(resolveAISandboxTimeoutMs("90000")).toBe(90000);
    expect(resolveAISandboxTimeoutMs("invalid")).toBe(60000);
    expect(resolveAISandboxTimeoutMs("0")).toBe(60000);
  });

  it("returns a specific UX error when the sandbox request times out", async () => {
    mockedClient.post.mockRejectedValue({
      isAxiosError: true,
      code: "ECONNABORTED",
    });

    await expect(
      aiAssistantApi.testConfig("c1", { message: "Hello" } as any)
    ).rejects.toThrow(
      "La prueba tardó más de lo esperado. El modelo local puede estar iniciando; inténtalo de nuevo."
    );
  });

  it("getConversationHistory fetches conversation", async () => {
    mockedClient.get.mockResolvedValue({
      data: { messages: [], from_phone: "+1234" },
    });

    const result = await aiAssistantApi.getConversationHistory("c1", "+1234");

    expect(mockedClient.get).toHaveBeenCalledWith(
      "/ai-assistant/configs/c1/conversations/+1234"
    );
    expect(result.from_phone).toBe("+1234");
  });

  it("getKnowledgeBases fetches /knowledge-base", async () => {
    mockedClient.get.mockResolvedValue({ data: [{ id: "kb1" }] });

    const result = await aiAssistantApi.getKnowledgeBases();

    expect(mockedClient.get).toHaveBeenCalledWith("/knowledge-base");
    expect(result).toHaveLength(1);
  });
});
