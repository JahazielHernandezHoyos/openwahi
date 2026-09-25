/**
 * Tests for whatsappApi service
 * Verifies all WhatsApp API endpoints: devices, messages, chats
 */
import { describe, it, expect, beforeEach, vi } from "vitest";

vi.mock("@/tools/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

import { whatsappApi } from "@/modules/whatsapp/services/whatsappApi";
import { apiClient } from "@/tools/api/client";

const mockedClient = vi.mocked(apiClient, { deep: true });

describe("whatsappApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ── Devices ──────────────────────────────────────────────────────

  it("getDevices fetches /whatsapp/devices", async () => {
    const data = { devices: [], total: 0 };
    mockedClient.get.mockResolvedValue({ data });

    const result = await whatsappApi.getDevices();

    expect(mockedClient.get).toHaveBeenCalledWith("/whatsapp/devices");
    expect(result).toEqual(data);
  });

  it("createDevice posts to /whatsapp/devices", async () => {
    const device = { id: "d1", device_id: "dev-1", status: "pending" };
    mockedClient.post.mockResolvedValue({
      data: { device, qr: { device_id: "dev-1", status: "pending" } },
    });

    const result = await whatsappApi.createDevice({ name: "My Phone" });

    expect(mockedClient.post).toHaveBeenCalledWith("/whatsapp/devices", {
      name: "My Phone",
    });
    expect(result.device.id).toBe("d1");
  });

  it("createDevice sends empty object when no data", async () => {
    mockedClient.post.mockResolvedValue({
      data: { device: {}, qr: {} },
    });

    await whatsappApi.createDevice();

    expect(mockedClient.post).toHaveBeenCalledWith("/whatsapp/devices", {});
  });

  it("getDevice fetches /whatsapp/devices/{id}", async () => {
    const device = { id: "d1", device_id: "dev-1", status: "connected" };
    mockedClient.get.mockResolvedValue({ data: device });

    const result = await whatsappApi.getDevice("d1");

    expect(mockedClient.get).toHaveBeenCalledWith("/whatsapp/devices/d1");
    expect(result.status).toBe("connected");
  });

  it("deleteDevice calls DELETE /whatsapp/devices/{id}", async () => {
    mockedClient.delete.mockResolvedValue({});

    await whatsappApi.deleteDevice("d1");

    expect(mockedClient.delete).toHaveBeenCalledWith("/whatsapp/devices/d1");
  });

  it("getDeviceQR fetches QR code endpoint", async () => {
    const qr = { device_id: "d1", qr_code: "base64...", status: "pending" };
    mockedClient.get.mockResolvedValue({ data: qr });

    const result = await whatsappApi.getDeviceQR("d1");

    expect(mockedClient.get).toHaveBeenCalledWith("/whatsapp/devices/d1/qr");
    expect(result.qr_code).toBe("base64...");
  });

  it("getDeviceStatus fetches status endpoint", async () => {
    const status = { device_id: "d1", status: "connected", phone: "+1234" };
    mockedClient.get.mockResolvedValue({ data: status });

    const result = await whatsappApi.getDeviceStatus("d1");

    expect(mockedClient.get).toHaveBeenCalledWith(
      "/whatsapp/devices/d1/status"
    );
    expect(result.status).toBe("connected");
  });

  // ── Messages ─────────────────────────────────────────────────────

  it("sendMessage posts to device send endpoint", async () => {
    const response = { success: true, message_id: "msg-1" };
    mockedClient.post.mockResolvedValue({ data: response });

    const result = await whatsappApi.sendMessage("d1", {
      phone: "+1234567890",
      message: "Hello!",
    });

    expect(mockedClient.post).toHaveBeenCalledWith(
      "/whatsapp/devices/d1/send",
      { phone: "+1234567890", message: "Hello!" }
    );
    expect(result.success).toBe(true);
  });

  it("getMessages fetches with pagination params", async () => {
    const data = { messages: [], total: 0, limit: 20, offset: 10 };
    mockedClient.get.mockResolvedValue({ data });

    const result = await whatsappApi.getMessages("d1", 20, 10);

    expect(mockedClient.get).toHaveBeenCalledWith(
      "/whatsapp/devices/d1/messages",
      { params: { limit: 20, offset: 10 } }
    );
    expect(result).toEqual(data);
  });

  // ── Chats ────────────────────────────────────────────────────────

  it("getChats fetches /whatsapp/chats without device filter", async () => {
    const data = { chats: [], total: 0 };
    mockedClient.get.mockResolvedValue({ data });

    const result = await whatsappApi.getChats();

    expect(mockedClient.get).toHaveBeenCalledWith("/whatsapp/chats", {
      params: undefined,
    });
    expect(result).toEqual(data);
  });

  it("getChats passes device_id filter when provided", async () => {
    const data = { chats: [], total: 0 };
    mockedClient.get.mockResolvedValue({ data });

    await whatsappApi.getChats("d1");

    expect(mockedClient.get).toHaveBeenCalledWith("/whatsapp/chats", {
      params: { device_id: "d1" },
    });
  });

  it("getChatMessages fetches with phone and deviceId", async () => {
    const data = { messages: [], total: 0, limit: 50, offset: 0 };
    mockedClient.get.mockResolvedValue({ data });

    const result = await whatsappApi.getChatMessages("+1234", "d1");

    expect(mockedClient.get).toHaveBeenCalledWith(
      "/whatsapp/chats/+1234/messages",
      { params: { device_id: "d1", limit: 50, offset: 0 } }
    );
    expect(result).toEqual(data);
  });
});
