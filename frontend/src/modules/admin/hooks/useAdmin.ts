import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { adminApi } from "../service";
import type {
  CreateAIChainEntryInput,
  UpdateAIChainEntryInput,
} from "../service";

/** Current user from `/auth/me`; `is_admin` gates the admin panel. */
export function useCurrentUser(enabled: boolean) {
  return useQuery({
    queryKey: ["auth", "me"],
    queryFn: adminApi.getCurrentUser,
    enabled,
    retry: false,
    staleTime: 1000 * 60 * 5,
  });
}

export function useAdminStats() {
  return useQuery({
    queryKey: ["admin", "stats"],
    queryFn: adminApi.getStats,
    staleTime: 1000 * 30,
    refetchInterval: 1000 * 60,
  });
}

export function useAdminUsers() {
  return useQuery({
    queryKey: ["admin", "users"],
    queryFn: adminApi.getUsers,
    staleTime: 1000 * 30,
  });
}

export function useAdminUserUsage(userId: string | null) {
  return useQuery({
    queryKey: ["admin", "user-usage", userId],
    queryFn: () => adminApi.getUserUsage(userId!),
    enabled: !!userId,
  });
}

export function useAdminCosts() {
  return useQuery({
    queryKey: ["admin", "costs"],
    queryFn: adminApi.getCosts,
    staleTime: 1000 * 60,
  });
}

export function useUpdateUserPlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, plan }: { userId: string; plan: string }) =>
      adminApi.updateUserPlan(userId, plan),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin"] });
    },
  });
}

export function useToggleSubscription() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => adminApi.toggleSubscription(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin"] });
    },
  });
}

function useInvalidateAdminAIChain() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ["admin", "ai-chain"] });
}

export function useAdminAIChain() {
  return useQuery({
    queryKey: ["admin", "ai-chain"],
    queryFn: adminApi.getAIChain,
    staleTime: 1000 * 15,
    refetchInterval: 30_000,
  });
}

export function useAdminAIChainEvents() {
  return useQuery({
    queryKey: ["admin", "ai-chain", "events"],
    queryFn: () => adminApi.getAIChainEvents(100),
    staleTime: 1000 * 15,
  });
}

export function useCreateAIChainEntry() {
  const invalidate = useInvalidateAdminAIChain();
  return useMutation({
    mutationFn: (input: CreateAIChainEntryInput) => adminApi.createAIChainEntry(input),
    onSuccess: invalidate,
  });
}

export function useUpdateAIChainEntry() {
  const invalidate = useInvalidateAdminAIChain();
  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: UpdateAIChainEntryInput }) =>
      adminApi.updateAIChainEntry(id, input),
    onSuccess: invalidate,
  });
}

export function useDeleteAIChainEntry() {
  const invalidate = useInvalidateAdminAIChain();
  return useMutation({
    mutationFn: (id: string) => adminApi.deleteAIChainEntry(id),
    onSuccess: invalidate,
  });
}

export function useReorderAIChain() {
  const invalidate = useInvalidateAdminAIChain();
  return useMutation({
    mutationFn: (orderedIds: string[]) => adminApi.reorderAIChain(orderedIds),
    onSuccess: invalidate,
  });
}

export function useProbeAIChainEntry() {
  const invalidate = useInvalidateAdminAIChain();
  return useMutation({
    mutationFn: (id: string) => adminApi.probeAIChainEntry(id),
    onSettled: invalidate,
  });
}
