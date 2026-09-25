import Link from "next/link";
import { headers } from "next/headers";

const copy = {
  en: {
    message: "Page not found",
    cta: "Back to home",
  },
  es: {
    message: "Página no encontrada",
    cta: "Volver al inicio",
  },
} as const;

export default async function RootNotFound() {
  const locale = (await headers()).get("x-openwahi-locale") === "en" ? "en" : "es";

  return (
    <html lang={locale} className="dark">
      <body className="bg-background text-foreground">
        <main className="flex min-h-screen flex-col items-center justify-center gap-6 px-6 text-center">
          <h1 className="text-6xl font-bold tracking-tight">404</h1>
          <p className="text-lg opacity-80">{copy[locale].message}</p>
          <Link
            href={`/${locale}`}
            className="inline-flex items-center rounded-md bg-white px-4 py-2 text-sm font-medium text-black hover:opacity-90"
          >
            {copy[locale].cta}
          </Link>
        </main>
      </body>
    </html>
  );
}
