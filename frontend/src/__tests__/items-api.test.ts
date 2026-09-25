/**
 * Tests for itemsApi service
 * Mocks the apiClient to verify correct endpoints, params, and return values
 */
import { describe, it, expect, beforeEach, vi } from "vitest";

// Mock apiClient
vi.mock("@/tools/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

import { itemsApi } from "@/modules/items/services/itemsApi";
import { apiClient } from "@/tools/api/client";
import type { Item, PaginatedItems } from "@/modules/items/types";

const mockedClient = vi.mocked(apiClient, { deep: true });

const mockItem: Item = {
  id: "item-1",
  user_id: "user-1",
  title: "Test Item",
  description: "A test item",
  created_at: "2025-01-01T00:00:00Z",
  updated_at: "2025-01-01T00:00:00Z",
};

const mockPaginated: PaginatedItems = {
  items: [mockItem],
  total: 1,
  limit: 50,
  offset: 0,
};

describe("itemsApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("getAll fetches /items/ and returns items array", async () => {
    mockedClient.get.mockResolvedValue({ data: mockPaginated });

    const result = await itemsApi.getAll();

    expect(mockedClient.get).toHaveBeenCalledWith("/items/");
    expect(result).toEqual([mockItem]);
  });

  it("getPaginated passes limit and offset", async () => {
    mockedClient.get.mockResolvedValue({ data: mockPaginated });

    const result = await itemsApi.getPaginated(10, 5);

    expect(mockedClient.get).toHaveBeenCalledWith("/items/?limit=10&offset=5");
    expect(result).toEqual(mockPaginated);
  });

  it("getById fetches /items/{id}", async () => {
    mockedClient.get.mockResolvedValue({ data: mockItem });

    const result = await itemsApi.getById("item-1");

    expect(mockedClient.get).toHaveBeenCalledWith("/items/item-1");
    expect(result).toEqual(mockItem);
  });

  it("create posts to /items/ with data", async () => {
    const newItem = { title: "New", description: "Desc" };
    mockedClient.post.mockResolvedValue({ data: { ...mockItem, ...newItem } });

    const result = await itemsApi.create(newItem);

    expect(mockedClient.post).toHaveBeenCalledWith("/items/", newItem);
    expect(result.title).toBe("New");
  });

  it("update puts to /items/{id} with data", async () => {
    const updates = { title: "Updated" };
    mockedClient.put.mockResolvedValue({
      data: { ...mockItem, ...updates },
    });

    const result = await itemsApi.update("item-1", updates);

    expect(mockedClient.put).toHaveBeenCalledWith("/items/item-1", updates);
    expect(result.title).toBe("Updated");
  });

  it("delete calls DELETE /items/{id}", async () => {
    mockedClient.delete.mockResolvedValue({});

    await itemsApi.delete("item-1");

    expect(mockedClient.delete).toHaveBeenCalledWith("/items/item-1");
  });
});
