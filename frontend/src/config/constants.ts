let apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Avoid mixed-content errors when the page is served over HTTPS.
if (
  apiUrl.startsWith("http://") &&
  typeof window !== "undefined" &&
  window.location.protocol === "https:"
) {
  apiUrl = apiUrl.replace("http://", "https://");
  console.warn(
    "⚠️ API URL was using HTTP in HTTPS context, forced to HTTPS:",
    apiUrl,
  );
}

export const API_BASE_URL = apiUrl;
