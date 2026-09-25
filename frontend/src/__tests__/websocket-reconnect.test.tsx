import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useWebSocket } from "@/tools/hooks/useWebSocket";

class MockWebSocket {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;
  static instances: MockWebSocket[] = [];

  readonly url: string;
  readyState = MockWebSocket.CONNECTING;
  onopen: (() => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  send = vi.fn();

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  open() {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.();
  }

  message(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) } as MessageEvent);
  }

  serverClose(code = 1006) {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.({ code } as CloseEvent);
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
  }
}

function showDocument() {
  Object.defineProperty(document, "visibilityState", {
    configurable: true,
    value: "visible",
  });
  document.dispatchEvent(new Event("visibilitychange"));
}

describe("useWebSocket reconnect policy", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    MockWebSocket.instances = [];
    vi.stubGlobal("WebSocket", MockWebSocket);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("reconnects only up to maxReconnectAttempts", () => {
    renderHook(() =>
      useWebSocket({
        url: "ws://example.test/socket",
        reconnectInterval: 10,
        maxReconnectAttempts: 1,
        pingInterval: 60_000,
      }),
    );

    expect(MockWebSocket.instances).toHaveLength(1);
    act(() => MockWebSocket.instances[0].serverClose());
    act(() => vi.advanceTimersByTime(10));
    expect(MockWebSocket.instances).toHaveLength(2);

    act(() => MockWebSocket.instances[1].serverClose());
    act(() => vi.advanceTimersByTime(100));
    expect(MockWebSocket.instances).toHaveLength(2);

    act(showDocument);
    expect(MockWebSocket.instances).toHaveLength(2);
  });

  it("does not reset reconnect attempts for immediately unstable opens", () => {
    renderHook(() =>
      useWebSocket({
        url: "ws://example.test/socket",
        reconnectInterval: 10,
        maxReconnectAttempts: 1,
        pingInterval: 60_000,
      }),
    );

    act(() => {
      MockWebSocket.instances[0].open();
      MockWebSocket.instances[0].serverClose();
      vi.advanceTimersByTime(10);
      MockWebSocket.instances[1].open();
      MockWebSocket.instances[1].serverClose();
      vi.advanceTimersByTime(100);
    });

    expect(MockWebSocket.instances).toHaveLength(2);
  });

  it("resets reconnect attempts after a valid message", () => {
    renderHook(() =>
      useWebSocket({
        url: "ws://example.test/socket",
        reconnectInterval: 10,
        maxReconnectAttempts: 1,
        pingInterval: 60_000,
      }),
    );

    act(() => {
      MockWebSocket.instances[0].serverClose();
      vi.advanceTimersByTime(10);
      MockWebSocket.instances[1].open();
      MockWebSocket.instances[1].message({ type: "pong" });
      MockWebSocket.instances[1].serverClose();
      vi.advanceTimersByTime(10);
    });

    expect(MockWebSocket.instances).toHaveLength(3);
  });

  it("resets reconnect attempts after the connection stays stable", () => {
    renderHook(() =>
      useWebSocket({
        url: "ws://example.test/socket",
        reconnectInterval: 10,
        maxReconnectAttempts: 1,
        pingInterval: 60_000,
      }),
    );

    act(() => {
      MockWebSocket.instances[0].serverClose();
      vi.advanceTimersByTime(10);
      MockWebSocket.instances[1].open();
      vi.advanceTimersByTime(10_000);
      MockWebSocket.instances[1].serverClose();
      vi.advanceTimersByTime(10);
    });

    expect(MockWebSocket.instances).toHaveLength(3);
  });

  it("does not reconnect on visibility change when autoReconnect is false", () => {
    renderHook(() =>
      useWebSocket({
        url: "ws://example.test/socket",
        autoReconnect: false,
      }),
    );

    act(() => MockWebSocket.instances[0].serverClose());
    act(showDocument);

    expect(MockWebSocket.instances).toHaveLength(1);
  });

  it("keeps a manual disconnect disabled across visibility changes", () => {
    const { result } = renderHook(() =>
      useWebSocket({ url: "ws://example.test/socket" }),
    );

    act(() => result.current.disconnect());
    act(showDocument);

    expect(MockWebSocket.instances).toHaveLength(1);
    expect(result.current.status).toBe("disconnected");
  });

  it("does not reset failures or duplicate a pending reconnect on visibility change", () => {
    renderHook(() =>
      useWebSocket({
        url: "ws://example.test/socket",
        reconnectInterval: 10,
        maxReconnectAttempts: 2,
        pingInterval: 60_000,
      }),
    );

    act(() => MockWebSocket.instances[0].serverClose());
    act(showDocument);
    act(showDocument);
    expect(MockWebSocket.instances).toHaveLength(1);

    act(() => vi.advanceTimersByTime(10));
    expect(MockWebSocket.instances).toHaveLength(2);

    act(() => MockWebSocket.instances[1].serverClose());
    act(showDocument);
    expect(MockWebSocket.instances).toHaveLength(2);

    act(() => vi.advanceTimersByTime(20));
    expect(MockWebSocket.instances).toHaveLength(3);

    act(() => MockWebSocket.instances[2].serverClose());
    act(showDocument);
    act(() => vi.advanceTimersByTime(100));

    expect(MockWebSocket.instances).toHaveLength(3);
  });

  it("does not replace an open or connecting socket on visibility change", () => {
    renderHook(() => useWebSocket({ url: "ws://example.test/socket" }));

    act(showDocument);
    expect(MockWebSocket.instances).toHaveLength(1);

    act(() => MockWebSocket.instances[0].open());
    act(showDocument);
    expect(MockWebSocket.instances).toHaveLength(1);
  });

  it("keeps a policy-violation close terminal across visibility changes", () => {
    const { result } = renderHook(() =>
      useWebSocket({
        url: "ws://example.test/socket",
        reconnectInterval: 10,
        maxReconnectAttempts: 5,
      }),
    );

    act(() => MockWebSocket.instances[0].serverClose(1008));
    act(() => vi.advanceTimersByTime(1_000));
    act(showDocument);
    expect(MockWebSocket.instances).toHaveLength(1);

    act(() => result.current.reconnect());
    expect(MockWebSocket.instances).toHaveLength(2);
  });

  it("rebuilds the socket when the URL token changes", () => {
    const { rerender } = renderHook(
      ({ url }) => useWebSocket({ url, autoReconnect: false }),
      { initialProps: { url: "ws://example.test/socket?token=old" } },
    );

    rerender({ url: "ws://example.test/socket?token=new" });

    expect(MockWebSocket.instances.map((socket) => socket.url)).toEqual([
      "ws://example.test/socket?token=old",
      "ws://example.test/socket?token=new",
    ]);
  });
});
