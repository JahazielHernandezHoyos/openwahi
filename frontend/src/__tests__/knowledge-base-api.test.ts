/**
 * Tests for knowledgeBaseApi service
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

import { knowledgeBaseApi } from "@/modules/knowledge-base/services/knowledgeBaseApi";
import { apiClient } from "@/tools/api/client";

const mockedClient = vi.mocked(apiClient, { deep: true });

describe("knowledgeBaseApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ── Knowledge Base CRUD ──────────────────────────────────────────

  it("listKnowledgeBases fetches /knowledge-base", async () => {
    mockedClient.get.mockResolvedValue({ data: [{ id: "kb1" }] });

    const result = await knowledgeBaseApi.listKnowledgeBases();

    expect(mockedClient.get).toHaveBeenCalledWith("/knowledge-base");
    expect(result).toHaveLength(1);
  });

  it("listKnowledgeBases includes inactive when requested", async () => {
    mockedClient.get.mockResolvedValue({ data: [] });

    await knowledgeBaseApi.listKnowledgeBases(true);

    expect(mockedClient.get).toHaveBeenCalledWith(
      "/knowledge-base?include_inactive=true"
    );
  });

  it("getKnowledgeBase fetches by id", async () => {
    mockedClient.get.mockResolvedValue({
      data: { id: "kb1", name: "FAQ" },
    });

    const result = await knowledgeBaseApi.getKnowledgeBase("kb1");

    expect(mockedClient.get).toHaveBeenCalledWith("/knowledge-base/kb1");
    expect(result.name).toBe("FAQ");
  });

  it("createKnowledgeBase posts data", async () => {
    const data = { name: "FAQ", description: "Frequently asked" };
    mockedClient.post.mockResolvedValue({
      data: { id: "kb1", ...data },
    });

    const result = await knowledgeBaseApi.createKnowledgeBase(data as any);

    expect(mockedClient.post).toHaveBeenCalledWith("/knowledge-base", data);
    expect(result.id).toBe("kb1");
  });

  it("updateKnowledgeBase patches by id", async () => {
    const updates = { name: "Updated FAQ" };
    mockedClient.patch.mockResolvedValue({
      data: { id: "kb1", ...updates },
    });

    const result = await knowledgeBaseApi.updateKnowledgeBase(
      "kb1",
      updates as any
    );

    expect(mockedClient.patch).toHaveBeenCalledWith(
      "/knowledge-base/kb1",
      updates
    );
    expect(result.name).toBe("Updated FAQ");
  });

  it("deleteKnowledgeBase calls DELETE", async () => {
    mockedClient.delete.mockResolvedValue({});

    await knowledgeBaseApi.deleteKnowledgeBase("kb1");

    expect(mockedClient.delete).toHaveBeenCalledWith("/knowledge-base/kb1");
  });

  it("toggleKnowledgeBase posts toggle", async () => {
    const response = {
      success: true,
      message: "activated",
      knowledge_base: { id: "kb1" },
    };
    mockedClient.post.mockResolvedValue({ data: response });

    const result = await knowledgeBaseApi.toggleKnowledgeBase("kb1", true);

    expect(mockedClient.post).toHaveBeenCalledWith(
      "/knowledge-base/kb1/toggle?is_active=true"
    );
    expect(result.success).toBe(true);
  });

  // ── Documents ────────────────────────────────────────────────────

  it("listDocuments fetches documents for a KB", async () => {
    mockedClient.get.mockResolvedValue({ data: [{ id: "doc1" }] });

    const result = await knowledgeBaseApi.listDocuments("kb1");

    expect(mockedClient.get).toHaveBeenCalledWith(
      "/knowledge-base/kb1/documents"
    );
    expect(result).toHaveLength(1);
  });

  it("getDocument fetches specific document", async () => {
    mockedClient.get.mockResolvedValue({
      data: { id: "doc1", filename: "faq.pdf" },
    });

    const result = await knowledgeBaseApi.getDocument("kb1", "doc1");

    expect(mockedClient.get).toHaveBeenCalledWith(
      "/knowledge-base/kb1/documents/doc1"
    );
    expect(result.filename).toBe("faq.pdf");
  });

  it("deleteDocument calls DELETE on document", async () => {
    mockedClient.delete.mockResolvedValue({});

    await knowledgeBaseApi.deleteDocument("kb1", "doc1");

    expect(mockedClient.delete).toHaveBeenCalledWith(
      "/knowledge-base/kb1/documents/doc1"
    );
  });

  it("reprocessDocument posts to reprocess endpoint", async () => {
    const response = { success: true, message: "reprocessing" };
    mockedClient.post.mockResolvedValue({ data: response });

    const result = await knowledgeBaseApi.reprocessDocument("kb1", "doc1");

    expect(mockedClient.post).toHaveBeenCalledWith(
      "/knowledge-base/kb1/documents/doc1/reprocess"
    );
    expect(result.success).toBe(true);
  });

  // ── Search ───────────────────────────────────────────────────────

  it("searchKnowledgeBase posts query", async () => {
    const request = { query: "what is the return policy?", top_k: 5 };
    const response = { results: [], total: 0 };
    mockedClient.post.mockResolvedValue({ data: response });

    const result = await knowledgeBaseApi.searchKnowledgeBase(
      "kb1",
      request as any
    );

    expect(mockedClient.post).toHaveBeenCalledWith(
      "/knowledge-base/kb1/query",
      request
    );
    expect(result).toEqual(response);
  });

  it("searchAllKnowledgeBases posts to query-all", async () => {
    const request = { query: "pricing", top_k: 3 };
    const response = { results: [], total: 0 };
    mockedClient.post.mockResolvedValue({ data: response });

    const result = await knowledgeBaseApi.searchAllKnowledgeBases(
      request as any
    );

    expect(mockedClient.post).toHaveBeenCalledWith(
      "/knowledge-base/query-all",
      request
    );
    expect(result).toEqual(response);
  });
});
