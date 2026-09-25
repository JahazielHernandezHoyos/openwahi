/**
 * Obtiene el Firebase ID Token para enviarlo al backend.
 * Intenta obtenerlo de localStorage primero. Si no hay o expiró,
 * lo renueva desde Firebase Auth directamente.
 */
import { tokenManager } from '@/tools/auth/token-manager'

export async function getAuthToken(): Promise<string | null> {
  // Primero intentar obtener de localStorage
  const cached = tokenManager.getAccessToken()
  if (cached) {
    return cached
  }

  // Si no hay token en localStorage y estamos en el navegador,
  // intentar obtenerlo directamente del usuario de Firebase Auth
  if (typeof window !== 'undefined') {
    try {
      const { getAuth } = await import('firebase/auth')
      const { auth } = await import('@/config/firebase')
      const currentUser = getAuth(auth.app).currentUser

      if (currentUser) {
        // forceRefresh=false: usa el token cacheado de Firebase si no expiró
        const token = await currentUser.getIdToken(false)
        tokenManager.setAccessToken(token)
        return token
      }
    } catch {
      // Error silenciado
    }
  }

  return null
}
