/**
 * Token Manager
 * Maneja el almacenamiento y recuperación del Firebase ID Token en localStorage.
 * Firebase ID Tokens expiran cada 1 hora. onAuthStateChanged en AuthContext
 * los renueva automáticamente con getIdToken() y los guarda aquí.
 */

const ACCESS_TOKEN_KEY = "fb_id_token";

export const tokenManager = {
  /**
   * Obtiene el Firebase ID Token del localStorage
   */
  getAccessToken: (): string | null => {
    if (typeof window === "undefined") {
      return null;
    }
    try {
      return localStorage.getItem(ACCESS_TOKEN_KEY);
    } catch {
      return null;
    }
  },

  /**
   * Guarda el Firebase ID Token en localStorage
   */
  setAccessToken: (token: string): void => {
    if (typeof window === "undefined") {
      return;
    }
    try {
      localStorage.setItem(ACCESS_TOKEN_KEY, token);
    } catch {
      // Error silenciado
    }
  },

  /**
   * Elimina el token del localStorage
   */
  clearTokens: (): void => {
    if (typeof window === "undefined") {
      return;
    }
    localStorage.removeItem(ACCESS_TOKEN_KEY);
  },

  /**
   * Verifica si hay un token guardado
   */
  hasToken: (): boolean => {
    if (typeof window === "undefined") {
      return false;
    }
    return !!localStorage.getItem(ACCESS_TOKEN_KEY);
  },
};
