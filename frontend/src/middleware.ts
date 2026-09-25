import createMiddleware from 'next-intl/middleware';
import { routing } from './i18n/routing';
import { NextRequest } from 'next/server';

const intlMiddleware = createMiddleware(routing);

const LOCALE_HEADER = 'x-openwahi-locale';

function getPathLocale(pathname: string) {
  const locale = pathname.split('/')[1];
  return routing.locales.includes(locale as (typeof routing.locales)[number])
    ? locale
    : routing.defaultLocale;
}

export default function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Make the URL locale available to the root 404 boundary. Next.js renders
  // unmatched App Router URLs through app/not-found.tsx, outside [locale].
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set(LOCALE_HEADER, getPathLocale(pathname));

  return intlMiddleware(
    new NextRequest(request, {
      headers: requestHeaders,
    }),
  );
}

export const config = {
  // Match all pathnames except for
  // - API routes
  // - Static files (_next, images, etc.)
  matcher: ['/((?!api|_next|.*\\..*).*)']
};
