import { client } from './client';

/**
 * Telemetry API - Handles real-time location submission
 */
export const telemetryAPI = {
  /**
   * Submits raw location data from the worker's device
   * @param {string} workerId 
   * @param {[number, number]} coordinates [lat, lng]
   * @param {number} speed km/h
   */
  submit: async (workerId, coordinates, speed = 0) => {
    try {
      const response = await client.post('/telemetry/submit', {
        worker_id: workerId,
        coordinates,
        speed: speed || 0,
        captured_at: new Date().toISOString()
      });
      return response.data;
    } catch (err) {
      console.error('[TELEMETRY_API] Submission failed:', err);
      throw err;
    }
  }
};
