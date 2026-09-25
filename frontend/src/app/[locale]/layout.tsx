import { NextIntlClientProvider } from "next-intl";
import { getMessages, setRequestLocale } from "next-intl/server";
import { Inter } from "next/font/google";
import "../globals.css";
import { AuthProvider } from "@/context/AuthContext";
import { AuthenticatedRouteGuard } from "@/components/auth/AuthenticatedRouteGuard";
import { QueryProvider } from "@/providers/QueryProvider";
import { Toaster } from "@/components/ui/toaster";
import { routing } from "@/i18n/routing";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { getLocaleMetadata } from "./metadata";
import Script from "next/script";
import { APP_NAME } from "@/config/brand";
import { API_BASE_URL } from "@/config/constants";

const inter = Inter({ subsets: ["latin"] });

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return getLocaleMetadata(locale);
}

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;

  // Ensure that the incoming `locale` is valid
  if (!routing.locales.includes(locale as any)) {
    notFound();
  }

  // Enable static rendering
  setRequestLocale(locale);

  // Providing all messages to the client
  // side is the easiest way to get started
  const messages = await getMessages();

  const WIDGET_TOKEN = process.env.NEXT_PUBLIC_SUPPORT_WIDGET_TOKEN;
  const WIDGET_TITLE =
    process.env.NEXT_PUBLIC_SUPPORT_WIDGET_TITLE || `${APP_NAME} support`;

  return (
    <html lang={locale} className="dark" suppressHydrationWarning>
      <body className={inter.className} suppressHydrationWarning>
        <NextIntlClientProvider messages={messages}>
          <QueryProvider>
            <AuthProvider>
              <AuthenticatedRouteGuard>
                {children}
                <Toaster />
              </AuthenticatedRouteGuard>
            </AuthProvider>
          </QueryProvider>
        </NextIntlClientProvider>

        {/* Optional support chat widget — loaded via next/script to avoid React hydration issues */}
        {WIDGET_TOKEN && (
          <>
            {/*
              Pass config to widget.js via window globals.
              __OPENWAHI_DARK__=true activates the dark theme so the widget
              matches the app's dark-mode design system.
            */}
            <Script id="support-widget-config" strategy="afterInteractive">
              {[
                `window.__OPENWAHI_TOKEN__=${JSON.stringify(WIDGET_TOKEN)};`,
                `window.__OPENWAHI_BACKEND_URL__=${JSON.stringify(API_BASE_URL)};`,
                `window.__OPENWAHI_TITLE__=${JSON.stringify(WIDGET_TITLE)};`,
                `window.__OPENWAHI_DARK__=true;`,
              ].join("")}
            </Script>
            <Script
              src={`${API_BASE_URL}/static/widget.js`}
              data-widget-token={WIDGET_TOKEN}
              strategy="afterInteractive"
            />
          </>
        )}
      </body>
    </html>
  );
}
