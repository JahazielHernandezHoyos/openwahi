import axios from "axios";
import { API_BASE_URL } from "@/config/constants";
import { tokenManager } from "@/tools/auth/token-manager";
import { announceUnauthorized } from "@/tools/auth/auth-events";

/**
 * Cliente API con Axios
 * Incluye interceptores para agregar JWT automáticamente
 * Hace peticiones directamente al backend (no usa proxy de Next.js)
 *
 * Soporta DOS tipos de autenticación:
 * 1. Firebase ID token: Authorization: Bearer {token} - Para usuarios logueados
 * 2. API Key: X-API-Key: {key} - Para integraciones externas
 */

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 10000, // 10 segundos
});

// Request interceptor - Agregar token JWT en cada request
apiClient.interceptors.request.use(
  (config) => {
    // Verificar si ya tiene X-API-Key (para integraciones externas)
    if (config.headers["X-API-Key"]) {
      return config;
    }

    // Obtener el Firebase ID token desde localStorage
    const token = tokenManager.getAccessToken();

    if (token) {
      // Establecer el header Authorization con JWT
      config.headers["Authorization"] = `Bearer ${token}`;
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  },
);

// Response interceptor - Manejar errores globalmente
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    const status = error.response?.status;

    if (status === 401) {
      tokenManager.clearTokens();
      announceUnauthorized();
    }

    return Promise.reject(error);
  },
);

export default apiClient;
