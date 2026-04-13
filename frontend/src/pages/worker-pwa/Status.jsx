import { useEffect, useState } from 'react';
import { ArrowLeft, AlertTriangle, Zap, Cloud, Wind, TrendingUp, Loader2, MapPin } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { dciAPI } from '../../api/dci';

/**
 * Worker Status Page (PWA)
 * Displays current zone DCI, weather conditions, and payout trigger status
 */
export function WorkerStatus() {
  const navigate = useNavigate();
  const [dciData, setDciData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Fetch DCI data for worker's primary zone
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        setLoading(true);
        // TODO: Get worker's pincode from auth context
        const primaryPincode = localStorage.getItem('workerPincode') || '560001';
        
        const data = await dciAPI.getByPincode(primaryPincode);
        setDciData(data);
      } catch (err) {
        console.error('[WORKER_STATUS] Error:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchStatus();
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const primaryPincode = localStorage.getItem('workerPincode') || '560001';
      const data = await dciAPI.getByPincode(primaryPincode);
      setDciData(data);
    } catch (err) {
      console.error('[WORKER_STATUS] Refresh error:', err);
    } finally {
      setRefreshing(false);
    }
  };

  const getSeverityColor = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'critical':
      case 'catastrophic':
        return { bg: 'bg-red-50 dark:bg-red-900/20', border: 'border-red-200 dark:border-red-800', text: 'text-red-900 dark:text-red-100', badge: 'bg-red-500' };
      case 'high':
        return { bg: 'bg-orange-50 dark:bg-orange-900/20', border: 'border-orange-200 dark:border-orange-800', text: 'text-orange-900 dark:text-orange-100', badge: 'bg-orange-500' };
      case 'moderate':
        return { bg: 'bg-yellow-50 dark:bg-yellow-900/20', border: 'border-yellow-200 dark:border-yellow-800', text: 'text-yellow-900 dark:text-yellow-100', badge: 'bg-yellow-500' };
      case 'low':
      default:
        return { bg: 'bg-green-50 dark:bg-green-900/20', border: 'border-green-200 dark:border-green-800', text: 'text-green-900 dark:text-green-100', badge: 'bg-green-500' };
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gigkavach-navy dark:to-gray-900 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-gigkavach-orange animate-spin mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">Loading zone status...</p>
        </div>
      </div>
    );
  }

  const severityInfo = getSeverityColor(dciData?.severity);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gigkavach-navy dark:to-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 py-4 flex items-center justify-between">
          <button
            onClick={() => navigate(-1)}
            className="flex items-center gap-2 text-gigkavach-orange hover:text-orange-600"
          >
            <ArrowLeft className="w-5 h-5" />
            <span className="font-semibold">Back</span>
          </button>
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">Zone Status</h1>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="px-3 py-1 rounded-lg bg-gigkavach-orange hover:bg-orange-600 text-white font-semibold disabled:opacity-50 transition-all"
          >
            {refreshing ? 'Updating...' : 'Refresh'}
          </button>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
        {dciData ? (
          <>
            {/* Current DCI Status */}
            <div className={`rounded-2xl shadow-lg overflow-hidden border-2 ${severityInfo.border}`}>
              <div className={`bg-gradient-to-r ${severityInfo.bg} p-8`}>
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-sm font-semibold text-gray-600 dark:text-gray-400 uppercase mb-2">
                      Current DCI Score
                    </p>
                    <div className="flex items-baseline gap-4">
                      <p className="text-6xl font-bold text-gray-900 dark:text-white">
                        {Math.round(dciData.current_dci || 0)}
                      </p>
                      <p className="text-xl text-gray-700 dark:text-gray-300">/ 100</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className={`inline-block px-4 py-2 rounded-full font-bold text-white text-sm ${severityInfo.badge}`}>
                      {(dciData.severity || 'Low').toUpperCase()}
                    </div>
                  </div>
                </div>
              </div>

              {/* Status Info */}
              <div className="p-6 bg-white dark:bg-gray-800 space-y-4">
                {dciData.payout_triggered && (
                  <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4 flex items-start gap-3">
                    <Zap className="w-5 h-5 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="font-semibold text-green-900 dark:text-green-200">✓ Payout Automatically Triggered</p>
                      <p className="text-sm text-green-700 dark:text-green-300 mt-1">Your automatic payout has been queued for processing</p>
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                    <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Zone</p>
                    <p className="text-lg font-bold text-gray-900 dark:text-white">{dciData.pincode}</p>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                    <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">City</p>
                    <p className="text-lg font-bold text-gray-900 dark:text-white">{dciData.city || 'Unknown'}</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Components Breakdown */}
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-8">
              <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-6 flex items-center gap-2">
                <TrendingUp className="w-6 h-6 text-gigkavach-orange" />
                Risk Components
              </h3>

              <div className="space-y-4">
                {dciData.components && Object.entries(dciData.components).map(([key, value]) => {
                  const percentage = Math.min(Math.round((value / 100) * 100), 100);
                  const isHigh = percentage > 70;
                  
                  return (
                    <div key={key} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <p className="font-semibold text-gray-900 dark:text-white capitalize">{key}</p>
                        <p className={`font-bold ${isHigh ? 'text-orange-600 dark:text-orange-400' : 'text-green-600 dark:text-green-400'}`}>
                          {Math.round(value)}
                        </p>
                      </div>
                      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                        <div
                          className={`h-full rounded-full transition-all ${
                            isHigh ? 'bg-orange-500' : 'bg-green-500'
                          }`}
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* City Weights Info */}
            {dciData.city_weights && (
              <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-8">
                <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-6 flex items-center gap-2">
                  <Cloud className="w-6 h-6 text-gigkavach-orange" />
                  How Your Zone DCI is Calculated
                </h3>

                <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                  Your city ({dciData.city}) weighs risk components differently based on local climate patterns
                </p>

                <div className="grid grid-cols-2 gap-3">
                  {Object.entries(dciData.city_weights).map(([key, weight]) => (
                    <div
                      key={key}
                      className="bg-gray-50 dark:bg-gray-700 p-3 rounded-lg border border-gray-200 dark:border-gray-600"
                    >
                      <p className="text-xs text-gray-600 dark:text-gray-400 capitalize mb-1">{key}</p>
                      <p className="font-bold text-gray-900 dark:text-white">{(weight * 100).toFixed(0)}%</p>
                      <div className="w-full bg-gray-300 dark:bg-gray-600 rounded-full h-1 mt-2">
                        <div
                          className="h-full rounded-full bg-gigkavach-orange"
                          style={{ width: `${weight * 100}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Last Updated */}
            <div className="text-center text-sm text-gray-500 dark:text-gray-400">
              Last updated: {new Date().toLocaleTimeString()}
            </div>
          </>
        ) : (
          <div className="bg-red-50 dark:bg-red-900/20 rounded-2xl p-8 border border-red-200 dark:border-red-800 text-center">
            <AlertTriangle className="w-12 h-12 text-red-600 dark:text-red-400 mx-auto mb-4" />
            <p className="font-semibold text-red-900 dark:text-red-200">Unable to Load Zone Data</p>
            <p className="text-sm text-red-700 dark:text-red-300 mt-2">Please try refreshing or contact support</p>
          </div>
        )}
      </div>
    </div>
  );
}
