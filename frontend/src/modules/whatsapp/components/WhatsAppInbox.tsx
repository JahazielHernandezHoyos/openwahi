"use client";

import { useEffect, useState } from "react";
import { useWhatsAppMessages } from "../hooks/useWhatsAppMessages";
import { useWhatsAppWebSocket } from "../hooks/useWhatsAppWebSocket";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Inbox,
  MessageSquare,
  RefreshCw,
  ArrowDownRight,
  ArrowUpRight,
  Wifi,
  WifiOff,
} from "lucide-react";
import { useTranslations } from "next-intl";

interface WhatsAppInboxProps {
  deviceId: string | null;
  onDeviceStatusChange?: () => void;
}

export function WhatsAppInbox({ deviceId, onDeviceStatusChange }: WhatsAppInboxProps) {
  const t = useTranslations("WhatsApp.inbox");
  const { messages, total, loading, error, refetch } =
    useWhatsAppMessages(deviceId);
  const [realtimeEnabled, setRealtimeEnabled] = useState(true);

  // WebSocket connection for real-time updates
  const {
    status: wsStatus,
    isConnected: wsConnected,
    messageCount: wsMessageCount,
    reconnect: wsReconnect,
  } = useWhatsAppWebSocket({
    deviceId: deviceId || "",
    enabled: !!deviceId && realtimeEnabled,
    onMessage: (message) => {
      // Handle different message types
      if (message.type === "new_message") {
        // Refetch messages to update the list
        refetch();
      } else if (message.type === "message_sent") {
        // Refetch when a message is sent to show it in the list
        refetch();
      } else if (message.type === "message_ack") {
        // Refetch to update message status
        refetch();
      } else if (message.type === "device_status") {
        // Invalidate devices cache to reflect status change
        onDeviceStatusChange?.();
      }
    },
  });

  // Show connection status on mount/change
  useEffect(() => {
    // Silenced
  }, [wsConnected, deviceId]);

  if (!deviceId) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="text-center py-8 text-muted-foreground">
            <Inbox className="h-12 w-12 mx-auto mb-2 opacity-50" />
            <p>{t("selectDevice")}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Inbox className="h-5 w-5" />
            {t("title")}
            {total > 0 && <Badge variant="secondary">{total}</Badge>}
          </CardTitle>
          <div className="flex items-center gap-2">
            {/* WebSocket status indicator */}
            {deviceId && (
              <div className="flex items-center gap-1 text-xs">
                {wsConnected ? (
                  <>
                    <Wifi className="h-4 w-4 text-green-500" />
                    <span className="text-green-600 font-medium">{t("live")}</span>
                  </>
                ) : wsStatus === "connecting" ? (
                  <>
                    <Wifi className="h-4 w-4 text-yellow-500 animate-pulse" />
                    <span className="text-yellow-600">{t("connecting")}</span>
                  </>
                ) : (
                  <>
                    <WifiOff className="h-4 w-4 text-gray-400" />
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => wsReconnect()}
                      className="h-6 px-2 text-xs"
                    >
                      {t("reconnect")}
                    </Button>
                  </>
                )}
              </div>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => refetch()}
              disabled={loading}
            >
              <RefreshCw
                className={`h-4 w-4 ${loading ? "animate-spin" : ""}`}
              />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {loading && messages.length === 0 && (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        )}

        {error && <p className="text-destructive text-center py-4">{error}</p>}

        {!loading && messages.length === 0 && (
          <div className="text-center py-8 text-muted-foreground">
            <MessageSquare className="h-12 w-12 mx-auto mb-2 opacity-50" />
            <p>{t("noMessages")}</p>
            <p className="text-sm">
              {t("noMessagesDesc")}
            </p>
            {wsConnected && (
              <div className="mt-4 flex items-center justify-center gap-2 text-xs text-green-600">
                <Wifi className="h-3 w-3" />
                <span>{t("realtimeActive")}</span>
              </div>
            )}
          </div>
        )}

        {messages.length > 0 && (
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`p-3 border rounded-lg ${msg.is_from_me
                    ? "bg-primary/5 border-primary/20"
                    : "bg-muted/50"
                  }`}
              >
                <div className="flex justify-between items-start mb-1">
                  <div className="flex items-center gap-2">
                    {msg.is_from_me ? (
                      <ArrowUpRight className="h-4 w-4 text-primary" />
                    ) : (
                      <ArrowDownRight className="h-4 w-4 text-green-500" />
                    )}
                    <span className="font-medium text-sm">
                      {msg.is_from_me
                        ? `${t("to")}: +${msg.to_phone}`
                        : `${t("from")}: +${msg.from_phone}`}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={msg.is_from_me ? "secondary" : "default"}>
                      {msg.is_from_me ? t("sent") : t("received")}
                    </Badge>
                    {msg.status && msg.status !== "received" && (
                      <Badge variant="outline" className="text-xs">
                        {msg.status}
                      </Badge>
                    )}
                  </div>
                </div>

                {msg.body && (
                  <p className="text-sm text-foreground mt-2 whitespace-pre-wrap">
                    {msg.body}
                  </p>
                )}

                {msg.message_type !== "text" && (
                  <Badge
                    variant="outline"
                    className={`mt-2 text-xs ${
                      msg.message_type === "audio_transcribed"
                        ? "border-blue-400 text-blue-600 bg-blue-50"
                        : ""
                    }`}
                  >
                    {msg.message_type === "audio_transcribed"
                      ? t("audioTranscribed")
                      : msg.message_type}
                  </Badge>
                )}

                <p className="text-xs text-muted-foreground mt-2">
                  {new Date(msg.timestamp).toLocaleString("es-ES", {
                    dateStyle: "short",
                    timeStyle: "short",
                  })}
                </p>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
