import { useEffect, useState } from 'react';
import { ArrowLeft, User, MapPin, DollarSign, Zap, TrendingUp, AlertCircle, Loader2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { workerAPI } from '../../api/workers';
import { premiumAPI } from '../../api/premium';
import { formatCurrency } from '../../utils/formatters';
import { PremiumQuote } from '../../components/premium/PremiumQuote';

/**
 * Worker Profile Page (PWA)
 * Displays worker's personal information, GigScore, premium, and metrics
 */
export function WorkerProfile() {
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedPlan, setSelectedPlan] = useState('basic');

  // Fetch worker profile
  useEffect(() => {
    const fetchProfile = async () => {
      try {
        setLoading(true);
        // TODO: Get worker ID from auth context
        const workerId = localStorage.getItem('workerId') || 'current';
        const data = await workerAPI.getById(workerId);
        
        setProfile(data.worker || data);
        setSelectedPlan(
          (data.policy?.plan || data.worker?.plan || 'basic')
            .toLowerCase()
            .replace('shield ', '')
        );
      } catch (err) {
        console.error('[WORKER_PROFILE] Error:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchProfile();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gigkavach-navy dark:to-gray-900 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-gigkavach-orange animate-spin mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">Loading your profile...</p>
        </div>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gigkavach-navy dark:to-gray-900 p-4">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-gigkavach-orange hover:text-orange-600 mb-4"
        >
          <ArrowLeft className="w-5 h-5" />
          Back
        </button>
        <div className="bg-red-50 dark:bg-red-900/20 rounded-xl p-6 border border-red-200 dark:border-red-800">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-6 h-6 text-red-600 dark:text-red-400" />
            <div>
              <p className="font-semibold text-red-900 dark:text-red-200">Unable to Load Profile</p>
              <p className="text-sm text-red-700 dark:text-red-300">Please try again or contact support</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gigkavach-navy dark:to-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-3xl mx-auto px-4 py-4 flex items-center justify-between">
          <button
            onClick={() => navigate(-1)}
            className="flex items-center gap-2 text-gigkavach-orange hover:text-orange-600"
          >
            <ArrowLeft className="w-5 h-5" />
            <span className="font-semibold">Back</span>
          </button>
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">Your Profile</h1>
          <div className="w-20" /> {/* spacer */}
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
        {/* Profile Card */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg overflow-hidden">
          <div className="bg-gradient-to-r from-gigkavach-orange to-orange-600 p-8 text-white">
            <div className="flex items-center gap-6">
              <div className="w-20 h-20 rounded-full bg-white/20 flex items-center justify-center text-4xl font-bold">
                {profile.name
                  ?.split(' ')
                  .map((n) => n[0])
                  .join('')
                  .slice(0, 2)
                  .toUpperCase() || '?'}
              </div>
              <div>
                <h2 className="text-3xl font-bold">{profile.name || 'Worker'}</h2>
                <p className="text-white/80 mt-1">Member since 2026</p>
              </div>
            </div>
          </div>

          <div className="p-8 space-y-6">
            {/* GigScore & Status */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/20 dark:to-gigkavach-navy p-6 rounded-xl border border-blue-200 dark:border-blue-800">
                <div className="flex items-center gap-2 mb-2">
                  <TrendingUp className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                  <p className="text-sm font-semibold text-blue-900 dark:text-blue-200">GigScore</p>
                </div>
                <p className="text-4xl font-bold text-blue-600 dark:text-blue-400">
                  {profile.gig_score || '85'}
                </p>
                <p className="text-xs text-blue-700 dark:text-blue-300 mt-1">Out of 100</p>
              </div>

              <div className="bg-gradient-to-br from-green-50 to-green-100 dark:from-green-900/20 dark:to-gigkavach-navy p-6 rounded-xl border border-green-200 dark:border-green-800">
                <div className="flex items-center gap-2 mb-2">
                  <Zap className="w-5 h-5 text-green-600 dark:text-green-400" />
                  <p className="text-sm font-semibold text-green-900 dark:text-green-200">Status</p>
                </div>
                <p className="text-2xl font-bold text-green-600 dark:text-green-400">
                  {profile.account_status === 'active' ? 'Active' : 'Inactive'}
                </p>
                <p className="text-xs text-green-700 dark:text-green-300 mt-1">Policy Status</p>
              </div>
            </div>

            {/* Contact Information */}
            <div className="space-y-3">
              <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <User className="w-5 h-5 text-gigkavach-orange" />
                Contact Information
              </h3>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded-lg">
                  <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Phone</p>
                  <p className="font-semibold text-gray-900 dark:text-white">{profile.phone || 'N/A'}</p>
                </div>
                <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded-lg">
                  <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">UPI ID</p>
                  <p className="font-semibold text-gray-900 dark:text-white font-mono text-xs">{profile.upi_id || 'N/A'}</p>
                </div>
              </div>
            </div>

            {/* Service Areas */}
            <div className="space-y-3">
              <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <MapPin className="w-5 h-5 text-gigkavach-orange" />
                Service Areas
              </h3>
              <div className="flex flex-wrap gap-2">
                {profile.pin_codes?.map((pin) => (
                  <span
                    key={pin}
                    className="bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200 px-3 py-1 rounded-full text-sm font-medium"
                  >
                    {pin}
                  </span>
                )) || <p className="text-gray-500 dark:text-gray-400 text-sm">No zones configured</p>}
              </div>
            </div>
          </div>
        </div>

        {/* Dynamic Premium Calculator */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-8">
          <div className="flex items-center gap-2 mb-6">
            <DollarSign className="w-6 h-6 text-gigkavach-orange" />
            <h3 className="text-xl font-bold text-gray-900 dark:text-white">Your Premium Quote</h3>
          </div>

          {profile.id && (
            <PremiumQuote
              workerId={profile.id}
              selectedPlan={selectedPlan}
              onPlanChange={setSelectedPlan}
            />
          )}
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl p-4 text-center shadow-sm">
            <p className="text-3xl font-bold text-gigkavach-orange">0</p>
            <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">Active Claims</p>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl p-4 text-center shadow-sm">
            <p className="text-3xl font-bold text-green-600">0</p>
            <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">Payouts Received</p>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl p-4 text-center shadow-sm">
            <p className="text-3xl font-bold text-blue-600">0</p>
            <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">Claims Filed</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default WorkerProfile;
