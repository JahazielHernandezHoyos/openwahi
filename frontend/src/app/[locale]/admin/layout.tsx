"use client";

import { useLocale } from "next-intl";
import { notFound, redirect } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { useCurrentUser } from "@/modules/admin/hooks/useAdmin";
import { useMounted } from "@/tools/hooks/useMounted";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const mounted = useMounted();
  const locale = useLocale();
  const { data: currentUser, isPending } = useCurrentUser(!!user);

  // Mientras carga, no renderizar nada (evita flash)
  if (!mounted || loading) return null;

  // Sin sesión → redirigir al login para que el admin pueda autenticarse
  if (!user) {
    redirect(`/${locale}/login`);
  }

  if (isPending) return null;

  // Sesión activa pero sin permisos de admin → 404 (no revelar existencia del panel)
  if (!currentUser?.is_admin) {
    notFound();
  }

  return <>{children}</>;
}
