"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  type User,
  signInWithPopup,
  GoogleAuthProvider,
  signOut as firebaseSignOut,
  onIdTokenChanged,
} from "firebase/auth";
import { auth } from "@/config/firebase";
import { tokenManager } from "@/tools/auth/token-manager";
import { AUTH_UNAUTHORIZED_EVENT } from "@/tools/auth/auth-events";
import { isEmailAllowed } from "@/lib/email-whitelist";

const googleProvider = new GoogleAuthProvider();

// Development-only support for an ID token injected into localStorage.
const DEV_BYPASS =
  process.env.NODE_ENV !== "production" &&
  process.env.NEXT_PUBLIC_DEV_BYPASS_AUTH === "true";

const makeSyntheticUser = (): User =>
  ({
    uid: "dev-bypass",
    email: "dev@local",
    displayName: "Dev Bypass",
    getIdToken: async (_forceRefresh?: boolean) =>
      tokenManager.getAccessToken() ?? "",
  }) as unknown as User;

interface AuthContextType {
  user: User | null;
  idToken: string | null;
  loading: boolean;
  signInWithGoogle: () => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<User | null>(null);
  const [idToken, setIdToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const generationRef = useRef(0);
  const mountedRef = useRef(true);
  const currentUidRef = useRef<string | null>(null);

  const clearQueryCache = useCallback(async () => {
    await queryClient.cancelQueries();
    queryClient.clear();
  }, [queryClient]);

  const clearSession = useCallback(async () => {
    generationRef.current += 1;
    currentUidRef.current = null;
    tokenManager.clearTokens();
    if (mountedRef.current) {
      setIdToken(null);
      setUser(null);
      setLoading(false);
    }
    await clearQueryCache();
  }, [clearQueryCache]);

  useEffect(() => {
    if (DEV_BYPASS) {
      console.warn(
        "[AuthContext] DEV_BYPASS_AUTH active — using injected localStorage token",
      );
    }

    // This listener covers login, logout, and every Firebase ID-token refresh.
    mountedRef.current = true;
    const unsubscribe = onIdTokenChanged(auth, async (firebaseUser) => {
      const generation = ++generationRef.current;
      if (!firebaseUser) {
        if (DEV_BYPASS && tokenManager.hasToken()) {
          const bypassToken = tokenManager.getAccessToken();
          if (mountedRef.current && generation === generationRef.current) {
            const bypassUser = makeSyntheticUser();
            currentUidRef.current = bypassUser.uid;
            setUser(bypassUser);
            setIdToken(bypassToken);
          }
        } else {
          currentUidRef.current = null;
          tokenManager.clearTokens();
          if (mountedRef.current) {
            setIdToken(null);
            setUser(null);
          }
          await clearQueryCache();
        }
        if (mountedRef.current && generation === generationRef.current) {
          setLoading(false);
        }
        return;
      }

      try {
        const nextToken = await firebaseUser.getIdToken();
        if (!mountedRef.current || generation !== generationRef.current) return;

        const previousUid = currentUidRef.current;
        if (previousUid !== null && previousUid !== firebaseUser.uid) {
          await clearQueryCache();
          if (!mountedRef.current || generation !== generationRef.current) return;
        }

        currentUidRef.current = firebaseUser.uid;
        tokenManager.setAccessToken(nextToken);
        setIdToken(nextToken);
        setUser(firebaseUser);
      } catch {
        if (!mountedRef.current || generation !== generationRef.current) return;
        // A failed refresh must not leave a user paired with a stale token.
        await clearSession();
        await firebaseSignOut(auth).catch(() => undefined);
      } finally {
        if (mountedRef.current && generation === generationRef.current) {
          setLoading(false);
        }
      }
    });

    return () => {
      mountedRef.current = false;
      generationRef.current += 1;
      unsubscribe();
    };
  }, [clearQueryCache, clearSession]);

  useEffect(() => {
    const handleUnauthorized = () => {
      // Clear React and cached state immediately; Firebase cleanup can finish later.
      void clearSession();
      void firebaseSignOut(auth).catch(() => undefined);
    };

    window.addEventListener(AUTH_UNAUTHORIZED_EVENT, handleUnauthorized);
    return () =>
      window.removeEventListener(AUTH_UNAUTHORIZED_EVENT, handleUnauthorized);
  }, [clearSession]);

  const signInWithGoogle = async () => {
    const result = await signInWithPopup(auth, googleProvider);
    const userEmail = result.user.email;

    if (!isEmailAllowed(userEmail ?? undefined)) {
      await clearSession();
      await firebaseSignOut(auth);
      window.location.href = `${window.location.origin}/login?error=email_not_allowed&email=${encodeURIComponent(userEmail || "")}`;
      return;
    }
  };

  const signOut = async () => {
    await clearSession();
    await firebaseSignOut(auth);
  };

  return (
    <AuthContext.Provider
      value={{ user, idToken, loading, signInWithGoogle, signOut }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
