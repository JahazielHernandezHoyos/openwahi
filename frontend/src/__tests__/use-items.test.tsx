/**
 * Tests for useItems hook
 * Tests React Query integration, optimistic updates, and error states
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

// Mock auth context
vi.mock("@/context/AuthContext", () => ({
  useAuth: vi.fn(() => ({
    user: { uid: "user-1", email: "test@test.com" },
    idToken: "test-token",
    loading: false,
    signInWithGoogle: vi.fn(),
    signOut: vi.fn(),
  })),
}));

// Mock items API
vi.mock("@/modules/items/services/itemsApi", () => ({
  itemsApi: {
    getAll: vi.fn(),
    getPaginated: vi.fn(),
    getById: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
  },
}));

import { useItems, itemsKeys } from "@/modules/items/hooks/useItems";
import { useAuth } from "@/context/AuthContext";
import { itemsApi } from "@/modules/items/services/itemsApi";
import type { Item } from "@/modules/items/types";

const mockedItemsApi = vi.mocked(itemsApi);
const mockedUseAuth = vi.mocked(useAuth);

const mockItem: Item = {
  id: "item-1",
  user_id: "user-1",
  title: "Test Item",
  description: "Description",
  created_at: "2025-01-01T00:00:00Z",
  updated_at: "2025-01-01T00:00:00Z",
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

describe("useItems", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedItemsApi.getAll.mockResolvedValue([mockItem]);
  });

  it("fetches items when user is authenticated", async () => {
    const { result } = renderHook(() => useItems(), {
      wrapper: createWrapper(),
    });

    // Initially loading
    expect(result.current.loading).toBe(true);

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.items).toEqual([mockItem]);
    expect(mockedItemsApi.getAll).toHaveBeenCalled();
  });

  it("does not fetch when user is not authenticated", async () => {
    mockedUseAuth.mockReturnValue({
      user: null,
      idToken: null,
      loading: false,
      signInWithGoogle: vi.fn(),
      signOut: vi.fn(),
    });

    const { result } = renderHook(() => useItems(), {
      wrapper: createWrapper(),
    });

    // Should not be loading because query is disabled
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(mockedItemsApi.getAll).not.toHaveBeenCalled();
    expect(result.current.items).toEqual([]);

    // Restore mock
    mockedUseAuth.mockReturnValue({
      user: { uid: "user-1", email: "test@test.com" } as any,
      idToken: "test-token",
      loading: false,
      signInWithGoogle: vi.fn(),
      signOut: vi.fn(),
    });
  });

  it("createItem calls itemsApi.create", async () => {
    const newItem = { ...mockItem, id: "item-2", title: "New Item" };
    mockedItemsApi.create.mockResolvedValue(newItem);

    const { result } = renderHook(() => useItems(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.createItem({ title: "New Item" });
    });

    expect(mockedItemsApi.create).toHaveBeenCalled();
    expect(mockedItemsApi.create.mock.calls[0][0]).toEqual({ title: "New Item" });
  });

  it("updateItem calls itemsApi.update with id and data", async () => {
    const updated = { ...mockItem, title: "Updated" };
    mockedItemsApi.update.mockResolvedValue(updated);

    const { result } = renderHook(() => useItems(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.updateItem("item-1", { title: "Updated" });
    });

    // mutationFn wraps the args, so check the actual API was called
    expect(mockedItemsApi.update).toHaveBeenCalled();
    const [id, data] = mockedItemsApi.update.mock.calls[0];
    expect(id).toBe("item-1");
    expect(data).toEqual({ title: "Updated" });
  });

  it("deleteItem calls itemsApi.delete", async () => {
    mockedItemsApi.delete.mockResolvedValue(undefined);

    const { result } = renderHook(() => useItems(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.deleteItem("item-1");
    });

    expect(mockedItemsApi.delete).toHaveBeenCalled();
    expect(mockedItemsApi.delete.mock.calls[0][0]).toBe("item-1");
  });

  it("exposes mutation pending states", async () => {
    const { result } = renderHook(() => useItems(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.isCreating).toBe(false);
    expect(result.current.isUpdating).toBe(false);
    expect(result.current.isDeleting).toBe(false);
  });

  it("returns error message when query fails", async () => {
    mockedItemsApi.getAll.mockRejectedValue(new Error("Network error"));

    const { result } = renderHook(() => useItems(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.error).toBe("Error al cargar los items");
    });
  });

  it("exports correct query keys", () => {
    expect(itemsKeys.all).toEqual(["items"]);
    expect(itemsKeys.detail("abc")).toEqual(["items", "abc"]);
  });
});
