/**
 * Tests for developerApi service
 */
import { describe, it, expect, beforeEach, vi } from "vitest";

vi.mock("@/tools/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

import { developerApi } from "@/modules/developer/services/developerApi";
import { apiClient } from "@/tools/api/client";

const mockedClient = vi.mocked(apiClient, { deep: true });

describe("developerApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ── API Tokens ───────────────────────────────────────────────────

  it("getTokens fetches /developer/tokens", async () => {
    const data = { tokens: [], total: 0 };
    mockedClient.get.mockResolvedValue({ data });

    const result = await developerApi.getTokens();

    expect(mockedClient.get).toHaveBeenCalledWith("/developer/tokens");
    expect(result).toEqual(data);
  });

  it("createToken posts name to /developer/tokens", async () => {
    const created = { id: "t1", name: "My Token", token: "whapi_abc123" };
    mockedClient.post.mockResolvedValue({ data: created });

    const result = await developerApi.createToken("My Token");

    expect(mockedClient.post).toHaveBeenCalledWith("/developer/tokens", {
      name: "My Token",
    });
    expect(result.token).toBe("whapi_abc123");
  });

  it("revokeToken deletes /developer/tokens/{id}", async () => {
    mockedClient.delete.mockResolvedValue({});

    await developerApi.revokeToken("t1");

    expect(mockedClient.delete).toHaveBeenCalledWith("/developer/tokens/t1");
  });

  // ── Webhook ──────────────────────────────────────────────────────

  it("getWebhook fetches /developer/webhook", async () => {
    const webhook = { url: "https://hook.example.com", events: ["message"] };
    mockedClient.get.mockResolvedValue({ data: webhook });

    const result = await developerApi.getWebhook();

    expect(mockedClient.get).toHaveBeenCalledWith("/developer/webhook");
    expect(result).toEqual(webhook);
  });

  it("getWebhook returns null on 404", async () => {
    mockedClient.get.mockRejectedValue({
      response: { status: 404 },
    });

    const result = await developerApi.getWebhook();

    expect(result).toBeNull();
  });

  it("getWebhook rethrows non-404 errors", async () => {
    mockedClient.get.mockRejectedValue({
      response: { status: 500 },
    });

    await expect(developerApi.getWebhook()).rejects.toEqual({
      response: { status: 500 },
    });
  });

  it("upsertWebhook puts to /developer/webhook", async () => {
    const config = { url: "https://hook.example.com", events: ["message"] };
    mockedClient.put.mockResolvedValue({ data: config });

    const result = await developerApi.upsertWebhook(config as any);

    expect(mockedClient.put).toHaveBeenCalledWith(
      "/developer/webhook",
      config
    );
    expect(result.url).toBe("https://hook.example.com");
  });

  it("deleteWebhook calls DELETE /developer/webhook", async () => {
    mockedClient.delete.mockResolvedValue({});

    await developerApi.deleteWebhook();

    expect(mockedClient.delete).toHaveBeenCalledWith("/developer/webhook");
  });

  it("testWebhook posts to /developer/webhook/test", async () => {
    const result_data = { success: true, status_code: 200 };
    mockedClient.post.mockResolvedValue({ data: result_data });

    const result = await developerApi.testWebhook();

    expect(mockedClient.post).toHaveBeenCalledWith("/developer/webhook/test");
    expect(result.success).toBe(true);
  });
});
