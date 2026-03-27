/**
 * Policy API endpoints
 */
import apiClient from './client.js';

const ENDPOINT = '/policies';

export const policyAPI = {
  /**
   * Get all policies
   */
  getAll: (params = {}) => {
    return apiClient.get(ENDPOINT, { params });
  },

  /**
   * Get single policy
   */
  getById: (id) => {
    return apiClient.get(`${ENDPOINT}/${id}`);
  },

  /**
   * Create new policy
   */
  create: (data) => {
    return apiClient.post(ENDPOINT, data);
  },

  /**
   * Update policy
   */
  update: (id, data) => {
    return apiClient.patch(`${ENDPOINT}/${id}`, data);
  },

  /**
   * Delete policy
   */
  delete: (id) => {
    return apiClient.delete(`${ENDPOINT}/${id}`);
  },

  /**
   * Get policy tiers
   */
  getTiers: () => {
    return apiClient.get(`${ENDPOINT}/tiers`);
  },

  /**
   * Get worker's active policy
   */
  getWorkerPolicy: (workerId) => {
    return apiClient.get(`/workers/${workerId}/policy`);
  },

  /**
   * Get policy coverage details
   */
  getCoverageDetails: (id) => {
    return apiClient.get(`${ENDPOINT}/${id}/coverage`);
  },

  /**
   * Clone policy for worker
   */
  cloneForWorker: (policyId, workerId) => {
    return apiClient.post(`${ENDPOINT}/${policyId}/clone`, { workerId });
  },
};
