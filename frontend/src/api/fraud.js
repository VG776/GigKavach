/**
 * Fraud Detection API Client
 *
 * Maps to real backend routes mounted in main.py:
 *   POST /api/v1/check-fraud              → Assess a single claim (FraudCheckRequest)
 *   POST /api/v1/fraud/appeal             → Submit an appeal for a blocked payout
 *   GET  /api/v1/fraud/health             → System readiness check for fraud models
 *   GET  /api/v1/fraud-flags              → List all fraud flag records (dashboard)
 *   GET  /api/v1/fraud-summary            → High-level fraud statistics
 */
import apiClient from './client.js';

export const fraudAPI = {
  /**
   * Assess a claim through the 3-stage fraud detection pipeline.
   * Returns: { is_fraud, fraud_score, decision, payout_action, explanation, audit_log }
   * POST /api/v1/check-fraud
   */
  checkClaim: (claimData, workerHistory = null, userContext = null) => {
    return apiClient.post('/api/v1/check-fraud', {
      claim: claimData,
      worker_history: workerHistory,
      user_context: userContext,
    });
  },

  /**
   * Appeal a flagged or blocked payout on behalf of a worker.
   * POST /api/v1/fraud/appeal
   */
  appealCase: (id, data) => {
    return apiClient.post(`/api/v1/fraud/${id}/appeal`, data);
  },

  /**
   * Check if the fraud detection models (IF + XGBoost) are loaded and ready.
   * GET /api/v1/fraud/health
   */
  getHealth: () => {
    return apiClient.get('/api/v1/fraud/health');
  },

  /**
   * Get all active fraud flags for the dashboard.
   * GET /api/v1/fraud-flags
   *
   * Query params:
   *   - limit: Max records (default: 100)
   *   - resolved: Include resolved cases (default: false)
   *   - tier: Filter by tier ('tier0', 'tier1', 'tier2')
   */
  getFraudFlags: (limit = 100, resolved = false, tier = null) => {
    const params = { limit, resolved };
    if (tier) params.tier = tier;
    return apiClient.get('/api/v1/fraud-flags', { params });
  },

  /**
   * Get high-level fraud summary statistics.
   * GET /api/v1/fraud-summary
   */
  getFraudSummary: () => {
    return apiClient.get('/api/v1/fraud-summary');
  },
};
