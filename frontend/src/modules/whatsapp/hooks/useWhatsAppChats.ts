/**
 * Hook for managing WhatsApp chats (conversations)
 */
import { useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/context/AuthContext";
import { whatsappApi } from "../services/whatsappApi";

export const CHATS_QUERY_KEY = ["whatsapp-chats"];

// Polling interval used as fallback when the WebSocket is disconnected.
// Keeps the chat list fresh even without a live WS connection.
const FALLBACK_POLL_INTERVAL = 5000; // 5 s

export function useWhatsAppChats(deviceId?: string, wsConnected = false) {
  const queryClient = useQueryClient();
  const { user } = useAuth();

  const {
    data: chatsData,
    isLoading: loading,
    error,
    refetch,
  } = useQuery({
    queryKey: [...CHATS_QUERY_KEY, deviceId],
    queryFn: () => whatsappApi.getChats(deviceId),
    enabled: !!deviceId && !!user,
    staleTime: 0,
    refetchOnWindowFocus: true,
    // Poll every 5 s when WS is down; let WS invalidation handle updates when connected
    refetchInterval: wsConnected ? false : FALLBACK_POLL_INTERVAL,
  });

  const invalidateChats = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: CHATS_QUERY_KEY });
  }, [queryClient]);

  return {
    chats: chatsData?.chats || [],
    total: chatsData?.total || 0,
    loading,
    error: error?.message || null,
    refetch,
    invalidateChats,
  };
}

export function useWhatsAppChatMessages(
  phone: string | null,
  deviceId: string | null,
  wsConnected = false,
  limit = 50,
  offset = 0,
) {
  const queryClient = useQueryClient();
  const { user } = useAuth();

  const {
    data: messagesData,
    isLoading: loading,
    error,
    refetch,
  } = useQuery({
    queryKey: ["whatsapp-chat-messages", phone, deviceId, limit, offset],
    queryFn: () =>
      phone && deviceId
        ? whatsappApi.getChatMessages(phone, deviceId, limit, offset)
        : null,
    enabled: !!phone && !!deviceId && !!user,
    staleTime: 0,
    refetchOnWindowFocus: true,
    // Poll every 5 s when WS is down
    refetchInterval: wsConnected ? false : FALLBACK_POLL_INTERVAL,
  });

  const invalidateMessages = useCallback(() => {
    queryClient.invalidateQueries({
      queryKey: ["whatsapp-chat-messages", phone, deviceId],
    });
  }, [queryClient, phone, deviceId]);

  return {
    messages: messagesData?.messages || [],
    total: messagesData?.total || 0,
    limit: messagesData?.limit || limit,
    offset: messagesData?.offset || offset,
    loading,
    error: error?.message || null,
    refetch,
    invalidateMessages,
  };
}
