export const AUTH_UNAUTHORIZED_EVENT = "openwahi:auth-unauthorized";

/** Notify the auth provider that the backend rejected the current session. */
export function announceUnauthorized(): void {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(AUTH_UNAUTHORIZED_EVENT));
  }
}
