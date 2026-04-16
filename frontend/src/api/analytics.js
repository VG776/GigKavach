/**
 * Analytics API Client
 *
 * Provides aggregated analytics data for dashboards:
 *   GET /api/v1/analytics/disruptions/top-causes  — Top disruption causes
 *   GET /api/v1/analytics/fraud/signals           — Current fraud signals
 *   GET /api/v1/analytics/summary                 — High-level summary
 */
import apiClient from './client.js';

export const analyticsAPI = {
  /**
   * Get top disruption causes for a specified period.
   * GET /api/v1/analytics/disruptions/top-causes
   *
   * Query params:
   *   - limit: Number of results (default: 5)
   *   - days: Number of days to look back (default: 30)
   */
  getTopDisruptionCauses: (limit = 5, days = 30) => {
    return apiClient.get('/api/v1/analytics/disruptions/top-causes', {
      params: { limit, days }
    });
  },

  /**
   * Get current fraud detection signals and trends.
   * GET /api/v1/analytics/fraud/signals
   *
   * Query params:
   *   - days: Number of days to analyze (default: 7)
   */
  getFraudSignals: (days = 7) => {
    return apiClient.get('/api/v1/analytics/fraud/signals', {
      params: { days }
    });
  },

  /**
   * Get high-level analytics summary.
   * GET /api/v1/analytics/summary
   */
  getSummary: () => {
    return apiClient.get('/api/v1/analytics/summary');
  },
};
