/**
 * Payout API endpoints
 */
import apiClient from './client.js';

const ENDPOINT = '/payouts';

export const payoutAPI = {
  /**
   * Get all payouts with filters
   */
  getAll: (params = {}) => {
    return apiClient.get(ENDPOINT, { params });
  },

  /**
   * Get single payout
   */
  getById: (id) => {
    return apiClient.get(`${ENDPOINT}/${id}`);
  },

  /**
   * Create payout
   */
  create: (data) => {
    return apiClient.post(ENDPOINT, data);
  },

  /**
   * Update payout status
   */
  updateStatus: (id, status) => {
    return apiClient.patch(`${ENDPOINT}/${id}/status`, { status });
  },

  /**
   * Get payout statistics
   */
  getStats: () => {
    return apiClient.get(`${ENDPOINT}/stats`);
  },

  /**
   * Get escrow data
   */
  getEscrow: (params = {}) => {
    return apiClient.get(`${ENDPOINT}/escrow`, { params });
  },

  /**
   * Release escrow
   */
  releaseEscrow: (id) => {
    return apiClient.patch(`${ENDPOINT}/${id}/escrow/release`);
  },

  /**
   * Re-verify escrow
   */
  reverifyEscrow: (id) => {
    return apiClient.patch(`${ENDPOINT}/${id}/escrow/reverify`);
  },

  /**
   * Trigger payout simulation
   */
  triggerSimulation: (data) => {
    return apiClient.post(`${ENDPOINT}/simulation`, data);
  },

  /**
   * Get payout history for worker
   */
  getWorkerHistory: (workerId, params = {}) => {
    return apiClient.get(`/workers/${workerId}/payouts`, { params });
  },
};
