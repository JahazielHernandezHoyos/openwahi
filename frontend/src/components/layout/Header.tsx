"use client";

import { useState } from "react";
import { useRouter, usePathname, Link } from "@/i18n/routing";
import { useLocale, useTranslations } from "next-intl";
import { useAuth } from "@/context/AuthContext";
import { useMounted } from "@/tools/hooks/useMounted";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { useQueryClient } from "@tanstack/react-query";
import { whatsappApi } from "@/modules/whatsapp/services/whatsappApi";
import { Menu, X } from "lucide-react";
import { APP_NAME } from "@/config/brand";

export const Header = () => {
  const t = useTranslations("Auth");
  const tNav = useTranslations("Navigation");
  const locale = useLocale();
  const pathname = usePathname();
  const { user, signOut } = useAuth();
  const router = useRouter();
  const mounted = useMounted();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const queryClient = useQueryClient();

  const handleSignOut = async () => {
    try {
      await signOut();
      router.push("/login");
    } catch (error) {
      // Error silenciado
    }
  };

  const prefetchDevices = () => {
    queryClient.prefetchQuery({
      queryKey: ["whatsapp-devices"],
      queryFn: () => whatsappApi.getDevices(),
    });
  };

  const prefetchChats = () => {
    queryClient.prefetchQuery({
      queryKey: ["whatsapp-chats", undefined],
      queryFn: () => whatsappApi.getChats(),
    });
  };

  // No renderizar hasta que el componente esté montado para evitar problemas de hidratación
  if (!mounted || !user) return null;

  return (
    <header className="w-full overflow-x-clip border-b bg-background">
      <div className="max-w-7xl min-w-0 mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo y navegación */}
          <div className="flex min-w-0 items-center gap-4 min-[1100px]:gap-8">
            <Link href="/dashboard" className="flex items-center">
              <span className="text-xl font-bold text-primary">{APP_NAME}</span>
            </Link>

            <Separator orientation="vertical" className="h-6 hidden min-[856px]:block" />

            <nav className="hidden min-[856px]:flex min-w-0 gap-0 min-[1100px]:gap-1">
              <Button variant="ghost" asChild>
                <Link href="/dashboard">{tNav("dashboard")}</Link>
              </Button>
              <Button variant="ghost" asChild onMouseEnter={prefetchDevices}>
                <Link href="/whatsapp-devices">{tNav("devices")}</Link>
              </Button>
              <Button variant="ghost" asChild onMouseEnter={prefetchChats}>
                <Link href="/whatsapp-chats">{tNav("chats")}</Link>
              </Button>
              <Button variant="ghost" asChild>
                <Link href="/ai-assistant">{tNav("aiAssistant")}</Link>
              </Button>
              <Button variant="ghost" asChild>
                <Link href="/knowledge-base">{tNav("knowledgeBase")}</Link>
              </Button>
              <Button variant="ghost" asChild>
                <Link href="/developer">{tNav("developer")}</Link>
              </Button>
            </nav>
          </div>

          {/* Usuario y logout */}
          <div className="flex items-center gap-4">
            <div className="hidden min-[1200px]:flex items-center gap-3">
              <span className="text-sm text-muted-foreground">
                {user.email}
              </span>
            </div>

            <div className="flex items-center gap-2 mr-2">
              <Link
                href={pathname}
                locale="en"
                className={locale === "en" ? "font-bold" : ""}
              >
                <Button variant="ghost" size="sm" className="px-2">
                  EN
                </Button>
              </Link>
              <Link
                href={pathname}
                locale="es"
                className={locale === "es" ? "font-bold" : ""}
              >
                <Button variant="ghost" size="sm" className="px-2">
                  ES
                </Button>
              </Link>
            </div>

            <Button
              variant="outline"
              className="hidden min-[856px]:inline-flex"
              onClick={handleSignOut}
            >
              {t("logout")}
            </Button>

            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="min-[856px]:hidden"
              aria-label={mobileMenuOpen ? tNav("closeMenu") : tNav("openMenu")}
              aria-controls="mobile-navigation"
              aria-expanded={mobileMenuOpen}
              onClick={() => setMobileMenuOpen((open) => !open)}
            >
              {mobileMenuOpen ? (
                <X className="h-5 w-5" />
              ) : (
                <Menu className="h-5 w-5" />
              )}
            </Button>
          </div>
        </div>

        {mobileMenuOpen && (
          <nav
            id="mobile-navigation"
            className="grid gap-1 border-t py-3 min-[856px]:hidden"
            aria-label={tNav("mobileMenu")}
          >
            <Button variant="ghost" className="w-full justify-start" asChild>
              <Link href="/dashboard" onClick={() => setMobileMenuOpen(false)}>
                {tNav("dashboard")}
              </Link>
            </Button>
            <Button variant="ghost" className="w-full justify-start" asChild>
              <Link
                href="/whatsapp-devices"
                onClick={() => setMobileMenuOpen(false)}
              >
                {tNav("devices")}
              </Link>
            </Button>
            <Button variant="ghost" className="w-full justify-start" asChild>
              <Link
                href="/whatsapp-chats"
                onClick={() => setMobileMenuOpen(false)}
              >
                {tNav("chats")}
              </Link>
            </Button>
            <Button variant="ghost" className="w-full justify-start" asChild>
              <Link
                href="/ai-assistant"
                onClick={() => setMobileMenuOpen(false)}
              >
                {tNav("aiAssistant")}
              </Link>
            </Button>
            <Button variant="ghost" className="w-full justify-start" asChild>
              <Link
                href="/knowledge-base"
                onClick={() => setMobileMenuOpen(false)}
              >
                {tNav("knowledgeBase")}
              </Link>
            </Button>
            <Button variant="ghost" className="w-full justify-start" asChild>
              <Link href="/developer" onClick={() => setMobileMenuOpen(false)}>
                {tNav("developer")}
              </Link>
            </Button>
            <Button
              variant="ghost"
              className="w-full justify-start"
              onClick={handleSignOut}
            >
              {t("logout")}
            </Button>
          </nav>
        )}
      </div>
    </header>
  );
};
