import { NextResponse, type NextRequest } from 'next/server'

/**
 * Firebase Auth callback handler.
 *
 * With Firebase's signInWithRedirect flow, Firebase handles the OAuth exchange
 * internally at {authDomain}/__/auth/handler. When the user returns to the app,
 * getRedirectResult() in AuthContext picks up the result client-side.
 *
 * This route exists only as a fallback redirect in case anything lands here.
 */
export async function GET(request: NextRequest) {
  const { origin } = new URL(request.url)
  const pathname = new URL(request.url).pathname
  const locale = pathname.split('/')[1] || 'es'

  const isLocalhost = origin.includes('localhost') || origin.includes('127.0.0.1')
  const frontendUrl = isLocalhost
    ? origin
    : (process.env.NEXT_PUBLIC_FRONTEND_URL || origin)

  return NextResponse.redirect(`${frontendUrl}/${locale}/dashboard`)
}
