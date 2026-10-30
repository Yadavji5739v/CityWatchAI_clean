const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL?.replace(/\/+$/, "");

if (!configuredApiBaseUrl && !import.meta.env.DEV) {
  throw new Error("VITE_API_BASE_URL must be set to the deployed CityWatch API URL.");
}

export const API_BASE_URL = configuredApiBaseUrl || "http://127.0.0.1:8000/api";
