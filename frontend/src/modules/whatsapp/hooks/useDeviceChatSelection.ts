"use client";

import { useCallback, useState } from "react";
import type { ChatSummary } from "@/modules/whatsapp/types";

/** Keeps device-scoped chat UI state from leaking between devices. */
export function useDeviceChatSelection() {
  const [selectedDeviceId, setSelectedDeviceId] = useState("");
  const [selectedChat, setSelectedChat] = useState<ChatSummary | null>(null);
  const [messageText, setMessageText] = useState("");
  const [newMessageAlert, setNewMessageAlert] = useState(false);

  const changeDevice = useCallback((deviceId: string) => {
    setSelectedDeviceId(deviceId);
    setSelectedChat(null);
    setMessageText("");
    setNewMessageAlert(false);
  }, []);

  return {
    selectedDeviceId,
    selectedChat,
    messageText,
    newMessageAlert,
    changeDevice,
    setSelectedChat,
    setMessageText,
    setNewMessageAlert,
  };
}