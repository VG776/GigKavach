import React, { useState, useMemo, useEffect } from 'react';
import { Zap, TrendingDown, DollarSign, CheckCircle, ChevronLeft, ChevronRight } from 'lucide-react';
import { formatCurrency, formatPercentage, formatDate } from '../utils/formatters';
import { Button } from '../components/common/Button';
import { RealTimePayoutFeed } from '../components/payouts/RealTimePayoutFeed';
import { WorkerModal } from '../components/workers/WorkerModal';
import { payoutAPI } from '../api/payouts';
import { workerAPI } from '../api/workers';

// Fallback mock data for when API is unavailable
const mockPayouts = [
  { id: 1, worker: 'Amit Patel', avatar: 'A', tier: 'Shield Pro', trigger: '🌧️ Heavy Rainfall · DCI 78', amount: 8500, coverage: 50, upiRef: 'GK2024001234', dateTime: new Date(Date.now() - 30 * 60000), status: 'paid', fraud: 'clean' },
];

export const Payouts = () => {
  const [activeTab, setActiveTab] = useState('all');
  const [isSimulationOpen, setIsSimulationOpen] = useState(false);
  const [simulationZone, setSimulationZone] = useState('Koramangala');
  const [simulationDisruption, setSimulationDisruption] = useState('rain');
  const [simulationDCI, setSimulationDCI] = useState(78);
  const [toastMessage, setToastMessage] = useState('');
  const [workerModalId, setWorkerModalId] = useState(null);
  const [workerModalOpen, setWorkerModalOpen] = useState(false);
  const [payouts, setPayouts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 5;
  const [liveStats, setLiveStats] = useState({
    totalDisbursedeThisWeek: 0,
    pending: 0,
    successRate: 98.2,
    avgProcessing: 4.2,
  });

  // Poll payouts every 5 seconds
  useEffect(() => {
    const fetchPayouts = async () => {
      try {
        setLoading(true);
        const res = await payoutAPI.getAll({ limit: 50 });
        
        // Transform API response to table format
        const apiPayouts = res?.data?.payouts || res?.payouts || [];
        console.log('API Payouts:', apiPayouts);
        
        // Get unique worker IDs and fetch ALL workers at once
        const uniqueWorkerIds = [...new Set(apiPayouts.map(p => p.worker_id).filter(Boolean))];
        console.log('Unique Worker IDs:', uniqueWorkerIds);
        
        const workerPlanMap = {};
        
        // Fetch all workers at once instead of one-by-one
        if (uniqueWorkerIds.length > 0) {
          try {
            const allWorkers = await workerAPI.getAll({ limit: 100 });
            console.log('All Workers Response:', allWorkers);
            
            // Backend returns { data: [...], total: ..., page: ..., totalPages: ... }
            const workers = allWorkers?.data || [];
            console.log('Workers Array:', workers);
            
            // Build map of worker ID to plan (backend already returns formatted plan text)
            workers.forEach(worker => {
              console.log(`Worker ${worker.id}: plan="${worker.plan}"`);
              workerPlanMap[worker.id] = worker.plan || 'Shield Basic';
            });
            
            console.log('Worker Plan Map:', workerPlanMap);
          } catch (err) {
            console.warn('Could not fetch workers:', err);
          }
        }
        
        const formatted = Array.isArray(apiPayouts) ? apiPayouts.map((p) => ({
          id: p.id,
          worker: p.worker_name || 'Unknown',
          avatar: p.worker_name
            ?.split(' ')
            .map((n) => n[0])
            .join('')
            .slice(0, 2)
            .toUpperCase() || '?',
          tier: workerPlanMap[p.worker_id] || 'Shield Basic',
          trigger: `DCI Event · ${p.dci_score || 'N/A'}`,
          amount: p.amount,
          coverage: Math.round((p.amount / (p.amount / (p.fraud_score ? 0.5 : 1))) * 100) || 50,
          upiRef: p.id.slice(0, 12).toUpperCase(),
          dateTime: new Date(p.timestamp),
          status: p.status === 'payout_sent' ? 'paid' : (p.status || 'processing'),
          fraud: p.fraud_score > 3 ? 'hard-block' : p.fraud_score > 1 ? 'soft-flag' : 'clean',
        })) : [];
        
        // Use REAL data from API - never fall back to mock data for table
        setPayouts(formatted);

        // Calculate total disbursed this week (last 7 days, only paid status)
        const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
        const thisWeekPayouts = formatted.filter(p => new Date(p.dateTime) >= sevenDaysAgo && p.status === 'paid');
        const totalThisWeek = thisWeekPayouts.reduce((sum, p) => sum + (p.amount || 0), 0);

        // Update live stats
        setLiveStats({
          totalDisbursedeThisWeek: totalThisWeek,
          pending: formatted.filter(p => p.status === 'pending').reduce((sum, p) => sum + (p.amount || 0), 0),
          successRate: formatted.length > 0 ? (formatted.filter(p => p.status === 'paid').length / formatted.length) * 100 : 98.2,
          avgProcessing: 4.2,
        });
      } catch (err) {
        console.error('Error fetching payouts:', err);
        // On error, show empty table (no mock fallback)
        setPayouts([]);
        setLiveStats({
          totalDisbursedeThisWeek: 0,
          pending: 0,
          successRate: 98.2,
          avgProcessing: 4.2,
        });
      } finally {
        setLoading(false);
      }
    };

    fetchPayouts();
    const interval = setInterval(fetchPayouts, 20000); // Poll every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const handleSimulation = () => {
    setToastMessage(`✓ Simulation triggered · 34 workers eligible · Payouts queued`);
    setIsSimulationOpen(false);
    setTimeout(() => setToastMessage(''), 4000);
  };

  const getStatusColor = (status) => {
    const colors = {
      paid: { bg: 'bg-green-100 dark:bg-green-900', text: 'text-green-900 dark:text-green-100', border: 'border-green-300 dark:border-green-700' },
      pending: { bg: 'bg-amber-100 dark:bg-amber-900', text: 'text-amber-900 dark:text-amber-100', border: 'border-amber-300 dark:border-amber-700' },
      failed: { bg: 'bg-red-100 dark:bg-red-900', text: 'text-red-900 dark:text-red-100', border: 'border-red-300 dark:border-red-700' },
    };
    return colors[status] || colors.pending;
  };

  const getTierColor = (tier) => {
    const colors = {
      'Shield Basic': { bg: 'bg-blue-100 dark:bg-blue-900', text: 'text-blue-900 dark:text-blue-100' },
      'Shield Plus': { bg: 'bg-purple-100 dark:bg-purple-900', text: 'text-purple-900 dark:text-purple-100' },
      'Shield Pro': { bg: 'bg-amber-100 dark:bg-amber-900', text: 'text-amber-900 dark:text-amber-100' },
    };
    return colors[tier] || colors['Shield Basic'];
  };

  // Reset pagination when activeTab changes
  useEffect(() => {
    setCurrentPage(1);
  }, [activeTab]);

  // Show loading screen while fetching initial data
  if (loading) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-sm">
        <div className="text-center px-6">
          <div className="mx-auto mb-6 h-16 w-16 rounded-full border-4 border-gray-300/60 dark:border-gray-700 border-t-green-500 animate-spin" />
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">Loading Payouts</h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">Fetching payout history, worker details & DCI trigger data from backend...</p>
          <div className="space-y-2 text-xs text-gray-500 dark:text-gray-500">
            <div className="flex items-center justify-center gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <span>Retrieving payout records</span>
            </div>
            <div className="flex items-center justify-center gap-2">
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" style={{animationDelay: '0.2s'}} />
              <span>Fetching worker details & plans</span>
            </div>
            <div className="flex items-center justify-center gap-2">
              <div className="w-2 h-2 bg-cyan-500 rounded-full animate-pulse" style={{animationDelay: '0.4s'}} />
              <span>Loading live statistics</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Payouts</h1>
        <p className="text-gray-600 dark:text-gray-400 mt-1">AI-triggered parametric payout pipeline</p>
      </div>

      {/* Stats Grid - Live Feed */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-blue-600 dark:bg-blue-700 text-white rounded-lg p-6 shadow-lg">
          <div className="flex items-start justify-between mb-3">
            <div>
              <p className="text-sm opacity-90 font-medium">Total Disbursed This Week</p>
              <p className="text-4xl font-bold mt-2 font-mono">{formatCurrency(liveStats.totalDisbursedeThisWeek)}</p>
            </div>
            <DollarSign className="w-8 h-8 opacity-40" />
          </div>
          <div className="flex items-center gap-2 text-xs opacity-75">
            <span className="w-2 h-2 rounded-full bg-blue-300 animate-pulse" />
            <span>Updating live</span>
          </div>
        </div>

        <div className="bg-amber-600 dark:bg-amber-700 text-white rounded-lg p-6 shadow-lg">
          <div className="flex items-start justify-between mb-3">
            <div>
              <p className="text-sm opacity-90 font-medium">Pending</p>
              <p className="text-4xl font-bold mt-2 font-mono">{formatCurrency(liveStats.pending)}</p>
            </div>
            <TrendingDown className="w-8 h-8 opacity-40" />
          </div>
          <div className="flex items-center gap-2 text-xs opacity-75">
            <span className="w-2 h-2 rounded-full bg-amber-300 animate-pulse" />
            <span>Updating live</span>
          </div>
        </div>

        <div className="bg-green-600 dark:bg-green-700 text-white rounded-lg p-6 shadow-lg">
          <div className="flex items-start justify-between mb-3">
            <div>
              <p className="text-sm opacity-90 font-medium">Success Rate</p>
              <p className="text-4xl font-bold mt-2 font-mono">{formatPercentage(liveStats.successRate)}</p>
            </div>
            <CheckCircle className="w-8 h-8 opacity-40" />
          </div>
          <div className="flex items-center gap-2 text-xs opacity-75">
            <span className="w-2 h-2 rounded-full bg-green-300 animate-pulse" />
            <span>Updating live</span>
          </div>
        </div>

        <div className="bg-purple-600 dark:bg-purple-700 text-white rounded-lg p-6 shadow-lg">
          <div className="flex items-start justify-between mb-3">
            <div>
              <p className="text-sm opacity-90 font-medium">Avg Processing</p>
              <p className="text-4xl font-bold mt-2 font-mono">{liveStats.avgProcessing.toFixed(1)} min</p>
            </div>
            <Zap className="w-8 h-8 opacity-40" />
          </div>
          <div className="flex items-center gap-2 text-xs opacity-75">
            <span className="w-2 h-2 rounded-full bg-purple-300 animate-pulse" />
            <span>Updating live</span>
          </div>
        </div>
      </div>

      {/* Real-time Processing Feed - Latest 5 */}
      <RealTimePayoutFeed
        limit={5}
        onWorkerClick={(id) => {
          setWorkerModalId(id);
          setWorkerModalOpen(true);
        }}
      />

      <WorkerModal
        workerId={workerModalId}
        isOpen={workerModalOpen}
        onClose={() => setWorkerModalOpen(false)}
      />

      {/* Controls */}
      <div className="bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 p-4 shadow-sm flex justify-between items-center">
        <div className="flex gap-2">
          {['all', 'paid', 'pending', 'processing', 'failed'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                activeTab === tab
                  ? 'bg-gigkavach-orange text-white'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
        <Button onClick={() => setIsSimulationOpen(true)} variant="primary" size="md">
          <Zap className="w-4 h-4" />
          Trigger Simulation
        </Button>
      </div>

      {/* Payouts Table with Pagination */}
      <div className="bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">Worker</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">Tier</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">Trigger</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">Amount</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">UPI Ref</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">Date & Time</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">Status</th>
              </tr>
            </thead>
            <tbody>
              {(() => {
                const filteredPayouts = payouts.filter((p) => activeTab === 'all' || p.status === activeTab);
                const totalPages = Math.ceil(filteredPayouts.length / itemsPerPage);
                const startIndex = (currentPage - 1) * itemsPerPage;
                const paginatedPayouts = filteredPayouts.slice(startIndex, startIndex + itemsPerPage);
                return paginatedPayouts.map((payout) => {
                  const statusColor = getStatusColor(payout.status);
                  const tierColor = getTierColor(payout.tier);
                  return (
                    <tr key={payout.id} className="border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-gigkavach-orange flex items-center justify-center text-white font-bold text-xs">
                            {payout.avatar}
                          </div>
                          <span className="text-sm font-medium text-gray-900 dark:text-white">{payout.worker}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`inline-block px-2 py-1 rounded text-xs font-semibold ${tierColor.bg} ${tierColor.text}`}>{payout.tier}</span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">{payout.trigger}</td>
                      <td className="px-6 py-4 font-mono font-bold text-gray-900 dark:text-white">{formatCurrency(payout.amount)}</td>
                      <td className="px-6 py-4 text-xs font-mono text-gray-500 dark:text-gray-400">{payout.upiRef}</td>
                      <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">{formatDate(payout.dateTime, 'datetime')}</td>
                      <td className="px-6 py-4">
                        <span className={`inline-block px-3 py-1 rounded-full text-xs font-semibold border ${statusColor.bg} ${statusColor.text} ${statusColor.border}`}>
                          {payout.status.charAt(0).toUpperCase() + payout.status.slice(1)}
                        </span>
                      </td>
                    </tr>
                  );
                });
              })()}
            </tbody>
          </table>
        </div>

        {/* Pagination Controls */}
        <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 flex items-center justify-between">
          <div className="text-sm text-gray-600 dark:text-gray-400">
            {(() => {
              const filteredPayouts = payouts.filter((p) => activeTab === 'all' || p.status === activeTab);
              const totalPages = Math.ceil(filteredPayouts.length / itemsPerPage);
              const startIndex = (currentPage - 1) * itemsPerPage;
              const endIndex = Math.min(startIndex + itemsPerPage, filteredPayouts.length);
              return `Showing ${filteredPayouts.length > 0 ? startIndex + 1 : 0} to ${endIndex} of ${filteredPayouts.length}`;
            })()}
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
              disabled={currentPage === 1}
              className="p-2 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              title="Previous page"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <div className="flex items-center gap-1">
              {(() => {
                const filteredPayouts = payouts.filter((p) => activeTab === 'all' || p.status === activeTab);
                const totalPages = Math.ceil(filteredPayouts.length / itemsPerPage);
                const pages = [];
                for (let i = 1; i <= totalPages; i++) {
                  pages.push(
                    <button
                      key={i}
                      onClick={() => setCurrentPage(i)}
                      className={`px-2 py-1 rounded text-sm font-medium transition-colors ${
                        i === currentPage
                          ? 'bg-gigkavach-orange text-white'
                          : 'border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                      }`}
                    >
                      {i}
                    </button>
                  );
                }
                return pages;
              })()}
            </div>
            <button
              onClick={() => setCurrentPage(currentPage + 1)}
              disabled={(() => {
                const filteredPayouts = payouts.filter((p) => activeTab === 'all' || p.status === activeTab);
                const totalPages = Math.ceil(filteredPayouts.length / itemsPerPage);
                return currentPage === totalPages;
              })()}
              className="p-2 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              title="Next page"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Simulation Modal */}
      {isSimulationOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white dark:bg-gigkavach-surface rounded-lg shadow-2xl w-full max-w-md p-6">
            <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">Trigger Payout Simulation</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Select Zone</label>
                <select
                  value={simulationZone}
                  onChange={(e) => setSimulationZone(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-gigkavach-orange"
                >
                  <option>Koramangala</option>
                  <option>HSR Layout</option>
                  <option>Whitefield</option>
                  <option>Electronic City</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Disruption Type</label>
                <div className="space-y-2">
                  {[
                    { value: 'rain', label: '🌧️ Heavy Rain' },
                    { value: 'aqi', label: '😷 Severe AQI' },
                    { value: 'heat', label: '🌡️ Extreme Heat' },
                    { value: 'bandh', label: '🚫 Bandh' },
                  ].map((opt) => (
                    <label key={opt.value} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="disruption"
                        value={opt.value}
                        checked={simulationDisruption === opt.value}
                        onChange={(e) => setSimulationDisruption(e.target.value)}
                        className="w-4 h-4 accent-gigkavach-orange"
                      />
                      <span className="text-sm text-gray-700 dark:text-gray-300">{opt.label}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">DCI Override: {simulationDCI}</label>
                <input
                  type="range"
                  min="65"
                  max="100"
                  value={simulationDCI}
                  onChange={(e) => setSimulationDCI(parseInt(e.target.value))}
                  className="w-full accent-gigkavach-orange"
                />
              </div>
            </div>

            <div className="flex gap-3 justify-end mt-6 p-4 bg-gray-50 dark:bg-gray-800 -mx-6 -mb-6 mt-6">
              <Button onClick={() => setIsSimulationOpen(false)} variant="secondary" size="md">
                Cancel
              </Button>
              <Button onClick={handleSimulation} variant="primary" size="md">
                Fire Simulation
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Toast */}
      {toastMessage && (
        <div className="fixed bottom-4 right-4 bg-emerald-500 text-white px-4 py-3 rounded-lg shadow-lg animate-pulse">
          {toastMessage}
        </div>
      )}
    </div>
  );
};
