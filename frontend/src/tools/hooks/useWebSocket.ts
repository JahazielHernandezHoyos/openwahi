'use client';

import { useEffect, useRef, useState, useCallback } from 'react';

const STABLE_CONNECTION_MS = 10_000;

export interface WebSocketMessage<T = unknown> {
  type: string;
  room_id?: string;
  data?: T;
  status?: string;
  message?: string;
  timestamp?: string;
}

export type WebSocketStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

export interface UseWebSocketOptions<T = unknown> {
  url: string | null;
  enabled?: boolean;
  onMessage?: (message: WebSocketMessage<T>) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
  autoReconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  pingInterval?: number;
  name?: string;
}

export interface UseWebSocketReturn<T = unknown> {
  status: WebSocketStatus;
  isConnected: boolean;
  isConnecting: boolean;
  isDisconnected: boolean;
  lastMessage: WebSocketMessage<T> | null;
  messageCount: number;
  connect: () => void;
  disconnect: () => void;
  reconnect: () => void;
  send: (data: unknown) => boolean;
}

/** Generic WebSocket hook with bounded reconnects and URL-based rebuilding. */
export function useWebSocket<T = unknown>(
  options: UseWebSocketOptions<T>,
): UseWebSocketReturn<T> {
  const {
    url,
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

  const wsRef = useRef<WebSocket | null>(null);
  const terminalReconnectRef = useRef(false);
  const reconnectPendingRef = useRef(false);
  const callbacksRef = useRef({ onMessage, onConnect, onDisconnect, onError });
  const [manualEnabled, setManualEnabled] = useState(true);
  const [connectionEpoch, setConnectionEpoch] = useState(0);
  const [status, setStatus] = useState<WebSocketStatus>('disconnected');
  const [lastMessage, setLastMessage] = useState<WebSocketMessage<T> | null>(null);
  const [messageCount, setMessageCount] = useState(0);

  useEffect(() => {
    callbacksRef.current = { onMessage, onConnect, onDisconnect, onError };
  }, [onMessage, onConnect, onDisconnect, onError]);

  useEffect(() => {
    if (!enabled || !manualEnabled || !url) {
      wsRef.current = null;
      setStatus('disconnected');
      return;
    }

    let cancelled = false;
    let reconnectAttempts = 0;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let stableConnectionTimer: ReturnType<typeof setTimeout> | null = null;
    let pingTimer: ReturnType<typeof setInterval> | null = null;

    const clearTimers = () => {
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (stableConnectionTimer) clearTimeout(stableConnectionTimer);
      if (pingTimer) clearInterval(pingTimer);
      reconnectTimer = null;
      reconnectPendingRef.current = false;
      stableConnectionTimer = null;
      pingTimer = null;
    };

    const openSocket = () => {
      if (cancelled) return;
      reconnectPendingRef.current = false;
      setStatus('connecting');

      try {
        const socket = new WebSocket(url);
        wsRef.current = socket;

        socket.onopen = () => {
          if (cancelled) return;
          setStatus('connected');
          stableConnectionTimer = setTimeout(() => {
            reconnectAttempts = 0;
            stableConnectionTimer = null;
          }, STABLE_CONNECTION_MS);
          pingTimer = setInterval(() => {
            if (socket.readyState === WebSocket.OPEN) {
              socket.send(JSON.stringify({ type: 'ping' }));
            }
          }, pingInterval);
          callbacksRef.current.onConnect?.();
        };

        socket.onmessage = (event) => {
          try {
            const message: WebSocketMessage<T> = JSON.parse(event.data);
            reconnectAttempts = 0;
            if (message.type !== 'pong') {
              setLastMessage(message);
              setMessageCount((count) => count + 1);
              callbacksRef.current.onMessage?.(message);
            }
          } catch {
            // Ignore malformed frames; a later valid frame can still be processed.
          }
        };

        socket.onerror = (error) => {
          if (cancelled) return;
          setStatus('error');
          callbacksRef.current.onError?.(error);
        };

        socket.onclose = (event) => {
          if (cancelled) return;
          clearTimers();
          wsRef.current = null;
          setStatus('disconnected');
          callbacksRef.current.onDisconnect?.();

          if (event.code === 1008) {
            terminalReconnectRef.current = true;
            return;
          }
          if (!autoReconnect) return;
          if (reconnectAttempts >= maxReconnectAttempts) {
            terminalReconnectRef.current = true;
            return;
          }

          reconnectAttempts += 1;
          const delay = Math.min(reconnectInterval * reconnectAttempts, 30000);
          reconnectPendingRef.current = true;
          reconnectTimer = setTimeout(openSocket, delay);
        };
      } catch {
        setStatus('error');
      }
    };

    openSocket();

    return () => {
      cancelled = true;
      clearTimers();
      const socket = wsRef.current;
      if (socket) {
        socket.onopen = null;
        socket.onmessage = null;
        socket.onerror = null;
        socket.onclose = null;
        if (
          socket.readyState === WebSocket.OPEN ||
          socket.readyState === WebSocket.CONNECTING
        ) {
          socket.close();
        }
      }
      wsRef.current = null;
    };
  }, [
    autoReconnect,
    connectionEpoch,
    enabled,
    manualEnabled,
    maxReconnectAttempts,
    pingInterval,
    reconnectInterval,
    url,
  ]);

  const connect = useCallback(() => {
    terminalReconnectRef.current = false;
    setManualEnabled(true);
    setConnectionEpoch((epoch) => epoch + 1);
  }, []);

  const disconnect = useCallback(() => {
    setManualEnabled(false);
    setStatus('disconnected');
  }, []);

  const reconnect = useCallback(() => {
    terminalReconnectRef.current = false;
    setManualEnabled(true);
    setConnectionEpoch((epoch) => epoch + 1);
  }, []);

  const send = useCallback((data: unknown): boolean => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) return false;
    try {
      wsRef.current.send(JSON.stringify(data));
      return true;
    } catch {
      return false;
    }
  }, []);

  useEffect(() => {
    const handleVisibilityChange = () => {
      if (
        document.visibilityState === 'visible' &&
        enabled &&
        autoReconnect &&
        manualEnabled &&
        url &&
        status === 'disconnected' &&
        !terminalReconnectRef.current &&
        !reconnectPendingRef.current
      ) {
        const socketState = wsRef.current?.readyState;
        if (
          socketState === WebSocket.OPEN ||
          socketState === WebSocket.CONNECTING ||
          socketState === WebSocket.CLOSING
        ) {
          return;
        }
        setManualEnabled(true);
        setConnectionEpoch((epoch) => epoch + 1);
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () =>
      document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, [autoReconnect, enabled, manualEnabled, status, url]);

  return {
    status,
    isConnected: status === 'connected',
    isConnecting: status === 'connecting',
    isDisconnected: status === 'disconnected',
    lastMessage,
    messageCount,
    connect,
    disconnect,
    reconnect,
    send,
  };
}

export function buildWebSocketUrl(
  apiBaseUrl: string,
  path: string,
  params?: Record<string, string>,
): string {
  const wsProtocol =
    typeof window !== 'undefined' && window.location.protocol === 'https:'
      ? 'wss:'
      : 'ws:';
  const wsBaseUrl = apiBaseUrl.replace(/^https?:/, wsProtocol);
  let result = `${wsBaseUrl}${path}`;

  if (params && Object.keys(params).length > 0) {
    const searchParams = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      searchParams.append(key, value);
    }
    result += `?${searchParams.toString()}`;
  }

  return result;
}
