"use client";

import { useState, useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Header } from "@/components/layout/Header";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  MessageSquare,
  Smartphone,
  Send,
  RefreshCw,
  ArrowLeft,
  Clock,
  Loader2,
} from "lucide-react";
import { useWhatsAppDevices } from "@/modules/whatsapp/hooks/useWhatsAppDevices";
import {
  useWhatsAppChats,
  useWhatsAppChatMessages,
} from "@/modules/whatsapp/hooks/useWhatsAppChats";
import { useWhatsAppWebSocket } from "@/modules/whatsapp/hooks/useWhatsAppWebSocket";
import { useDeviceChatSelection } from "@/modules/whatsapp/hooks/useDeviceChatSelection";
import { whatsappApi } from "@/modules/whatsapp/services/whatsappApi";
import { formatDistanceToNow } from "date-fns";
import { es, enUS } from "date-fns/locale";

import { useToast } from "@/hooks/use-toast";
import { useTranslations, useLocale } from "next-intl";

function getMessageTypeLabel(messageType: string, t: ReturnType<typeof useTranslations>): string {
  const map: Record<string, string> = {
    audio: t("typeAudio"),
    audio_transcribed: t("typeAudioTranscribed"),
    ptt: t("typeAudio"),
    voice: t("typeAudio"),
    image: t("typeImage"),
    video: t("typeVideo"),
    document: t("typeDocument"),
    sticker: t("typeSticker"),
  };
  return map[messageType] ?? messageType;
}

export default function WhatsAppChatsPage() {
  const t = useTranslations("WhatsAppChats");
  const locale = useLocale();
  const {
    selectedDeviceId,
    selectedChat,
    messageText,
    newMessageAlert,
    changeDevice,
    setSelectedChat,
    setMessageText,
    setNewMessageAlert,
  } = useDeviceChatSelection();
  const [isSending, setIsSending] = useState(false);
  const { toast } = useToast();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();

  const { devices, loading: devicesLoading } = useWhatsAppDevices();

  // Connect to WebSocket first so wsConnected is available for the polling hooks below
  const { lastMessage, isConnected: wsConnected } = useWhatsAppWebSocket({
    deviceId: selectedDeviceId || "",
    enabled: !!selectedDeviceId,
    onMessage: (message) => {
      // Handle new messages
      if (message.type === "new_message" || message.type === "message_sent") {
        // Extract phone numbers from message
        const fromPhone = message.data?.from_phone || message.data?.from || "";
        const toPhone = message.data?.to_phone || message.data?.to || "";

        // Clean phone numbers (remove @s.whatsapp.net)
        const cleanFromPhone = fromPhone
          .replace(/@s\.whatsapp\.net/g, "")
          .replace(/@c\.us/g, "");
        const cleanToPhone = toPhone
          .replace(/@s\.whatsapp\.net/g, "")
          .replace(/@c\.us/g, "");

        // Check if message is for current chat
        // The "other" party is from if not from me, else to
        const isFromMe = message.data?.is_from_me || false;
        const otherPartyPhone = isFromMe ? cleanToPhone : cleanFromPhone;

        const isForCurrentChat =
          selectedChat &&
          otherPartyPhone &&
          (otherPartyPhone === selectedChat.phone ||
            otherPartyPhone.endsWith(selectedChat.phone) ||
            selectedChat.phone.endsWith(otherPartyPhone));

        if (isForCurrentChat) {
          // Invalidate queries to trigger a refetch
          // Use partial matching to invalidate all queries for this chat
          queryClient.invalidateQueries({
            queryKey: ["whatsapp-chat-messages", selectedChat.phone, selectedChat.device_id],
            refetchType: 'active',
          });

          // Trigger immediate refetch
          refetchMessages();

          // Show new message alert
          setNewMessageAlert(true);
          setTimeout(() => setNewMessageAlert(false), 3000);
        } else {
          // Show toast for new message in other chat
          if (otherPartyPhone) {
            toast({
              title: t("newMessage"),
              description: t("messageFrom", {
                name: formatPhone(otherPartyPhone),
              }),
              duration: 3000,
            });
          }
        }

        // Always refresh chat list to update last message and timestamps
        queryClient.invalidateQueries({
          queryKey: ["whatsapp-chats", selectedDeviceId],
          refetchType: 'active',
        });
      }

      // Handle message status updates (sent, delivered, read)
      if (message.type === "message_ack") {
        // Only refresh if we're viewing messages
        if (selectedChat) {
          queryClient.invalidateQueries({
            queryKey: ["whatsapp-chat-messages", selectedChat.phone, selectedChat.device_id],
            refetchType: 'active',
          });
          refetchMessages();
        }
      }
    },
    autoReconnect: true,
    reconnectInterval: 3000,
    pingInterval: 30000,
  });

  const {
    chats,
    loading: chatsLoading,
    refetch: refetchChats,
  } = useWhatsAppChats(selectedDeviceId || undefined, wsConnected);

  const {
    messages,
    loading: messagesLoading,
    refetch: refetchMessages,
  } = useWhatsAppChatMessages(
    selectedChat?.phone || null,
    selectedChat?.device_id || null,
    wsConnected,
  );

  // Watch for lastMessage changes and trigger refetch
  useEffect(() => {
    if (!lastMessage || !selectedChat) return;

    // If it's a new message, refetch
    if (lastMessage.type === "new_message" || lastMessage.type === "message_sent") {
      // Invalidate and refetch messages
      queryClient.invalidateQueries({
        queryKey: ["whatsapp-chat-messages", selectedChat.phone, selectedChat.device_id],
        refetchType: 'active',
      });

      // Invalidate and refetch chats
      queryClient.invalidateQueries({
        queryKey: ["whatsapp-chats", selectedDeviceId],
        refetchType: 'active',
      });
    }
  }, [lastMessage, selectedChat, selectedDeviceId, queryClient]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (messages.length > 0) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  // Auto-select first connected device
  const connectedDevices = devices.filter((d) => d.status === "connected");
  const hasConnectedDevice = connectedDevices.length > 0;

  useEffect(() => {
    if (!selectedDeviceId && connectedDevices.length > 0) {
      changeDevice(connectedDevices[0].id);
    }
  }, [changeDevice, connectedDevices, selectedDeviceId]);

  const formatPhone = (phone: string) => {
    // Format phone number for display
    if (phone.startsWith("57")) {
      return `+${phone.slice(0, 2)} ${phone.slice(2)}`;
    }
    return `+${phone}`;
  };

  const formatTimestamp = (timestamp?: string) => {
    if (!timestamp) return "";
    try {
      return formatDistanceToNow(new Date(timestamp), {
        addSuffix: true,
        locale: locale === "es" ? es : enUS,
      });
    } catch {
      return "";
    }
  };

  const handleSendMessage = async () => {
    if (!messageText.trim() || !selectedChat || !selectedDeviceId) return;

    setIsSending(true);
    try {
      await whatsappApi.sendMessage(selectedDeviceId, {
        phone: selectedChat.phone,
        message: messageText,
      });

      // Clear input
      setMessageText("");

      // Immediately invalidate and refresh
      queryClient.invalidateQueries({
        queryKey: ["whatsapp-chat-messages", selectedChat.phone, selectedChat.device_id],
        refetchType: 'active',
      });
      queryClient.invalidateQueries({
        queryKey: ["whatsapp-chats", selectedDeviceId],
        refetchType: 'active',
      });

      // Trigger refetch
      refetchMessages();
      refetchChats();

      toast({
        title: t("messageSent"),
        description: t("messageSentDesc"),
      });
    } catch (error) {
      toast({
        title: t("error"),
        description: t("errorSending"),
        variant: "destructive",
      });
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="min-h-screen overflow-x-hidden bg-background">
      <Header />

      <div className="max-w-7xl min-w-0 mx-auto px-4 py-6 sm:py-8">
        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between mb-6">
          <div className="flex min-w-0 items-center gap-3">
            <MessageSquare className="h-8 w-8 text-green-500" />
            <div className="min-w-0">
              <h1 className="text-2xl sm:text-3xl font-bold break-words" suppressHydrationWarning>
                {t("title")}
              </h1>
              <p className="text-muted-foreground" suppressHydrationWarning>
                {t("description")}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Button variant="outline" onClick={() => {
              refetchChats();
            }} size="sm">
              <RefreshCw className="h-4 w-4 mr-2" />
              {t("update")}
            </Button>
            {wsConnected && selectedDeviceId && (
              <Badge
                variant="outline"
                className="text-green-600 border-green-600"
              >
                <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse mr-2" />
                {t("realtime")}
              </Badge>
            )}
          </div>
        </div>

        {/* Device Selector */}
        {hasConnectedDevice && (
          <Card className="mb-6">
            <CardContent className="pt-6">
              <div className="flex min-w-0 items-center gap-4">
                <Smartphone className="h-5 w-5 text-muted-foreground" />
                <Select
                  value={selectedDeviceId}
                  onValueChange={changeDevice}
                >
                  <SelectTrigger className="min-w-0 w-full sm:w-[300px]">
                    <SelectValue placeholder={t("selectDevice")} />
                  </SelectTrigger>
                  <SelectContent>
                    {connectedDevices.map((device) => (
                      <SelectItem key={device.id} value={device.id}>
                        {device.phone
                          ? formatPhone(device.phone)
                          : device.name || "Sin nombre"}{" "}
                        {device.name && device.phone && `(${device.name})`}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>
        )}

        {/* No Connected Devices */}
        {!hasConnectedDevice && !devicesLoading && (
          <Card>
            <CardContent className="pt-6">
              <div className="text-center py-12">
                <Smartphone className="h-16 w-16 mx-auto mb-4 opacity-30" />
                <h3 className="text-lg font-medium mb-2">{t("noDevices")}</h3>
                <p className="text-sm text-muted-foreground mb-4">
                  {t("noDevicesDesc")}
                </p>
                <Button
                  onClick={() => (window.location.href = "/whatsapp-devices")}
                >
                  <Smartphone className="h-4 w-4 mr-2" />
                  {t("goToDevices")}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Chats Layout */}
        {hasConnectedDevice && selectedDeviceId && (
          <div className="grid min-w-0 lg:grid-cols-3 gap-6">
            {/* Chat List */}
            <Card className={`min-w-0 lg:col-span-1 ${selectedChat ? "hidden lg:block" : ""}`}>
              <CardHeader>
                <CardTitle
                  className="flex items-center gap-2"
                  suppressHydrationWarning
                >
                  <MessageSquare className="h-5 w-5" />
                  {t("conversations")}
                </CardTitle>
                <CardDescription suppressHydrationWarning>
                  {t("conversationsCount", { count: chats.length })}
                </CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                <ScrollArea className="h-[600px]">
                  {chatsLoading && (
                    <div className="p-4 space-y-3">
                      <Skeleton className="h-20 w-full" />
                      <Skeleton className="h-20 w-full" />
                      <Skeleton className="h-20 w-full" />
                    </div>
                  )}

                  {!chatsLoading && chats.length === 0 && (
                    <div className="p-8 text-center text-muted-foreground">
                      <MessageSquare className="h-12 w-12 mx-auto mb-2 opacity-30" />
                      <p className="text-sm">{t("noConversations")}</p>
                    </div>
                  )}

                  {!chatsLoading &&
                    chats.map((chat) => (
                      <div
                        key={chat.phone}
                        className={`p-4 border-b cursor-pointer hover:bg-muted/50 transition-colors ${selectedChat?.phone === chat.phone
                          ? "bg-muted border-l-4 border-l-primary"
                          : ""
                          }`}
                        onClick={() => {
                          setSelectedChat(chat);
                        }}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <p className="font-semibold text-sm truncate">
                                {formatPhone(chat.phone)}
                              </p>
                              {chat.unread_count > 0 && (
                                <Badge
                                  variant="default"
                                  className="h-5 px-2 text-xs"
                                >
                                  {chat.unread_count}
                                </Badge>
                              )}
                            </div>
                                 <p className="text-xs text-muted-foreground truncate">
                                              {chat.is_last_from_me && t("you")}
                                              {chat.last_message
                                                ? chat.last_message
                                                : chat.last_message_type && chat.last_message_type !== "text"
                                                  ? `[${getMessageTypeLabel(chat.last_message_type, t)}]`
                                                  : `[${t("noConversations")}]`}
                                            </p>
                            <div className="flex items-center gap-1 mt-1">
                              <Clock className="h-3 w-3 text-muted-foreground" />
                              <p className="text-xs text-muted-foreground">
                                {formatTimestamp(chat.last_message_timestamp)}
                              </p>
                            </div>
                          </div>
                          <Badge variant="outline" className="text-xs">
                            {chat.total_messages}
                          </Badge>
                        </div>
                      </div>
                    ))}
                </ScrollArea>
              </CardContent>
            </Card>

            {/* Messages View */}
            <Card className={`min-w-0 lg:col-span-2 ${selectedChat ? "" : "hidden lg:block"}`}>
              {selectedChat ? (
                <>
                  <CardHeader className="border-b">
                    <div className="flex min-w-0 items-center justify-between gap-2">
                      <div className="flex min-w-0 items-center gap-2 sm:gap-3">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="lg:hidden"
                          onClick={() => setSelectedChat(null)}
                        >
                          <ArrowLeft className="h-5 w-5" />
                        </Button>
                        <div className="min-w-0">
                          <CardTitle className="truncate">
                            {formatPhone(selectedChat.phone)}
                          </CardTitle>
                          <CardDescription className="flex flex-wrap items-center gap-2">
                            {t("messages", { count: messages.length })}
                            {wsConnected && (
                              <>
                                <span>•</span>
                                <span className="flex items-center gap-1 text-green-600">
                                  <div className="h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse" />
                                  {t("live")}
                                </span>
                              </>
                            )}
                            {newMessageAlert && (
                              <>
                                <span>•</span>
                                <Badge
                                  variant="default"
                                  className="bg-blue-500 animate-pulse"
                                >
                                  {t("newMessage")}
                                </Badge>
                              </>
                            )}
                          </CardDescription>
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => refetchMessages()}
                      >
                        <RefreshCw className="h-4 w-4" />
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent className="p-0">
                    <ScrollArea className="h-[600px] p-4">
                      {messagesLoading && (
                        <div className="space-y-3">
                          <Skeleton className="h-16 w-3/4" />
                          <Skeleton className="h-16 w-2/3 ml-auto" />
                          <Skeleton className="h-16 w-3/4" />
                        </div>
                      )}

                      {!messagesLoading && messages.length === 0 && (
                        <div className="text-center py-12 text-muted-foreground">
                          <MessageSquare className="h-12 w-12 mx-auto mb-2 opacity-30" />
                          <p>{t("noMessages")}</p>
                        </div>
                      )}

                      <div className="space-y-3">
                        {!messagesLoading &&
                          [...messages].reverse().map((message) => (
                            <div
                              key={message.id}
                              className={`flex ${message.is_from_me
                                ? "justify-end"
                                : "justify-start"
                                }`}
                            >
                              <div
                                className={`max-w-[85%] sm:max-w-[70%] rounded-lg px-4 py-2 ${message.is_from_me
                                  ? "bg-green-500 text-white"
                                  : "bg-muted"
                                  }`}
                              >
                                 <p className="text-sm break-words">
                                                  {message.body || `[${getMessageTypeLabel(message.message_type, t)}]`}
                                                </p>
                                <div
                                  className={`flex items-center gap-1 mt-1 text-xs ${message.is_from_me
                                    ? "text-green-100"
                                    : "text-muted-foreground"
                                    }`}
                                >
                                  <Clock className="h-3 w-3" />
                                  <span>
                                    {new Date(
                                      message.timestamp,
                                    ).toLocaleTimeString(
                                      locale === "es" ? "es-CO" : "en-US",
                                      {
                                        hour: "2-digit",
                                        minute: "2-digit",
                                      },
                                    )}
                                  </span>
                                  {message.is_from_me && (
                                    <span className="ml-1">
                                      {message.status === "read"
                                        ? "✓✓"
                                        : message.status === "delivered"
                                          ? "✓✓"
                                          : "✓"}
                                    </span>
                                  )}
                                </div>
                              </div>
                            </div>
                          ))}
                        <div ref={messagesEndRef} />
                      </div>
                    </ScrollArea>
                  </CardContent>

                  {/* Message Input */}
                  <div className="border-t p-4">
                    <div className="flex items-center gap-2">
                      <Input
                        placeholder={t("inputPlaceholder")}
                        value={messageText}
                        onChange={(e) => setMessageText(e.target.value)}
                        onKeyPress={handleKeyPress}
                        disabled={isSending}
                        className="flex-1"
                        autoFocus
                      />
                      <Button
                        onClick={handleSendMessage}
                        disabled={isSending || !messageText.trim()}
                        size="icon"
                        className="bg-green-500 hover:bg-green-600"
                      >
                        {isSending ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Send className="h-4 w-4" />
                        )}
                      </Button>
                    </div>
                  </div>
                </>
              ) : (
                <CardContent className="pt-6">
                  <div className="text-center py-24 text-muted-foreground">
                    <Send className="h-16 w-16 mx-auto mb-4 opacity-30" />
                    <h3 className="text-lg font-medium mb-2">
                      {t("selectChat")}
                    </h3>
                    <p className="text-sm">{t("selectChatDesc")}</p>
                  </div>
                </CardContent>
              )}
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
