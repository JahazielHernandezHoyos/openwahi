import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const authState = vi.hoisted(() => ({
  user: { uid: "user-1" },
  idToken: "token-old" as string | null,
}));
const useWebSocketMock = vi.hoisted(() => vi.fn((_options: { url: string | null }) => ({
  status: "disconnected",
  isConnected: false,
  lastMessage: null,
})));

vi.mock("@/context/AuthContext", () => ({ useAuth: () => authState }));
vi.mock("@/tools/hooks/useWebSocket", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/tools/hooks/useWebSocket")>();
  return { ...original, useWebSocket: useWebSocketMock };
});

import { useWhatsAppWebSocket } from "@/modules/whatsapp/hooks/useWhatsAppWebSocket";

describe("useWhatsAppWebSocket token renewal", () => {
  beforeEach(() => {
    authState.idToken = "token-old";
    useWebSocketMock.mockClear();
  });

  it("rebuilds its URL from the refreshed ID token", () => {
    const { rerender } = renderHook(() =>
      useWhatsAppWebSocket({ deviceId: "device-1" }),
    );

    expect(useWebSocketMock.mock.lastCall?.[0].url).toContain("token=token-old");

    authState.idToken = "token-new";
    rerender();

    expect(useWebSocketMock.mock.lastCall?.[0].url).toContain("token=token-new");
  });
});
