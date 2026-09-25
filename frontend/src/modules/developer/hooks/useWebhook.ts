import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/context/AuthContext";
import { developerApi } from "../services/developerApi";
import { WebhookConfigCreate } from "../types";

export const WEBHOOK_QUERY_KEY = ["webhook-config"];

export function useWebhook() {
  const queryClient = useQueryClient();
  const { user } = useAuth();

  const {
    data: webhook,
    isLoading: loading,
    error,
    refetch,
  } = useQuery({
    queryKey: WEBHOOK_QUERY_KEY,
    queryFn: () => developerApi.getWebhook(),
    enabled: !!user,
    staleTime: 60000,
  });

  const upsertMutation = useMutation({
    mutationFn: (config: WebhookConfigCreate) =>
      developerApi.upsertWebhook(config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: WEBHOOK_QUERY_KEY });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => developerApi.deleteWebhook(),
    onSuccess: () => {
      queryClient.setQueryData(WEBHOOK_QUERY_KEY, null);
    },
  });

  const testMutation = useMutation({
    mutationFn: () => developerApi.testWebhook(),
  });

  return {
    webhook,
    loading,
    error,
    refetch,
    upsertWebhook: upsertMutation.mutateAsync,
    isSaving: upsertMutation.isPending,
    deleteWebhook: deleteMutation.mutateAsync,
    isDeleting: deleteMutation.isPending,
    testWebhook: testMutation.mutateAsync,
    isTesting: testMutation.isPending,
    testResult: testMutation.data,
  };
}
