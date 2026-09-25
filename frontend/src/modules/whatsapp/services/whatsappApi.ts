/**
 * WhatsApp API service
 */
import { apiClient } from "@/tools/api/client";
import {
  DeviceListResponse,
  DeviceCreateRequest,
  DeviceCreateResponse,
  WhatsAppDevice,
  QRCodeResponse,
  DeviceStatusResponse,
  SendMessageRequest,
  SendMessageResponse,
  MessageListResponse,
  ChatListResponse,
} from "../types";

export const whatsappApi = {
  // ==================== Device Operations ====================

  /**
   * List all WhatsApp devices for current user
   */
  async getDevices(): Promise<DeviceListResponse> {
    const response =
      await apiClient.get<DeviceListResponse>("/whatsapp/devices");
    return response.data;
  },

  /**
   * Create a new device and start linking (get QR)
   */
  async createDevice(
    data?: DeviceCreateRequest,
  ): Promise<DeviceCreateResponse> {
    const response = await apiClient.post<DeviceCreateResponse>(
      "/whatsapp/devices",
      data || {},
    );
    return response.data;
  },

  /**
   * Get a specific device
   */
  async getDevice(deviceId: string): Promise<WhatsAppDevice> {
    const response = await apiClient.get<WhatsAppDevice>(
      `/whatsapp/devices/${deviceId}`,
    );
    return response.data;
  },

  /**
   * Delete/unlink a device
   */
  async deleteDevice(deviceId: string): Promise<void> {
    await apiClient.delete(`/whatsapp/devices/${deviceId}`);
  },

  /**
   * Get QR code for a device (for re-scanning)
   */
  async getDeviceQR(deviceId: string): Promise<QRCodeResponse> {
    const response = await apiClient.get<QRCodeResponse>(
      `/whatsapp/devices/${deviceId}/qr`,
    );
    return response.data;
  },

  /**
   * Get device connection status
   */
  async getDeviceStatus(deviceId: string): Promise<DeviceStatusResponse> {
    const response = await apiClient.get<DeviceStatusResponse>(
      `/whatsapp/devices/${deviceId}/status`,
    );
    return response.data;
  },

  // ==================== Message Operations ====================

  /**
   * Send a message using a specific device
   */
  async sendMessage(
    deviceId: string,
    data: SendMessageRequest,
  ): Promise<SendMessageResponse> {
    const response = await apiClient.post<SendMessageResponse>(
      `/whatsapp/devices/${deviceId}/send`,
      data,
    );
    return response.data;
  },

  /**
   * Get messages for a device
   */
  async getMessages(
    deviceId: string,
    limit = 50,
    offset = 0,
  ): Promise<MessageListResponse> {
    const response = await apiClient.get<MessageListResponse>(
      `/whatsapp/devices/${deviceId}/messages`,
      {
        params: { limit, offset },
      },
    );
    return response.data;
  },

  // ==================== Chat Operations ====================

  /**
   * Get all chats (conversations) for the user
   */
  async getChats(deviceId?: string): Promise<ChatListResponse> {
    const response = await apiClient.get<ChatListResponse>("/whatsapp/chats", {
      params: deviceId ? { device_id: deviceId } : undefined,
    });
    return response.data;
  },

  /**
   * Get messages for a specific chat (conversation with a phone number)
   */
  async getChatMessages(
    phone: string,
    deviceId: string,
    limit = 50,
    offset = 0,
  ): Promise<MessageListResponse> {
    const response = await apiClient.get<MessageListResponse>(
      `/whatsapp/chats/${phone}/messages`,
      {
        params: { device_id: deviceId, limit, offset },
      },
    );
    return response.data;
  },
};
