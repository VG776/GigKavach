/**
 * Worker API endpoints
 */
import apiClient from './client.js';

const ENDPOINT = '/workers';

export const workerAPI = {
  /**
   * Get all workers with pagination and filters
   */
  getAll: (params = {}) => {
    return apiClient.get(ENDPOINT, { params });
  },

  /**
   * Get single worker by ID
   */
  getById: (id) => {
    return apiClient.get(`${ENDPOINT}/${id}`);
  },

  /**
   * Create new worker
   */
  create: (data) => {
    return apiClient.post(ENDPOINT, data);
  },

  /**
   * Update worker
   */
  update: (id, data) => {
    return apiClient.patch(`${ENDPOINT}/${id}`, data);
  },

  /**
   * Delete worker
   */
  delete: (id) => {
    return apiClient.delete(`${ENDPOINT}/${id}`);
  },

  /**
   * Get worker's DCI score
   */
  getDCI: (id) => {
    return apiClient.get(`${ENDPOINT}/${id}/dci`);
  },

  /**
   * Get worker's payouts
   */
  getPayouts: (id, params = {}) => {
    return apiClient.get(`${ENDPOINT}/${id}/payouts`, { params });
  },

  /**
   * Get worker's fraud flags
   */
  getFraudFlags: (id) => {
    return apiClient.get(`${ENDPOINT}/${id}/fraud-flags`);
  },

  /**
   * Get worker's GigScore (derived from multiple factors)
   */
  getGigScore: (id) => {
    return apiClient.get(`${ENDPOINT}/${id}/gig-score`);
  },

  /**
   * Search workers by name or phone
   */
  search: (query) => {
    return apiClient.get(`${ENDPOINT}/search`, { params: { q: query } });
  },

  /**
   * Get workers by zone
   */
  getByZone: (zoneId, params = {}) => {
    return apiClient.get(`${ENDPOINT}/zone/${zoneId}`, { params });
  },

  /**
   * Export workers list
   */
  export: (format = 'csv') => {
    return apiClient.get(`${ENDPOINT}/export`, { params: { format } });
  },
};
