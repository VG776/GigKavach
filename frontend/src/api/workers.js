/**
 * Worker API Client
 * 
 * Maps 1:1 to live backend routes with a mix of root and /api prefixes.
 */
import apiClient from './client.js';

export const workerAPI = {
  /**
   * Get all workers with pagination and filters.
   * GET /api/v1/workers/
   */
  getAll: (params = {}) => {
    return apiClient.get('/api/v1/workers/', { params });
  },

  /**
   * Get single worker by ID with full profile details.
   * GET /api/v1/workers/{worker_id}
   */
  getById: (worker_id) => {
    return apiClient.get(`/api/v1/workers/${worker_id}`);
  },

  /**
   * Get the total count of workers with an active policy this calendar week.
   * GET /api/v1/workers/active/week
   */
  getActiveWeekCount: () => {
    return apiClient.get('/api/v1/workers/active/week');
  },

  /**
   * Toggle worker shift status (Start/Stop Work)
   * PATCH /api/v1/workers/shift-status
   */
  updateShiftStatus: (worker_id, is_working) => {
    return apiClient.patch('/api/v1/workers/shift-status', null, { 
      params: { worker_id, is_working } 
    });
  }
};
