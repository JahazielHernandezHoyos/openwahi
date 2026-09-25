"use client";

import { useMemo } from "react";
import { useAuth } from "@/context/AuthContext";
import { API_BASE_URL } from "@/config/constants";
import {
  useWebSocket,
  buildWebSocketUrl,
  WebSocketMessage,
  WebSocketStatus,
} from "@/tools/hooks/useWebSocket";

/**
 * WhatsApp-specific message data structure
 */
export interface WhatsAppMessageData {
  id?: string;
  message_id?: string;
  from?: string;
  from_phone?: string;
  to?: string;
  to_phone?: string;
  body?: string;
  type?: string;
  is_from_me?: boolean;
  status?: string;
  timestamp?: string;
  phone?: string;
  message?: string;
  chat_id?: string;
  receipt_type?: string;
  media_url?: string;
  caption?: string;
}

/**
 * WhatsApp WebSocket message types
 */
export type WhatsAppMessageType =
  | "new_message"
  | "message_sent"
  | "message_ack"
  | "device_status"
  | "connection"
  | "pong";

/**
 * WhatsApp WebSocket message structure
 */
export interface WhatsAppWebSocketMessage extends WebSocketMessage<WhatsAppMessageData> {
  type: WhatsAppMessageType;
  device_id?: string;
  phone?: string;
}

/**
 * Options for useWhatsAppWebSocket hook
 */
export interface UseWhatsAppWebSocketOptions {
  /** Device ID to connect to */
  deviceId: string;
  /** Whether the connection is enabled */
  enabled?: boolean;
  /** Callback when a message is received */
  onMessage?: (message: WhatsAppWebSocketMessage) => void;
  /** Callback when connection is established */
  onConnect?: () => void;
  /** Callback when connection is closed */
  onDisconnect?: () => void;
  /** Callback when an error occurs */
  onError?: (error: Event) => void;
  /** Whether to automatically reconnect on disconnect */
  autoReconnect?: boolean;
  /** Base interval between reconnection attempts (ms) */
  reconnectInterval?: number;
  /** Maximum number of automatic reconnection attempts */
  maxReconnectAttempts?: number;
  /** Interval between ping messages (ms) */
  pingInterval?: number;
}

/**
 * WhatsApp-specific WebSocket hook.
 *
 * Wraps the generic useWebSocket hook with WhatsApp-specific URL building
 * and message typing.
 *
 * @example
 * ```tsx
 * const { isConnected, lastMessage } = useWhatsAppWebSocket({
 *   deviceId: 'device-uuid',
 *   onMessage: (msg) => {
 *     if (msg.type === 'new_message') {
 *       console.log('New message:', msg.data?.body);
 *     }
 *   },
 * });
 * ```
 */
export function useWhatsAppWebSocket(options: UseWhatsAppWebSocketOptions) {
  const {
    deviceId,
    enabled = true,
    onMessage,
    onConnect,
    onDisconnect,
    onError,
    autoReconnect = true,
    reconnectInterval = 5000,
    maxReconnectAttempts = 5,
    pingInterval = 30000,
  } = options;

  const { user, idToken } = useAuth();

  // AuthContext versions idToken on every Firebase refresh. Depending on that
  // value rebuilds the socket URL without reading a second global token source.
  const wsUrl = useMemo(() => {
    if (!idToken || !deviceId) return null;

    return buildWebSocketUrl(API_BASE_URL, `/whatsapp/devices/${deviceId}/ws`, {
      token: idToken,
    });
  }, [idToken, deviceId]);

  // Use the generic WebSocket hook
  const ws = useWebSocket<WhatsAppMessageData>({
    url: wsUrl,
    enabled: enabled && !!deviceId && !!user,
    name: "WhatsApp WS",
    autoReconnect,
    reconnectInterval,
    maxReconnectAttempts,
    pingInterval,
    onMessage: onMessage as (
      message: WebSocketMessage<WhatsAppMessageData>,
    ) => void,
    onConnect,
    onDisconnect,
    onError,
  });

  return {
    ...ws,
    // Expose lastMessage with proper typing
    lastMessage: ws.lastMessage as WhatsAppWebSocketMessage | null,
  };
}

// Re-export types for convenience
export type { WebSocketStatus } from "@/tools/hooks/useWebSocket";
