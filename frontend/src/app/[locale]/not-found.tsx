"use client";

import { useLocale, useTranslations } from "next-intl";
import Link from "next/link";

export default function LocaleNotFound() {
  const t = useTranslations("notFound");
  const locale = useLocale();
  return (
    <main className="flex min-h-[70vh] flex-col items-center justify-center gap-6 px-6 text-center">
      <h1 className="text-6xl font-bold tracking-tight">404</h1>
      <p className="text-lg text-muted-foreground">{t("message")}</p>
      <Link
        href={`/${locale}`}
        className="inline-flex items-center rounded-md border border-border bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
      >
        {t("cta")}
      </Link>
    </main>
  );
}
