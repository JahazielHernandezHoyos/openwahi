const createNextIntlPlugin = require("next-intl/plugin");

const withNextIntl = createNextIntlPlugin();

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Configuración de rewrites para el backend
  async rewrites() {
    let apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    // Ensure HTTPS protocol in production to avoid mixed content errors
    // Allow HTTP for localhost (development)
    const isLocalhost =
      apiUrl.includes("localhost") || apiUrl.includes("127.0.0.1");
    if (apiUrl.startsWith("http://") && !isLocalhost) {
      apiUrl = apiUrl.replace("http://", "https://");
      console.warn("⚠️ API URL was using HTTP, forced to HTTPS:", apiUrl);
    }

    return [
      {
        source: "/api/backend/:path*",
        destination: `${apiUrl}/:path*`,
      },
    ];
  },

  // Configuración de headers para mejor caché
  async headers() {
    return [
      {
        source: "/_next/static/:path*",
        headers: [
          {
            key: "Cache-Control",
            value: "public, max-age=31536000, immutable",
          },
        ],
      },
    ];
  },
};

module.exports = withNextIntl(nextConfig);
