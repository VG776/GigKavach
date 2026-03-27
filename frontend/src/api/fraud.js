/**
 * Fraud detection API endpoints
 */
import apiClient from './client.js';

const ENDPOINT = '/fraud';

export const fraudAPI = {
  /**
   * Get all fraud alerts
   */
  getAll: (params = {}) => {
    return apiClient.get(ENDPOINT, { params });
  },

  /**
   * Get single fraud alert
   */
  getById: (id) => {
    return apiClient.get(`${ENDPOINT}/${id}`);
  },

  /**
   * Get fraud statistics
   */
  getStats: () => {
    return apiClient.get(`${ENDPOINT}/stats`);
  },

  /**
   * Get fraud signals for worker
   */
  getWorkerSignals: (workerId) => {
    return apiClient.get(`${ENDPOINT}/worker/${workerId}`);
  },

  /**
   * Detect fraud ring (syndicate detection)
   */
  detectSyndicate: (params = {}) => {
    return apiClient.get(`${ENDPOINT}/syndicate`, { params });
  },

  /**
   * Review fraud case
   */
  reviewCase: (id, data) => {
    return apiClient.patch(`${ENDPOINT}/${id}/review`, data);
  },

  /**
   * Appeal fraud case
   */
  appealCase: (id, data) => {
    return apiClient.post(`${ENDPOINT}/${id}/appeal`, data);
  },

  /**
   * Blacklist worker
   */
  blacklistWorker: (workerId, data) => {
    return apiClient.post(`${ENDPOINT}/blacklist/${workerId}`, data);
  },

  /**
   * Remove from blacklist
   */
  removeFromBlacklist: (workerId) => {
    return apiClient.delete(`${ENDPOINT}/blacklist/${workerId}`);
  },

  /**
   * Get zone fraud density
   */
  getZoneDensity: () => {
    return apiClient.get(`${ENDPOINT}/zones/density`);
  },

  /**
   * Get fraud trends (historical data)
   */
  getTrends: (params = {}) => {
    return apiClient.get(`${ENDPOINT}/trends`, { params });
  },

  /**
   * Export fraud report
   */
  exportReport: (format = 'csv') => {
    return apiClient.get(`${ENDPOINT}/export`, { params: { format } });
  },
};
