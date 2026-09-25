/**
 * WhatsApp module types
 */

// Device types
export interface WhatsAppDevice {
  id: string;
  device_id: string;
  phone?: string;
  name?: string;
  status: "pending" | "connected" | "disconnected";
  connected_at?: string;
  created_at?: string;
}

export interface DeviceListResponse {
  devices: WhatsAppDevice[];
  total: number;
}

export interface DeviceCreateRequest {
  name?: string;
}

export interface DeviceCreateResponse {
  device: WhatsAppDevice;
  qr: QRCodeResponse;
}

export interface QRCodeResponse {
  device_id: string;
  qr_code?: string;
  status: string;
  message?: string;
}

export interface DeviceStatusResponse {
  device_id: string;
  status: string;
  phone?: string;
  name?: string;
  connected_at?: string;
}

// Message types
export interface WhatsAppMessage {
  id: string;
  message_id: string;
  from_phone: string;
  to_phone: string;
  body?: string;
  message_type: string;
  is_from_me: boolean;
  status: string;
  media_url?: string;
  timestamp: string;
  created_at?: string;
}

export interface MessageListResponse {
  messages: WhatsAppMessage[];
  total: number;
  limit: number;
  offset: number;
}

export interface SendMessageRequest {
  phone: string;
  message: string;
}

export interface SendMessageResponse {
  success: boolean;
  message_id?: string;
  error?: string;
}

// Chat types
export interface ChatSummary {
  phone: string;
  device_id: string;
  device_phone?: string;
  last_message?: string;
  last_message_type?: string;
  last_message_timestamp?: string;
  unread_count: number;
  total_messages: number;
  is_last_from_me: boolean;
}

export interface ChatListResponse {
  chats: ChatSummary[];
  total: number;
}
