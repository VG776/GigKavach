import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { workerAPI } from '../../api/workers.js';
import { dciAPI } from '../../api/dci.js';
import { premiumAPI } from '../../api/premium.js';

/**
 * ProfileShare — Token-authenticated shared profile view
 * 
 * This page displays a worker's profile data when accessed via a shareable link.
 * Unlike the full Profile.jsx, this is read-only and includes expiry messaging.
 * 
 * Route: /link/:shareToken/profile
 */

export default function ProfileShare() {
  const { shareToken } = useParams();
  const navigate = useNavigate();

  const [workerData, setWorkerData] = useState(null);
  const [dciData, setDciData] = useState(null);
  const [premiumData, setPremiumData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchProfileData = async () => {
      try {
        // Step 1: Verify token to get worker_id
        const verifyResponse = await fetch('/api/v1/share-tokens/verify', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ share_token: shareToken }),
        });

        if (!verifyResponse.ok) {
          throw new Error('Invalid or expired share link');
        }

        const tokenData = await verifyResponse.json();
        const workerId = tokenData.worker_id;

        // Step 2: Fetch worker profile
        const workerResponse = await workerAPI.getById(workerId);
        setWorkerData(workerResponse);

        // Step 3: Fetch DCI data for worker zone
        if (workerResponse.zone) {
          try {
            const dciResponse = await dciAPI.getDCIByZone(workerResponse.zone);
            setDciData(dciResponse);
          } catch (err) {
            console.error('[ProfileShare] DCI fetch error:', err);
            // DCI is optional, don't fail the page
          }
        }

        // Step 4: Fetch premium quote
        // TODO: Premium data fetch temporarily disabled
        // May be causing 422 validation errors
        // try {
        //   if (workerId && workerId.trim() !== '') {
        //     const planTier = workerResponse?.plan || 'basic';
        //     const premiumResponse = await premiumAPI.getQuote(workerId, planTier);
        //     setPremiumData(premiumResponse);
        //   }
        // } catch (err) {
        //   console.error('[ProfileShare] Premium fetch error:', err);
        //   // Premium is optional
        // }

        setIsLoading(false);
      } catch (err) {
        console.error('[ProfileShare] Error:', err);
        setError(err.message || 'Failed to load profile');
        setIsLoading(false);
      }
    };

    if (shareToken) {
      fetchProfileData();
    }
  }, [shareToken]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading profile...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full text-center">
          <div className="text-red-600 text-5xl mb-4">⚠️</div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Error</h1>
          <p className="text-gray-600 mb-6">{error}</p>
          <button
            onClick={() => navigate('/')}
            className="inline-block bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors"
          >
            Go Home
          </button>
        </div>
      </div>
    );
  }

  if (!workerData) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-center">
          <p className="text-gray-600">No profile data available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-2xl mx-auto px-4 py-6">
          <div className="flex justify-between items-center">
            <h1 className="text-2xl font-bold text-gray-900">My Profile</h1>
            <button
              onClick={() => navigate('/')}
              className="text-blue-600 hover:underline"
            >
              Home
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-2">
            📱 This is a readonly shared link. <button onClick={() => navigate('/auth/login')} className="text-blue-600 hover:underline">Sign in for full access</button>
          </p>
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-4 py-8">
        {/* Worker Info Card */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Worker Details</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-500">Name</p>
              <p className="font-semibold text-gray-900">{workerData.name || 'N/A'}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Phone</p>
              <p className="font-semibold text-gray-900">{workerData.phone || 'N/A'}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Zone</p>
              <p className="font-semibold text-gray-900">{workerData.zone || 'N/A'}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Pincode</p>
              <p className="font-semibold text-gray-900">{workerData.pincode || 'N/A'}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Platform</p>
              <p className="font-semibold text-gray-900">{workerData.platform || 'N/A'}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Status</p>
              <p className="font-semibold text-gray-900">
                <span className={'px-2 py-1 rounded text-xs font-semibold ' + 
                  (workerData.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800')}>
                  {workerData.is_active ? 'Active' : 'Inactive'}
                </span>
              </p>
            </div>
          </div>
        </div>

        {/* GigScore Card */}
        {workerData.gig_score !== undefined && (
          <div className="bg-white rounded-lg shadow-md p-6 mb-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">GigScore</h2>
            <div className="flex items-center">
              <div className="relative w-24 h-24">
                <svg className="transform -rotate-90 w-24 h-24">
                  <circle cx="48" cy="48" r="40" fill="none" stroke="#e5e7eb" strokeWidth="4" />
                  <circle
                    cx="48"
                    cy="48"
                    r="40"
                    fill="none"
                    stroke="#3b82f6"
                    strokeWidth="4"
                    strokeDasharray={`${(workerData.gig_score / 100) * 251.2} 251.2`}
                    strokeLinecap="round"
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-3xl font-bold text-gray-900">{workerData.gig_score}</span>
                </div>
              </div>
              <div className="ml-6">
                <p className="text-sm text-gray-500">Overall Performance Score</p>
                <p className="text-gray-600 text-sm mt-2">
                  Based on shift consistency, earnings, and platform ratings.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* DCI Components Card */}
        {dciData && (
          <div className="bg-white rounded-lg shadow-md p-6 mb-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Zone Status (DCI Components)</h2>
            <div className="grid grid-cols-2 gap-4">
              <div className="border border-gray-200 rounded p-4">
                <p className="text-sm text-gray-500">Weather Impact</p>
                <p className="text-2xl font-bold text-blue-600">{dciData.weather_component?.toFixed(1) || 'N/A'}</p>
                <p className="text-xs text-gray-500 mt-1">{dciData.weather_status || ''}</p>
              </div>
              <div className="border border-gray-200 rounded p-4">
                <p className="text-sm text-gray-500">Air Quality</p>
                <p className="text-2xl font-bold text-orange-600">{dciData.aqi_component?.toFixed(1) || 'N/A'}</p>
                <p className="text-xs text-gray-500 mt-1">{dciData.aqi_status || ''}</p>
              </div>
              <div className="border border-gray-200 rounded p-4">
                <p className="text-sm text-gray-500">Heat Index</p>
                <p className="text-2xl font-bold text-red-600">{dciData.heat_component?.toFixed(1) || 'N/A'}</p>
              </div>
              <div className="border border-gray-200 rounded p-4">
                <p className="text-sm text-gray-500">Social Impact</p>
                <p className="text-2xl font-bold text-purple-600">{dciData.social_component?.toFixed(1) || 'N/A'}</p>
              </div>
            </div>
          </div>
        )}

        {/* Premium Card */}
        {premiumData && (
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg shadow-md p-6 mb-6 border border-blue-200">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">💎 Premium Quote</h2>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <p className="text-sm text-gray-600">Base Price</p>
                <p className="text-2xl font-bold text-gray-900">₹{premiumData.base_price?.toFixed(0) || 'N/A'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Discount</p>
                <p className="text-2xl font-bold text-green-600">-₹{premiumData.discount_amount?.toFixed(0) || 'N/A'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Final Price</p>
                <p className="text-2xl font-bold text-blue-600">₹{premiumData.final_price?.toFixed(0) || 'N/A'}</p>
              </div>
            </div>
            {premiumData.bonus_hours && (
              <p className="text-sm text-purple-700 mt-4">
                ⏳ Includes {premiumData.bonus_hours} bonus coverage hours
              </p>
            )}
          </div>
        )}

        {/* Sign-In CTA */}
        <div className="bg-blue-50 rounded-lg border border-blue-200 p-6 text-center">
          <h3 className="font-semibold text-gray-900 mb-2">Want More Details?</h3>
          <p className="text-gray-600 text-sm mb-4">
            Sign in to GigKavach to see your transaction history, real-time payouts, and access your full profile.
          </p>
          <button
            onClick={() => navigate('/auth/login')}
            className="inline-block bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors"
          >
            Sign In
          </button>
        </div>
      </div>
    </div>
  );
}
