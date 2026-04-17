import { useEffect, useState } from 'react';
import { ArrowLeft, FileText, DollarSign, Loader2, AlertCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { payoutAPI } from '../../api/payouts';
import { formatCurrency, formatDate } from '../../utils/formatters';

/**
 * Worker History Page (PWA)
 * Displays payout history, claims, and transactions
 */
export function WorkerHistory() {
  const navigate = useNavigate();
  const [transactions, setTransactions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('payouts');

  // Fetch payout history
  useEffect(() => {
    const fetchHistory = async () => {
      try {
        setLoading(true);
        // Fetch payouts sorted by date, descending
        const data = await payoutAPI.getAll({ 
          limit: 100, 
          sort: '-triggered_at' 
        });
        
        // Transform data for display
        const formatted = (data?.data || data?.payouts || data || []).map((p: any) => ({
          id: p.id,
          type: 'payout',
          amount: p.final_amount || p.amount,
          status: p.status,
          date: new Date(p.triggered_at || p.created_at),
          reason: p.dci_score ? `DCI Event (${Math.round(p.dci_score)})` : 'Weekly Payout',
          zone: p.pincode || 'Unknown',
        }));
        
        setTransactions(formatted);
      } catch (err) {
        console.error('[WORKER_HISTORY] Error:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, []);

  const getStatusBadge = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'paid':
      case 'completed':
      case 'success':
        return { bg: 'bg-green-100 dark:bg-green-900/30', text: 'text-green-800 dark:text-green-200', label: 'Paid' };
      case 'pending':
        return { bg: 'bg-yellow-100 dark:bg-yellow-900/30', text: 'text-yellow-800 dark:text-yellow-200', label: 'Pending' };
      case 'failed':
        return { bg: 'bg-red-100 dark:bg-red-900/30', text: 'text-red-800 dark:text-red-200', label: 'Failed' };
      default:
        return { bg: 'bg-gray-100 dark:bg-gray-700', text: 'text-gray-800 dark:text-gray-200', label: status || 'Unknown' };
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gigkavach-navy dark:to-gray-900 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-gigkavach-orange animate-spin mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">Loading your history...</p>
        </div>
      </div>
    );
  }

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
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">Transaction History</h1>
          <div className="w-20" /> {/* spacer */}
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 py-6">
        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-white dark:bg-gray-800 rounded-xl p-4 text-center shadow-sm">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Total Payouts</p>
            <p className="text-2xl font-bold text-gigkavach-orange">
              {transactions.length}
            </p>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl p-4 text-center shadow-sm">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Total Received</p>
            <p className="text-2xl font-bold text-green-600">
              {formatCurrency(
                transactions
                  .filter((t) => t.status === 'paid' || t.status === 'completed')
                  .reduce((sum, t) => sum + (t.amount || 0), 0)
              )}
            </p>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl p-4 text-center shadow-sm">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Pending</p>
            <p className="text-2xl font-bold text-yellow-600">
              {transactions.filter((t) => t.status === 'pending').length}
            </p>
          </div>
        </div>

        {/* Transactions List */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg overflow-hidden">
          <div className="border-b border-gray-200 dark:border-gray-700">
            <div className="flex">
              <button
                onClick={() => setActiveTab('payouts')}
                className={`flex-1 px-6 py-4 font-semibold transition-all border-b-2 ${
                  activeTab === 'payouts'
                    ? 'border-gigkavach-orange text-gigkavach-orange'
                    : 'border-transparent text-gray-600 dark:text-gray-400'
                }`}
              >
                <div className="flex items-center justify-center gap-2">
                  <DollarSign className="w-5 h-5" />
                  Payouts
                </div>
              </button>
              <button
                onClick={() => setActiveTab('claims')}
                className={`flex-1 px-6 py-4 font-semibold transition-all border-b-2 ${
                  activeTab === 'claims'
                    ? 'border-gigkavach-orange text-gigkavach-orange'
                    : 'border-transparent text-gray-600 dark:text-gray-400'
                }`}
              >
                <div className="flex items-center justify-center gap-2">
                  <FileText className="w-5 h-5" />
                  Claims
                </div>
              </button>
            </div>
          </div>

          <div className="p-4">
            {activeTab === 'payouts' ? (
              transactions.length > 0 ? (
                <div className="space-y-3">
                  {transactions.map((tx) => (
                    <div
                      key={tx.id}
                      className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"
                    >
                      <div className="flex items-center gap-4 flex-1">
                        <div className="w-12 h-12 rounded-full bg-gradient-to-br from-green-400 to-green-600 flex items-center justify-center text-white">
                          <DollarSign className="w-6 h-6" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="font-semibold text-gray-900 dark:text-white">{tx.reason}</p>
                          <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                            {formatDate(tx.date)} • Zone: {tx.zone}
                          </p>
                        </div>
                      </div>
                      <div className="text-right ml-4">
                        <p className="font-bold text-green-600 dark:text-green-400 text-lg">
                          {formatCurrency(tx.amount)}
                        </p>
                        <span className={`text-xs font-semibold px-2 py-1 rounded mt-1 inline-block ${getStatusBadge(tx.status).bg} ${getStatusBadge(tx.status).text}`}>
                          {getStatusBadge(tx.status).label}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12">
                  <DollarSign className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
                  <p className="text-gray-600 dark:text-gray-400">No payouts yet</p>
                </div>
              )
            ) : (
              <div className="text-center py-12">
                <FileText className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
                <p className="text-gray-600 dark:text-gray-400">No claims filed</p>
              </div>
            )}
          </div>
        </div>

        {/* Help Text */}
        <div className="bg-blue-50 dark:bg-blue-900/20 rounded-xl p-4 mt-6 border border-blue-200 dark:border-blue-800">
          <div className="flex gap-3">
            <AlertCircle className=" w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-blue-900 dark:text-blue-200">
              <p className="font-semibold mb-1">Automatic Payouts</p>
              <p>When DCI exceeds 65 in your zone, you automatically receive a payout. No claim needed!</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default WorkerHistory;
