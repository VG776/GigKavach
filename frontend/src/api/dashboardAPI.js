/**
 * Dashboard API client
 * ✅ Uses the properly configured API client from client.js
 * which reads VITE_API_BASE_URL from environment variables
 */
import apiClient from "./client.js";

export const dashboardAPI = {
  // Payout endpoints (registered at: /payouts/total/today)
  getTodayPayout: () => apiClient.get("/payouts/total/today"),

  // DCI endpoints (registered at: /dci/total/today)
  getTodayDCI: () => apiClient.get("/dci/total/today"),

  // Workers endpoints (registered at: /api/workers/active/week)
  getActiveWorkersWeek: () => apiClient.get("/api/workers/active/week"),

  // Payouts list (registered at: /payouts?limit=3)
  getRecentPayouts: () => apiClient.get("/payouts?limit=3"),

  // DCI Alerts (registered at: /api/v1/dci-alerts/latest)
  getActiveZones: () =>
    apiClient.get("/api/v1/dci-alerts/latest?limit=3"),
};