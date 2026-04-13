import { useEffect, useState } from 'react';
import { Zap, TrendingDown, Clock, AlertCircle, Loader2, CheckCircle } from 'lucide-react';
import { premiumAPI } from '../../api/premium.js';
import { formatCurrency } from '../../utils/formatters.js';

/**
 * PremiumQuote Component
 * Displays dynamic premium pricing based on worker profile and zone risk
 * Shows base price, discount, bonus coverage, and risk factors
 */
export function PremiumQuote({ workerId, selectedPlan = 'basic', onPlanChange = () => {} }) {
  const [quote, setQuote] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedPlanLocal, setSelectedPlanLocal] = useState(selectedPlan);

  // Fetch premium quote whenever worker or plan changes
  useEffect(() => {
    if (!workerId) {
      setError('Worker ID required');
      return;
    }

    const fetchQuote = async () => {
      // TODO: Premium API temporarily disabled due to 422 validation errors
      // Need to investigate request format mismatch
      setLoading(false);
      setError(null);
      setQuote(null);
      // setLoading(true);
      // setError(null);
      // try {
      //   const quoteData = await premiumAPI.getQuote(workerId, selectedPlanLocal);
      //   setQuote(quoteData);
      // } catch (err) {
      //   console.error('[PREMIUM_QUOTE] Error:', err);
      //   setError(err.response?.data?.detail || 'Failed to fetch premium quote');
      //   setQuote(null);
      // } finally {
      //   setLoading(false);
      // }
    };

    const timer = setTimeout(fetchQuote, 300);
    return () => clearTimeout(timer);
  }, [workerId, selectedPlanLocal]);

  // Handle plan change
  const handlePlanChange = (newPlan) => {
    setSelectedPlanLocal(newPlan);
    onPlanChange(newPlan);
  };

  // Plan options
  const plans = [
    { value: 'basic', label: 'Basic', color: 'from-blue-500 to-blue-600', bgColor: 'bg-blue-50 dark:bg-blue-900/20', textColor: 'text-blue-600 dark:text-blue-300' },
    { value: 'plus', label: 'Plus', color: 'from-purple-500 to-purple-600', bgColor: 'bg-purple-50 dark:bg-purple-900/20', textColor: 'text-purple-600 dark:text-purple-300' },
    { value: 'pro', label: 'Pro', color: 'from-amber-500 to-amber-600', bgColor: 'bg-amber-50 dark:bg-amber-900/20', textColor: 'text-amber-600 dark:text-amber-300' },
  ];

  // Loading state
  if (loading && !quote) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-center gap-3">
          <Loader2 className="w-5 h-5 text-gigkavach-orange animate-spin" />
          <p className="text-gray-600 dark:text-gray-400">Calculating your premium...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error && !quote) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 rounded-xl p-6 border border-red-200 dark:border-red-800">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-red-900 dark:text-red-200">Unable to Calculate Premium</p>
            <p className="text-sm text-red-700 dark:text-red-300 mt-1">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Plan Selector */}
      <div className="grid grid-cols-3 gap-3">
        {plans.map((plan) => (
          <button
            key={plan.value}
            onClick={() => handlePlanChange(plan.value)}
            className={`p-3 rounded-lg border-2 transition-all ${
              selectedPlanLocal === plan.value
                ? `border-${plan.value === 'basic' ? 'blue' : plan.value === 'plus' ? 'purple' : 'amber'}-500 bg-gradient-to-br ${plan.color} text-white shadow-lg`
                : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-gray-300 dark:hover:border-gray-600'
            }`}
          >
            <div className="text-sm font-semibold">{plan.label}</div>
            <div className={`text-xs mt-1 ${selectedPlanLocal === plan.value ? 'text-white/80' : 'text-gray-500 dark:text-gray-400'}`}>
              {quote?.base_premium && selectedPlanLocal === plan.value
                ? formatCurrency(quote.dynamic_premium)
                : 'Link'}
            </div>
          </button>
        ))}
      </div>

      {/* Premium Details */}
      {quote && (
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700 space-y-4">
          {/* Price Breakdown */}
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-gray-600 dark:text-gray-400">Base Price ({quote.plan_type})</span>
              <span className="font-semibold text-gray-900 dark:text-white">{formatCurrency(quote.base_premium)}</span>
            </div>

            {quote.discount_applied > 0 && (
              <div className="flex justify-between items-center text-green-600 dark:text-green-400">
                <span className="flex items-center gap-2">
                  <TrendingDown className="w-4 h-4" />
                  Discount
                </span>
                <span className="font-semibold">-{formatCurrency(quote.discount_applied)}</span>
              </div>
            )}

            <div className="border-t border-gray-200 dark:border-gray-700 pt-3 flex justify-between items-center">
              <span className="font-semibold text-gray-900 dark:text-white">Your Premium</span>
              <span className="text-xl font-bold text-gigkavach-orange">{formatCurrency(quote.dynamic_premium)}</span>
            </div>
          </div>

          {/* Discount Percentage */}
          {quote.discount_applied > 0 && (
            <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-3 border border-green-200 dark:border-green-800">
              <p className="text-sm font-semibold text-green-900 dark:text-green-200">
                ✓ You're saving {premiumAPI.getDiscountPercentage(quote.base_premium, quote.discount_applied)}%
              </p>
            </div>
          )}

          {/* Bonus Coverage */}
          {quote.bonus_coverage_hours > 0 && (
            <div className="bg-amber-50 dark:bg-amber-900/20 rounded-lg p-3 border border-amber-200 dark:border-amber-800">
              <div className="flex items-center gap-2">
                <Zap className="w-5 h-5 text-amber-600 dark:text-amber-400" />
                <div>
                  <p className="text-sm font-semibold text-amber-900 dark:text-amber-200">Bonus Coverage Active</p>
                  <p className="text-xs text-amber-800 dark:text-amber-300">+{quote.bonus_coverage_hours} hours coverage in high-risk zones</p>
                </div>
              </div>
            </div>
          )}

          {/* Risk Factors */}
          <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4 space-y-2">
            <p className="text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase">Risk Factors</p>
            
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <p className="text-gray-600 dark:text-gray-400">Your GigScore</p>
                <p className="font-semibold text-gray-900 dark:text-white">{quote.insights?.gig_score || 'N/A'} / 100</p>
              </div>
              
              <div>
                <p className="text-gray-600 dark:text-gray-400">Zone Risk</p>
                <p className={`font-semibold ${quote.insights?.forecasted_zone_risk === 'High' ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
                  {quote.insights?.forecasted_zone_risk || 'Normal'}
                </p>
              </div>

              <div className="col-span-2">
                <p className="text-gray-600 dark:text-gray-400">Location</p>
                <p className="font-semibold text-gray-900 dark:text-white">{quote.insights?.primary_zone || 'N/A'}</p>
              </div>
            </div>
          </div>

          {/* Explanation */}
          {quote.explanation && (
            <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3 border border-blue-200 dark:border-blue-800">
              <p className="text-sm text-blue-900 dark:text-blue-200">
                <span className="font-semibold">Why this price? </span>
                {quote.explanation}
              </p>
            </div>
          )}

          {/* Action Button */}
          <button className="w-full bg-gradient-to-r from-gigkavach-orange to-orange-600 hover:shadow-lg text-white font-semibold py-3 rounded-lg transition-all flex items-center justify-center gap-2 mt-4">
            <CheckCircle className="w-5 h-5" />
            Confirm & Continue
          </button>
        </div>
      )}
    </div>
  );
}
