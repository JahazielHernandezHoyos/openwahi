import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useDeviceChatSelection } from "@/modules/whatsapp/hooks/useDeviceChatSelection";
import type { ChatSummary } from "@/modules/whatsapp/types";

const chat: ChatSummary = {
  phone: "15551234567",
  device_id: "device-a",
  last_message: "hello",
  last_message_type: "text",
  last_message_timestamp: new Date().toISOString(),
  is_last_from_me: false,
  unread_count: 0,
  total_messages: 1,
};

describe("useDeviceChatSelection", () => {
  it("clears the chat, message input, and alerts when the device changes", () => {
    const { result } = renderHook(() => useDeviceChatSelection());

    act(() => {
      result.current.changeDevice("device-a");
      result.current.setSelectedChat(chat);
      result.current.setMessageText("draft for device A");
      result.current.setNewMessageAlert(true);
    });

    act(() => result.current.changeDevice("device-b"));

    expect(result.current.selectedDeviceId).toBe("device-b");
    expect(result.current.selectedChat).toBeNull();
    expect(result.current.messageText).toBe("");
    expect(result.current.newMessageAlert).toBe(false);
  });
});
