/**
 * Premium API Client
 * 
 * Handles all premium quote calculations and pricing endpoints.
 * Maps to backend /api/v1/premium/* endpoints
 */
import apiClient from './client.js';

export const premiumAPI = {
  /**
   * Get a dynamic premium quote for a worker
   * POST /api/v1/premium/quote
   * 
   * Request body:
   *   - worker_id: string (UUID) - worker identifier
   *   - plan_tier: string - one of: 'basic', 'plus', 'pro'
   * 
   * Response:
   *   {
   *     worker_id: string,
   *     base_premium: number - list price for plan
   *     dynamic_premium: number - personalized price after discount
   *     discount_applied: number - amount saved in currency
   *     bonus_coverage_hours: number - bonus hours if DCI is high
   *     plan_type: string - confirmed plan tier
   *     risk_score: number - 0-100 inverse of gig_score
   *     risk_factors: {
   *       gig_score: number,
   *       zone_risk: string - 'High' or 'Normal',
   *       primary_zone: string - city name
   *     },
   *     explanation: string - reason for discount
   *     insights: {
   *       gig_score: number,
   *       forecasted_zone_risk: string,
   *       primary_zone: string,
   *       reason: string
   *     }
   *   }
   */
  getQuote: async (workerId, planTier = 'basic') => {
    try {
      const response = await apiClient.post('/api/v1/premium/quote', {
        worker_id: workerId,
        plan_tier: planTier.toLowerCase()
      });
      return response;
    } catch (error) {
      console.error('[PREMIUM_API] Error fetching quote:', error.response?.data || error.message);
      throw error;
    }
  },

  /**
   * Get premium quote using GET endpoint (legacy support)
   * GET /api/v1/premium/quote?worker_id={id}&plan={tier}
   * 
   * Use post-based getQuote() instead for production
   */
  getQuoteGet: async (workerId, planTier = 'basic') => {
    try {
      const response = await apiClient.get('/api/v1/premium/quote', {
        params: {
          worker_id: workerId,
          plan: planTier.toLowerCase()
        }
      });
      return response;
    } catch (error) {
      console.error('[PREMIUM_API] Error fetching quote (GET):', error.response?.data || error.message);
      throw error;
    }
  },

  /**
   * Validate plan tier is correct
   * @param {string} planTier - 'basic', 'plus', or 'pro'
   * @returns {boolean}
   */
  isValidPlanTier: (planTier) => {
    const validPlans = ['basic', 'plus', 'pro'];
    return validPlans.includes((planTier || '').toLowerCase());
  },

  /**
   * Get plan base prices (convenience mapping)
   * Note: Actual base prices are returned from API, this is just reference
   */
  getPlanPrices: () => {
    return {
      basic: 20,      // ₹20 per week
      plus: 32,       // ₹32 per week  
      pro: 44         // ₹44 per week
    };
  },

  /**
   * Format currency for display
   * @param {number} amount 
   * @returns {string} formatted currency string
   */
  formatCurrency: (amount) => {
    return `₹${(amount || 0).toFixed(2)}`;
  },

  /**
   * Calculate discount percentage
   * @param {number} basePrice
   * @param {number} discountAmount
   * @returns {number} percentage
   */
  getDiscountPercentage: (basePrice, discountAmount) => {
    if (!basePrice || basePrice === 0) return 0;
    return Math.round((discountAmount / basePrice) * 100);
  }
};
