import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { dciAPI } from '../../api/dci.js';
import { workerAPI } from '../../api/workers.js';

/**
 * StatusShare — Token-authenticated real-time zone status view
 * 
 * Displays current zone DCI readings and component breakdown.
 * Updates every 30 seconds to reflect real-time changes.
 * 
 * Route: /link/:shareToken/status
 */

export default function StatusShare() {
  const { shareToken } = useParams();
  const navigate = useNavigate();

  const [workerData, setWorkerData] = useState(null);
  const [dciData, setDciData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(new Date());

  useEffect(() => {
    const fetchStatusData = async () => {
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

        // Step 2: Fetch worker data to get zone/pincode
        const workerResponse = await workerAPI.getById(workerId);
        setWorkerData(workerResponse);

        // Step 3: Fetch DCI data for worker's zone/pincode
        let dciResponse;
        if (workerResponse.zone) {
          dciResponse = await dciAPI.getDCIByZone(workerResponse.zone);
        } else if (workerResponse.pincode) {
          dciResponse = await dciAPI.getDCIByPincode(workerResponse.pincode);
        } else {
          throw new Error('Worker zone/pincode not found');
        }

        setDciData(dciResponse);
        setLastUpdated(new Date());
        setIsLoading(false);
      } catch (err) {
        console.error('[StatusShare] Error:', err);
        setError(err.message || 'Failed to load status');
        setIsLoading(false);
      }
    };

    fetchStatusData();

    // Set up auto-refresh every 30 seconds
    const interval = setInterval(fetchStatusData, 30000);
    return () => clearInterval(interval);
  }, [shareToken]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading status...</p>
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

  if (!dciData) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-center">
          <p className="text-gray-600">No status data available</p>
        </div>
      </div>
    );
  }

  // Overall DCI score (0-100)
  const overallDCI = dciData.composite_score || 50;
  const dciStatus = overallDCI > 70 ? '🔴 High Disruption' :
                   overallDCI > 40 ? '🟡 Medium Disruption' :
                   '🟢 Low Disruption';

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Zone Status</h1>
              {workerData?.zone && <p className="text-gray-600">{workerData.zone}</p>}
            </div>
            <button
              onClick={() => navigate('/')}
              className="text-blue-600 hover:underline"
            >
              Home
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-2">
            ⏱️ Last updated: {lastUpdated.toLocaleTimeString()} (refreshes every 30 sec)
          </p>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Overall DCI Score */}
        <div className="bg-white rounded-lg shadow-md p-8 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-6">Disruption Composite Index (DCI)</h2>
          <div className="flex items-center justify-between">
            {/* Large DCI Display */}
            <div className="flex items-center">
              <div className="relative w-32 h-32">
                <svg className="transform -rotate-90 w-32 h-32">
                  <circle cx="64" cy="64" r="56" fill="none" stroke="#e5e7eb" strokeWidth="6" />
                  <circle
                    cx="64"
                    cy="64"
                    r="56"
                    fill="none"
                    stroke={overallDCI > 70 ? '#ef4444' : overallDCI > 40 ? '#eab308' : '#22c55e'}
                    strokeWidth="6"
                    strokeDasharray={`${(overallDCI / 100) * 351.86} 351.86`}
                    strokeLinecap="round"
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="text-center">
                    <div className="text-4xl font-bold text-gray-900">{overallDCI.toFixed(0)}</div>
                    <div className="text-xs text-gray-500 mt-1">/ 100</div>
                  </div>
                </div>
              </div>

              <div className="ml-8">
                <p className="text-2xl font-semibold text-gray-900 mb-2">{dciStatus}</p>
                <p className="text-sm text-gray-600 mb-4">
                  This score represents how disrupted your zone is right now.
                </p>
                <div className="bg-blue-50 border border-blue-200 rounded p-3">
                  <p className="text-xs text-blue-700">
                    💡 Higher DCI = More disruptions = Higher insurance payout trigger threshold
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Component Breakdown */}
        <div className="grid grid-cols-2 gap-6 mb-6">
          {/* Weather Component */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">🌤️ Weather Impact</h3>
            <div className="mb-4">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium text-gray-600">Score</span>
                <span className="text-2xl font-bold text-blue-600">
                  {dciData.weather_component?.toFixed(1) || 'N/A'}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-500 h-2 rounded-full"
                  style={{ width: `${(dciData.weather_component || 0) / 100 * 100}%` }}
                ></div>
              </div>
            </div>
            <p className="text-sm text-gray-600">{dciData.weather_status || 'Monitoring weather patterns'}</p>
          </div>

          {/* Air Quality Component */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">💨 Air Quality</h3>
            <div className="mb-4">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium text-gray-600">AQI</span>
                <span className="text-2xl font-bold text-orange-600">
                  {dciData.aqi_component?.toFixed(1) || 'N/A'}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-orange-500 h-2 rounded-full"
                  style={{ width: `${(dciData.aqi_component || 0) / 500 * 100}%` }}
                ></div>
              </div>
            </div>
            <p className="text-sm text-gray-600">{dciData.aqi_status || 'Air quality within normal range'}</p>
          </div>

          {/* Heat Index Component */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">🔥 Heat Index</h3>
            <div className="mb-4">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium text-gray-600">Heat</span>
                <span className="text-2xl font-bold text-red-600">
                  {dciData.heat_component?.toFixed(1) || 'N/A'}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-red-500 h-2 rounded-full"
                  style={{ width: `${(dciData.heat_component || 0) / 50 * 100}%` }}
                ></div>
              </div>
            </div>
            <p className="text-sm text-gray-600">Temperature and humidity conditions</p>
          </div>

          {/* Social Impact Component */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">👥 Social Impact</h3>
            <div className="mb-4">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium text-gray-600">Score</span>
                <span className="text-2xl font-bold text-purple-600">
                  {dciData.social_component?.toFixed(1) || 'N/A'}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-purple-500 h-2 rounded-full"
                  style={{ width: `${(dciData.social_component || 0) / 100 * 100}%` }}
                ></div>
              </div>
            </div>
            <p className="text-sm text-gray-600">Social event disruption impact</p>
          </div>
        </div>

        {/* Alert Info */}
        {dciData.alert_triggered && (
          <div className="bg-red-50 border border-red-300 rounded-lg p-6 mb-6">
            <h3 className="font-semibold text-red-900 mb-2">🚨 Alerts Active</h3>
            <p className="text-red-700 text-sm">
              Current zone conditions have triggered disruption alerts. Insurance coverage assessment in progress.
            </p>
          </div>
        )}

        {/* Updated Indicator */}
        <div className="text-center text-xs text-gray-500">
          <p>This data is updated every 5 minutes by GigKavach monitoring systems</p>
        </div>
      </div>
    </div>
  );
}
