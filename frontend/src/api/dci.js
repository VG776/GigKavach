/**
 * DCI (Disaster Coefficient Index) API endpoints
 */
import apiClient from './client.js';

const ENDPOINT = '/dci';

export const dciAPI = {
  /**
   * Get current DCI for zone
   */
  getByZone: (zoneId) => {
    return apiClient.get(`${ENDPOINT}/zone/${zoneId}`);
  },

  /**
   * Get all zones DCI data
   */
  getAllZones: () => {
    return apiClient.get(`${ENDPOINT}/zones`);
  },

  /**
   * Get DCI history for zone (24 hours)
   */
  getHistory: (zoneId, hoursBack = 24) => {
    return apiClient.get(`${ENDPOINT}/zone/${zoneId}/history`, {
      params: { hours: hoursBack },
    });
  },

  /**
   * Get DCI forecast for zone (24 hours ahead)
   */
  getForecast: (zoneId, hoursAhead = 24) => {
    return apiClient.get(`${ENDPOINT}/zone/${zoneId}/forecast`, {
      params: { hours: hoursAhead },
    });
  },

  /**
   * Get heatmap data
   */
  getHeatmap: () => {
    return apiClient.get(`${ENDPOINT}/heatmap`);
  },

  /**
   * Get DCI breakdown (components: temperature, rainfall, wind, etc)
   */
  getBreakdown: (zoneId) => {
    return apiClient.get(`${ENDPOINT}/zone/${zoneId}/breakdown`);
  },

  /**
   * Get DCI trends
   */
  getTrends: (params = {}) => {
    return apiClient.get(`${ENDPOINT}/trends`, { params });
  },

  /**
   * Get critical zones (DCI > threshold)
   */
  getCriticalZones: (threshold = 75) => {
    return apiClient.get(`${ENDPOINT}/critical`, { params: { threshold } });
  },
};
