/**
 * Hook for managing WhatsApp messages
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/context/AuthContext";
import { whatsappApi } from "../services/whatsappApi";
import { SendMessageRequest } from "../types";

export function useWhatsAppMessages(deviceId: string | null) {
  const queryClient = useQueryClient();
  const { user } = useAuth();

  // Fetch messages
  const {
    data: messagesData,
    isLoading: loading,
    error,
    refetch,
  } = useQuery({
    queryKey: ["whatsapp-messages", deviceId],
    queryFn: () => (deviceId ? whatsappApi.getMessages(deviceId) : null),
    enabled: !!deviceId && !!user,
    // No polling needed - WebSocket provides real-time updates
  });

  // Send message mutation
  const sendMutation = useMutation({
    mutationFn: (data: SendMessageRequest) => {
      if (!deviceId) throw new Error("No device selected");
      return whatsappApi.sendMessage(deviceId, data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["whatsapp-messages", deviceId],
      });
    },
  });

  return {
    messages: messagesData?.messages || [],
    total: messagesData?.total || 0,
    loading,
    error: error?.message || null,
    refetch,
    sendMessage: sendMutation.mutateAsync,
    isSending: sendMutation.isPending,
    sendError: sendMutation.error?.message || null,
  };
}
