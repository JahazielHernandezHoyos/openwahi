import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/context/AuthContext";
import { itemsApi } from "../services/itemsApi";
import { Item, ItemCreate, ItemUpdate } from "../types";

// Query keys for cache management
export const itemsKeys = {
  all: ["items"] as const,
  detail: (id: string) => ["items", id] as const,
};

/**
 * Hook para obtener todos los items con TanStack Query
 */
export function useItems() {
  const queryClient = useQueryClient();
  const { user } = useAuth();

  // Query para obtener items
  const {
    data: items = [],
    isLoading: loading,
    error,
    refetch,
  } = useQuery({
    queryKey: itemsKeys.all,
    queryFn: itemsApi.getAll,
    enabled: !!user,
  });

  // Mutation para crear item con optimistic update
  const createMutation = useMutation({
    mutationFn: itemsApi.create,
    onMutate: async (newItemData: ItemCreate) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: itemsKeys.all });

      // Snapshot the previous value
      const previousItems = queryClient.getQueryData<Item[]>(itemsKeys.all);

      // Optimistically update with a temporary item
      const optimisticItem: Item = {
        id: `temp-${Date.now()}`,
        user_id: "",
        title: newItemData.title,
        description: newItemData.description || null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };

      queryClient.setQueryData<Item[]>(itemsKeys.all, (old = []) => [
        ...old,
        optimisticItem,
      ]);

      return { previousItems };
    },
    onError: (_err, _newItem, context) => {
      // Rollback on error
      if (context?.previousItems) {
        queryClient.setQueryData(itemsKeys.all, context.previousItems);
      }
    },
    onSettled: () => {
      // Always refetch after error or success
      queryClient.invalidateQueries({ queryKey: itemsKeys.all });
    },
  });

  // Mutation para actualizar item con optimistic update
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: ItemUpdate }) =>
      itemsApi.update(id, data),
    onMutate: async ({ id, data }) => {
      await queryClient.cancelQueries({ queryKey: itemsKeys.all });

      const previousItems = queryClient.getQueryData<Item[]>(itemsKeys.all);

      queryClient.setQueryData<Item[]>(itemsKeys.all, (old = []) =>
        old.map((item) =>
          item.id === id
            ? { ...item, ...data, updated_at: new Date().toISOString() }
            : item,
        ),
      );

      return { previousItems };
    },
    onError: (_err, _variables, context) => {
      if (context?.previousItems) {
        queryClient.setQueryData(itemsKeys.all, context.previousItems);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: itemsKeys.all });
    },
  });

  // Mutation para eliminar item con optimistic update
  const deleteMutation = useMutation({
    mutationFn: itemsApi.delete,
    onMutate: async (id: string) => {
      await queryClient.cancelQueries({ queryKey: itemsKeys.all });

      const previousItems = queryClient.getQueryData<Item[]>(itemsKeys.all);

      // Optimistically remove the item
      queryClient.setQueryData<Item[]>(itemsKeys.all, (old = []) =>
        old.filter((item) => item.id !== id),
      );

      return { previousItems };
    },
    onError: (_err, _id, context) => {
      if (context?.previousItems) {
        queryClient.setQueryData(itemsKeys.all, context.previousItems);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: itemsKeys.all });
    },
  });

  // Wrapper functions para mantener la API compatible
  const createItem = async (data: ItemCreate) => {
    return createMutation.mutateAsync(data);
  };

  const updateItem = async (id: string, data: ItemUpdate) => {
    return updateMutation.mutateAsync({ id, data });
  };

  const deleteItem = async (id: string) => {
    return deleteMutation.mutateAsync(id);
  };

  return {
    items,
    loading,
    error: error ? "Error al cargar los items" : null,
    createItem,
    updateItem,
    deleteItem,
    refetch,
    // Expose mutation states for UI feedback
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
  };
}
