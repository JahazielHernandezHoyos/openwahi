"use client";

import { useEffect, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";

const PRIVATE_ROUTE_SEGMENTS = new Set([
  "dashboard",
  "items",
  "whatsapp-devices",
  "whatsapp-chats",
  "ai-assistant",
  "knowledge-base",
  "developer",
  "admin",
]);

/** Return the locale when the pathname belongs to a private route. */
export function getPrivateRouteLocale(pathname: string): string | null {
  const [, locale, route] = pathname.split("/");
  return locale && route && PRIVATE_ROUTE_SEGMENTS.has(route) ? locale : null;
}

export function AuthenticatedRouteGuard({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, loading } = useAuth();
  const privateLocale = getPrivateRouteLocale(pathname);

  useEffect(() => {
    if (privateLocale && !loading && !user) {
      router.replace(`/${privateLocale}/login`);
    }
  }, [loading, privateLocale, router, user]);

  // Public routes never wait for Firebase. Private children do not mount until
  // auth resolves, which also prevents their data hooks from firing early.
  if (!privateLocale) return children;
  if (loading || !user) return null;
  return children;
}
