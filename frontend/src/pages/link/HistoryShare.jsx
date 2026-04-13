import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { payoutAPI } from '../../api/payouts.js';
import { workerAPI } from '../../api/workers.js';

/**
 * HistoryShare — Token-authenticated payout transaction history view
 * 
 * Displays worker's recent payouts, transaction status, and earning trends.
 * Read-only view accessible via shareable links.
 * 
 * Route: /link/:shareToken/history
 */

export default function HistoryShare() {
  const { shareToken } = useParams();
  const navigate = useNavigate();

  const [workerData, setWorkerData] = useState(null);
  const [payouts, setPayouts] = useState([]);
  const [stats, setStats] = useState({
    totalEarnings: 0,
    totalPayouts: 0,
    pendingAmount: 0,
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sortBy, setSortBy] = useState('date-desc');

  useEffect(() => {
    const fetchHistoryData = async () => {
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

        // Step 2: Fetch worker data
        const workerResponse = await workerAPI.getById(workerId);
        setWorkerData(workerResponse);

        // Step 3: Fetch payout history
        const payoutResponse = await payoutAPI.getAll({ worker_id: workerId });
        if (Array.isArray(payoutResponse)) {
          setPayouts(payoutResponse);
        } else if (payoutResponse.payouts) {
          setPayouts(payoutResponse.payouts);
        } else if (payoutResponse.data) {
          setPayouts(payoutResponse.data);
        }

        // Step 4: Calculate stats
        let totalEarnings = 0;
        let totalPayouts = 0;
        let pendingAmount = 0;

        payouts.forEach((payout) => {
          totalEarnings += payout.base_amount || 0;
          if (payout.status === 'completed' || payout.status === 'successful') {
            totalPayouts += payout.amount_paid || payout.final_amount || 0;
          } else if (payout.status === 'pending') {
            pendingAmount += payout.final_amount || 0;
          }
        });

        setStats({ totalEarnings, totalPayouts, pendingAmount });
        setIsLoading(false);
      } catch (err) {
        console.error('[HistoryShare] Error:', err);
        setError(err.message || 'Failed to load history');
        setIsLoading(false);
      }
    };

    if (shareToken) {
      fetchHistoryData();
    }
  }, [shareToken]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading history...</p>
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

  // Sort payouts based on selection
  const sortedPayouts = [...payouts].sort((a, b) => {
    const dateA = new Date(a.created_at);
    const dateB = new Date(b.created_at);

    if (sortBy === 'date-desc') return dateB - dateA;
    if (sortBy === 'date-asc') return dateA - dateB;
    if (sortBy === 'amount-high') return (b.final_amount || 0) - (a.final_amount || 0);
    if (sortBy === 'amount-low') return (a.final_amount || 0) - (b.final_amount || 0);
    return 0;
  });

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'completed':
      case 'successful':
        return 'bg-green-100 text-green-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'failed':
      case 'rejected':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <div className="flex justify-between items-center">
            <h1 className="text-2xl font-bold text-gray-900">Transaction History</h1>
            <button
              onClick={() => navigate('/')}
              className="text-blue-600 hover:underline"
            >
              Home
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Stats Cards */}
        <div className="grid grid-cols-3 gap-4 mb-8">
          <div className="bg-white rounded-lg shadow-md p-6">
            <p className="text-sm text-gray-500 mb-2">Total Earnings</p>
            <p className="text-3xl font-bold text-gray-900">₹{stats.totalEarnings.toFixed(0)}</p>
            <p className="text-xs text-gray-400 mt-2">All time</p>
          </div>
          <div className="bg-white rounded-lg shadow-md p-6">
            <p className="text-sm text-gray-500 mb-2">Paid Out</p>
            <p className="text-3xl font-bold text-green-600">₹{stats.totalPayouts.toFixed(0)}</p>
            <p className="text-xs text-gray-400 mt-2">Completed transfers</p>
          </div>
          <div className="bg-white rounded-lg shadow-md p-6">
            <p className="text-sm text-gray-500 mb-2">Pending</p>
            <p className="text-3xl font-bold text-yellow-600">₹{stats.pendingAmount.toFixed(0)}</p>
            <p className="text-xs text-gray-400 mt-2">Awaiting transfer</p>
          </div>
        </div>

        {/* Sort Controls */}
        <div className="bg-white rounded-lg shadow-md p-4 mb-6 flex justify-between items-center">
          <h2 className="text-lg font-semibold text-gray-900">Recent Transactions</h2>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="date-desc">Latest First</option>
            <option value="date-asc">Oldest First</option>
            <option value="amount-high">Highest Amount</option>
            <option value="amount-low">Lowest Amount</option>
          </select>
        </div>

        {/* Transactions List */}
        {sortedPayouts.length > 0 ? (
          <div className="space-y-4">
            {sortedPayouts.map((payout, index) => (
              <div key={payout.id || index} className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
                <div className="flex justify-between items-start mb-4">
                  <div className="flex-1">
                    <p className="font-semibold text-gray-900">
                      Payout #{payout.id?.substring(0, 8) || index + 1}
                    </p>
                    <p className="text-sm text-gray-500">
                      {new Date(payout.created_at).toLocaleDateString('en-IN', {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                      })}
                    </p>
                  </div>
                  <span
                    className={`px-3 py-1 rounded-full text-xs font-semibold ${getStatusColor(payout.status)}`}
                  >
                    {payout.status?.charAt(0).toUpperCase() + payout.status?.slice(1).toLowerCase() || 'Unknown'}
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-4 mb-4 pb-4 border-b border-gray-200">
                  <div>
                    <p className="text-xs text-gray-500">Base Amount</p>
                    <p className="text-lg font-semibold text-gray-900">₹{(payout.base_amount || 0).toFixed(0)}</p>
                  </div>
                  {payout.discount_amount > 0 && (
                    <div>
                      <p className="text-xs text-gray-500">Discount</p>
                      <p className="text-lg font-semibold text-green-600">-₹{(payout.discount_amount || 0).toFixed(0)}</p>
                    </div>
                  )}
                  <div>
                    <p className="text-xs text-gray-500">Final Amount</p>
                    <p className="text-lg font-bold text-blue-600">₹{(payout.final_amount || 0).toFixed(0)}</p>
                  </div>
                </div>

                {/* Details */}
                <div className="grid grid-cols-2 gap-4 text-sm">
                  {payout.payment_method && (
                    <div>
                      <p className="text-xs text-gray-500">Payment Method</p>
                      <p className="text-gray-900">{payout.payment_method}</p>
                    </div>
                  )}
                  {payout.utr && (
                    <div>
                      <p className="text-xs text-gray-500">Reference</p>
                      <p className="text-gray-900 font-mono text-xs">{payout.utr}</p>
                    </div>
                  )}
                  {payout.dci_triggered && (
                    <div>
                      <p className="text-xs text-gray-500">DCI Status</p>
                      <p className="text-orange-600 font-semibold">DCI Triggered ⚠️</p>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow-md p-12 text-center">
            <p className="text-gray-600">No transactions yet</p>
          </div>
        )}

        {/* Info Section */}
        <div className="bg-blue-50 rounded-lg border border-blue-200 p-6 mt-8">
          <h3 className="font-semibold text-gray-900 mb-2">📱 Access Full History</h3>
          <p className="text-gray-600 text-sm mb-4">
            Sign in to GigKavach to see detailed analytics, export your transaction history, and manage your account preferences.
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
