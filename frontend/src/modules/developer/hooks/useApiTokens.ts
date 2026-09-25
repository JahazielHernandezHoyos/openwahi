import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/context/AuthContext";
import { developerApi } from "../services/developerApi";

export const API_TOKENS_QUERY_KEY = ["api-tokens"];

export function useApiTokens() {
  const queryClient = useQueryClient();
  const { user } = useAuth();

  const {
    data: tokensData,
    isLoading: loading,
    error,
    refetch,
  } = useQuery({
    queryKey: API_TOKENS_QUERY_KEY,
    queryFn: () => developerApi.getTokens(),
    enabled: !!user,
    staleTime: 60000, // Consider data fresh for 1 minute
  });

  const createMutation = useMutation({
    mutationFn: (name: string) => developerApi.createToken(name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: API_TOKENS_QUERY_KEY });
    },
  });

  const revokeMutation = useMutation({
    mutationFn: (tokenId: string) => developerApi.revokeToken(tokenId),
    onMutate: async (tokenId) => {
      await queryClient.cancelQueries({ queryKey: API_TOKENS_QUERY_KEY });
      const previous = queryClient.getQueryData<any>(API_TOKENS_QUERY_KEY);

      if (previous) {
        queryClient.setQueryData(API_TOKENS_QUERY_KEY, {
          ...previous,
          tokens: previous.tokens.filter((t: any) => t.id !== tokenId),
        });
      }

      return { previous };
    },
    onError: (err, tokenId, context) => {
      if (context?.previous) {
        queryClient.setQueryData(API_TOKENS_QUERY_KEY, context.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: API_TOKENS_QUERY_KEY });
    },
  });

  return {
    tokens: tokensData?.tokens || [],
    total: tokensData?.total || 0,
    loading,
    error,
    refetch,
    createToken: createMutation.mutateAsync,
    isCreating: createMutation.isPending,
    revokeToken: revokeMutation.mutateAsync,
    isRevoking: revokeMutation.isPending,
  };
}
