import type { Metadata } from "next";
import { APP_NAME } from "@/config/brand";

const metadataByLocale = {
  en: {
    title: `${APP_NAME} - Automate WhatsApp with AI`,
    description:
      "Connect WhatsApp, create intelligent bots that reply for you, and manage thousands of conversations automatically.",
  },
  es: {
    title: `${APP_NAME} - Automatiza tu WhatsApp con IA`,
    description:
      "Conecta tu WhatsApp, crea bots inteligentes que responden por ti y gestiona miles de conversaciones automáticamente.",
  },
} as const;

export function getLocaleMetadata(locale: string): Metadata {
  const copy = locale === "en" ? metadataByLocale.en : metadataByLocale.es;

  return {
    ...copy,
    icons: {
      icon: [{ url: "/favicon.svg", type: "image/svg+xml" }],
    },
  };
}
