import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/tools/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

import { adminApi } from "@/modules/admin/service";
import { apiClient } from "@/tools/api/client";

const mockedClient = vi.mocked(apiClient, { deep: true });

describe("adminApi AI provider chain", () => {
  beforeEach(() => vi.clearAllMocks());

  it("fetches the chain and health events", async () => {
    mockedClient.get.mockResolvedValue({ data: [] });

    await adminApi.getAIChain();
    await adminApi.getAIChainEvents(30);

    expect(mockedClient.get).toHaveBeenNthCalledWith(1, "/internal/admin/ai-chain");
    expect(mockedClient.get).toHaveBeenNthCalledWith(2, "/internal/admin/ai-chain/events", {
      params: { limit: 30 },
    });
  });

  it("creates, updates, probes, reorders, and deletes entries", async () => {
    mockedClient.post.mockResolvedValue({ data: { success: true, id: "entry-1" } });
    mockedClient.patch.mockResolvedValue({ data: { success: true } });
    mockedClient.delete.mockResolvedValue({ data: { success: true } });

    await adminApi.createAIChainEntry({
      provider_name: "groq",
      model: "model-1",
      requires_tools: true,
    });
    await adminApi.updateAIChainEntry("entry-1", { is_enabled: false });
    await adminApi.probeAIChainEntry("entry-1");
    await adminApi.reorderAIChain(["entry-2", "entry-1"]);
    await adminApi.deleteAIChainEntry("entry-1");

    expect(mockedClient.post).toHaveBeenCalledWith("/internal/admin/ai-chain", {
      provider_name: "groq",
      model: "model-1",
      requires_tools: true,
    });
    expect(mockedClient.patch).toHaveBeenCalledWith("/internal/admin/ai-chain/entry-1", {
      is_enabled: false,
    });
    expect(mockedClient.post).toHaveBeenCalledWith("/internal/admin/ai-chain/entry-1/probe");
    expect(mockedClient.post).toHaveBeenCalledWith("/internal/admin/ai-chain/reorder", {
      ordered_ids: ["entry-2", "entry-1"],
    });
    expect(mockedClient.delete).toHaveBeenCalledWith("/internal/admin/ai-chain/entry-1");
  });
});
