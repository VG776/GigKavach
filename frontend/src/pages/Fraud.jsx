import { useState, useMemo, useEffect } from 'react';
import { X, AlertTriangle, Shield, TrendingDown, MapPin, Eye, MessageSquare, Ban } from 'lucide-react';
import { formatCurrency, getInitials } from '../utils/formatters';
import { fraudAPI } from '../api/fraud';

const signalLabels = ['GPS', 'IP', 'Velocity', 'Entropy', 'Cluster', 'Loyalty'];

const mockFraudRows = [
  {
    id: 1,
    workerId: 'W001',
    worker: 'Amit Patel',
    gigScore: 82,
    trigger: '🌧️ Heavy Rainfall · DCI 78',
    reason: 'GPS Spoofing · Signal 1+4 triggered',
    signals: [false, true, false, true, false, false],
    fraudScore: 2,
    riskLevel: 'medium',
    path: 'B',
    pathLabel: '⚠ Soft Flag · 50% held',
    rowTone: 'normal',
  },
  {
    id: 2,
    workerId: 'W002',
    worker: 'Sneha Reddy',
    gigScore: 91,
    trigger: '🌡️ Heat Wave · DCI 82',
    reason: 'Claim Timing Cluster · 6 workers · 45s window',
    signals: [true, false, true, false, true, false],
    fraudScore: 5,
    riskLevel: 'high',
    path: 'C',
    pathLabel: '✗ Hard Block',
    rowTone: 'hard-block',
  },
  {
    id: 3,
    workerId: 'W003',
    worker: 'Rajesh Kumar',
    gigScore: 75,
    trigger: '💨 High Wind · DCI 65',
    reason: 'IP Mismatch · Different networks day-to-day',
    signals: [false, true, false, false, false, false],
    fraudScore: 1,
    riskLevel: 'low',
    path: 'A',
    pathLabel: '✓ Clean',
    rowTone: 'normal',
  },
  {
    id: 4,
    workerId: 'W004',
    worker: 'Priya Singh',
    gigScore: 88,
    trigger: '🌊 Flooding · DCI 90',
    reason: 'Velocity Spike · 3 payouts in 5 mins',
    signals: [false, false, true, true, false, false],
    fraudScore: 3,
    riskLevel: 'medium',
    path: 'B',
    pathLabel: '⚠ Soft Flag · Under Review',
    rowTone: 'normal',
  },
  {
    id: 5,
    workerId: 'W005',
    worker: 'Vikram Desai',
    gigScore: 85,
    trigger: '🌧️ Heavy Rainfall · DCI 78',
    reason: 'Zone Loyalty Mismatch · Never worked Koramangala',
    signals: [false, false, false, true, false, true],
    fraudScore: 2,
    riskLevel: 'low',
    path: 'A',
    pathLabel: '✓ Clean',
    rowTone: 'normal',
  },
];

const transformAPIDataToTableRow = (flag) => {
  const signalOrder = ['gps', 'ip_mismatch', 'velocity', 'gps_entropy', 'timing_cluster', 'zone_loyalty'];
  
  // Get triggered signals
  const triggeredSignals = flag.signals || {};
  const signals = signalOrder.map(sig => triggeredSignals[sig] === true);
  
  // Count triggered signals
  const signalCount = signals.filter(s => s).length;
  
  // Get signal details for reason
  const signalDetails = Object.entries(triggeredSignals)
    .filter(([_, value]) => value === true)
    .map(([key, _]) => key.replace(/_/g, ' ').toUpperCase())
    .slice(0, 2);
  
  return {
    id: flag.id,
    workerId: flag.worker_id || flag.worker?.id || 'Unknown',
    worker: flag.worker_name || flag.worker?.name || 'Unknown Worker',
    gigScore: flag.gig_score || flag.worker?.gig_score || 75,
    trigger: flag.dci_score ? `🌧️ DCI ${flag.dci_score}` : flag.zone || 'Unknown Zone',
    reason: signalDetails.length > 0 ? signalDetails.join(' + ') : 'Flagged for review',
    signals: signals,
    fraudScore: signalCount,
    riskLevel: flag.risk_level || (signalCount >= 4 ? 'high' : signalCount >= 2 ? 'medium' : 'low'),
    path: flag.path || 'A',
    pathLabel: flag.path === 'C' ? '✗ Hard Block' : flag.path === 'B' ? '⚠ Soft Flag · Under Review' : '✓ Clean',
    rowTone: flag.path === 'C' ? 'hard-block' : 'normal',
    zone: flag.zone || 'Unknown',
  };
};

const heatmapZones = [
  { zone: 'Koramangala', workers: 18, activity: 'high' },
  { zone: 'Whitefield', workers: 14, activity: 'high' },
  { zone: 'HSR Layout', workers: 12, activity: 'high' },
  { zone: 'Marathahalli', workers: 9, activity: 'medium' },
  { zone: 'Indiranagar', workers: 8, activity: 'medium' },
  { zone: 'Electronic City', workers: 7, activity: 'medium' },
  { zone: 'Bangalore North', workers: 6, activity: 'low' },
  { zone: 'Bangalore South', workers: 5, activity: 'low' },
];

// Calculate zone density from fraud data
const calculateZoneDensity = (fraudRows) => {
  const zoneCounts = {};
  
  // Count workers by zone
  fraudRows.forEach(row => {
    if (row.zone && row.zone !== 'Unknown') {
      zoneCounts[row.zone] = (zoneCounts[row.zone] || 0) + 1;
    }
  });
  
  // Sort zones by worker count and assign activity levels
  const zones = Object.entries(zoneCounts)
    .sort((a, b) => b[1] - a[1])
    .map(([zone, count]) => {
      let activity = 'low';
      if (count >= 10) activity = 'high';
      else if (count >= 5) activity = 'medium';
      return { zone, workers: count, activity };
    });
  
  // If no real zones, fall back to hardcoded heatmap
  return zones.length > 0 ? zones : heatmapZones;
};

export const Fraud = () => {
  const [bannerDismissed, setBannerDismissed] = useState(false);
  const [filterPath, setFilterPath] = useState('all');
  const [filterRisk, setFilterRisk] = useState('all');
  const [fraudRows, setFraudRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 5;
  const [summaryStats, setSummaryStats] = useState({
    high_risk_active: 0,
    resolved_this_week: 0,
  });

  // Fetch fraud alerts and summary stats - WITH LIVE POLLING
  useEffect(() => {
    const fetchFraudData = async () => {
      try {
        setLoading(true);
        
        // Fetch fraud flags from API
        const response = await fraudAPI.getFraudFlags(100, false);
        
        // Handle API response - may be wrapped in .data or direct
        const flagsData = response?.flags || response?.data?.flags || response || [];
        
        if (flagsData && Array.isArray(flagsData) && flagsData.length > 0) {
          console.log('[Fraud] Fetched', flagsData.length, 'fraud flags from API');
          const transformedRows = flagsData.map(transformAPIDataToTableRow);
          setFraudRows(transformedRows);
        } else {
          console.log('[Fraud] No flags from API, using mock data');
          setFraudRows(mockFraudRows);
        }
        
        // Fetch summary stats
        const summaryResponse = await fraudAPI.getFraudSummary();
        const summaryData = summaryResponse?.data || summaryResponse || {};
        
        if (summaryData?.high_risk_active !== undefined) {
          setSummaryStats({
            high_risk_active: summaryData.high_risk_active || 0,
            resolved_this_week: summaryData.resolved_this_week || 0,
          });
        }
      } catch (err) {
        console.error('[Fraud] Error fetching fraud data:', err);
        // Fallback to mock data
        setFraudRows(mockFraudRows);
        setSummaryStats({
          high_risk_active: mockFraudRows.filter((r) => r.riskLevel === 'high').length,
          resolved_this_week: 8,
        });
      } finally {
        setLoading(false);
      }
    };

    // Initial fetch
    fetchFraudData();
    
    // Poll every 5 seconds for live updates
    const interval = setInterval(fetchFraudData, 20000);
    
    return () => clearInterval(interval);
  }, []);

  const stats = [
    {
      label: 'High Risk Active',
      value: summaryStats.high_risk_active,
      color: 'bg-red-600 dark:bg-red-700',
      icon: AlertTriangle,
    },
    {
      label: 'Resolved This Week',
      value: summaryStats.resolved_this_week,
      color: 'bg-green-600 dark:bg-green-700',
      icon: TrendingDown,
    },
    {
      label: 'DC Saved (Fraud Blocked)',
      value: '₹34,200',
      color: 'bg-gigkavach-orange dark:bg-orange-600',
      icon: Shield,
    },
  ];

  const filteredRows = useMemo(() => {
    let result = fraudRows;

    if (filterPath !== 'all') {
      result = result.filter((r) => r.path === filterPath);
    }

    if (filterRisk !== 'all') {
      result = result.filter((r) => r.riskLevel === filterRisk);
    }

    return result;
  }, [filterPath, filterRisk, fraudRows]);

  // Pagination logic
  const totalPages = Math.ceil(filteredRows.length / itemsPerPage);
  const paginatedRows = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    return filteredRows.slice(startIndex, startIndex + itemsPerPage);
  }, [filteredRows, currentPage]);

  // Reset to page 1 when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [filterPath, filterRisk]);

  // Calculate zone density from actual fraud data
  const zoneData = useMemo(() => {
    return calculateZoneDensity(fraudRows);
  }, [fraudRows]);

  const getRiskBadgeColor = (level) => {
    const colors = {
      high: 'bg-red-100 dark:bg-red-900 text-red-900 dark:text-red-100',
      medium: 'bg-amber-100 dark:bg-amber-900 text-amber-900 dark:text-amber-100',
      low: 'bg-green-100 dark:bg-green-900 text-green-900 dark:text-green-100',
    };
    return colors[level];
  };

  const getPathBadgeColor = (path) => {
    const colors = {
      A: 'bg-green-100 dark:bg-green-900 text-green-900 dark:text-green-100',
      B: 'bg-amber-100 dark:bg-amber-900 text-amber-900 dark:text-amber-100',
      C: 'bg-red-100 dark:bg-red-900 text-red-900 dark:text-red-100',
    };
    return colors[path];
  };

  const getHeatmapColor = (activity) => {
    const colors = {
      high: 'bg-rose-600 dark:bg-rose-700',
      medium: 'bg-amber-500 dark:bg-amber-600',
      low: 'bg-emerald-600 dark:bg-emerald-700',
    };
    return colors[activity];
  };

  // Show loading screen while fetching initial data
  if (loading) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-sm">
        <div className="text-center px-6">
          <div className="mx-auto mb-6 h-16 w-16 rounded-full border-4 border-gray-300/60 dark:border-gray-700 border-t-red-500 animate-spin" />
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">Loading Fraud Alerts</h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">Fetching real-time fraud flags and signal analysis from backend...</p>
          <div className="space-y-2 text-xs text-gray-500 dark:text-gray-500">
            <div className="flex items-center justify-center gap-2">
              <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
              <span>Scanning fraud detection signals</span>
            </div>
            <div className="flex items-center justify-center gap-2">
              <div className="w-2 h-2 bg-orange-500 rounded-full animate-pulse" style={{animationDelay: '0.2s'}} />
              <span>Analyzing worker gig scores</span>
            </div>
            <div className="flex items-center justify-center gap-2">
              <div className="w-2 h-2 bg-yellow-500 rounded-full animate-pulse" style={{animationDelay: '0.4s'}} />
              <span>Mapping zones and risk levels</span>
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
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Fraud Operations Center (PHASE 3 DELIVERABLE) </h1>
        <p className="text-gray-600 dark:text-gray-400 mt-1">Real-time signal monitoring, risk assessment & case management</p>
      </div>

      {/* Syndicate Detection Banner */}
      {!bannerDismissed && (
        <div className="bg-red-50 dark:bg-red-950 border-l-4 border-l-red-600 rounded-lg p-4 flex items-start justify-between gap-4">
          <div className="flex gap-4 flex-1">
            <AlertTriangle className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-red-900 dark:text-red-100">⚠️ Potential Fraud Ring Detected</p>
              <p className="text-sm text-red-800 dark:text-red-200 mt-2">
                6 workers claimed within 45s window in Koramangala. Claim clustering (Signal 5) triggered. All held at Path B pending review.
              </p>
              <div className="flex gap-2 mt-3">
                <button className="px-3 py-1 bg-red-600 text-white rounded text-sm font-medium hover:bg-red-700 transition-colors">
                  View Cluster
                </button>
                <button className="px-3 py-1 bg-red-100 dark:bg-red-900 text-red-900 dark:text-red-100 rounded text-sm font-medium hover:bg-red-200 dark:hover:bg-red-800 transition-colors">
                  View Timeline
                </button>
              </div>
            </div>
          </div>
          <button
            onClick={() => setBannerDismissed(true)}
            className="p-1 hover:bg-red-200 dark:hover:bg-red-900 rounded transition-colors flex-shrink-0"
          >
            <X className="w-5 h-5 text-red-600" />
          </button>
        </div>
      )}

      {/* KPI Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {stats.map((stat, idx) => {
          const Icon = stat.icon;
          return (
            <div key={idx} className={`${stat.color} text-white rounded-lg p-6 shadow-lg`}>
              <div className="flex items-start justify-between mb-3">
                <div>
                  <p className="text-sm opacity-90 font-medium">{stat.label}</p>
                  <p className="text-4xl font-bold mt-2">{stat.value}</p>
                </div>
                <Icon className="w-8 h-8 opacity-40" />
              </div>
            </div>
          );
        })}
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Main Table - 3/4 width */}
        <div className="lg:col-span-3">
          {/* Filters */}
          <div className="bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 p-4 shadow-sm mb-6">
            <div className="flex flex-col md:flex-row gap-4">
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Filter by Path</label>
                <select
                  value={filterPath}
                  onChange={(e) => setFilterPath(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-gigkavach-orange"
                >
                  <option value="all">All Cases</option>
                  <option value="A">Path A - Clean</option>
                  <option value="B">Path B - Soft Flag</option>
                  <option value="C">Path C - Hard Block</option>
                </select>
              </div>
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Filter by Risk</label>
                <select
                  value={filterRisk}
                  onChange={(e) => setFilterRisk(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-gigkavach-orange"
                >
                  <option value="all">All Risk Levels</option>
                  <option value="low">Low Risk</option>
                  <option value="medium">Medium Risk</option>
                  <option value="high">High Risk</option>
                </select>
              </div>
            </div>
          </div>

          {/* Fraud Signal Monitor Table */}
          <div className="bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">Worker</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">Location</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">Fraud Reason</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">Signals</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">Score</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">Risk</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">Path</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedRows.map((row) => (
                    <tr
                      key={row.id}
                      className={`border-b dark:border-gray-700 transition-colors ${
                        row.rowTone === 'hard-block'
                          ? 'bg-red-50/60 dark:bg-red-950/20 hover:bg-red-100/60 dark:hover:bg-red-950/30'
                          : 'hover:bg-gray-50 dark:hover:bg-gray-800'
                      }`}
                    >
                      {/* Worker */}
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-gigkavach-orange to-orange-600 flex items-center justify-center text-white font-bold text-xs flex-shrink-0">
                            {getInitials(row.worker.split(' ')[0], row.worker.split(' ')[1])}
                          </div>
                          <div>
                            <p className="font-medium text-gray-900 dark:text-white text-sm">{row.worker}</p>
                            <span className="text-xs bg-orange-100 dark:bg-orange-900 text-orange-900 dark:text-orange-100 px-2 py-0.5 rounded leading-relaxed">
                              Score {row.gigScore}
                            </span>
                          </div>
                        </div>
                      </td>

                      {/* Location */}
                      <td className="px-4 py-4 text-xs text-gray-600 dark:text-gray-400 whitespace-nowrap font-medium">{row.zone || 'Unknown'}</td>

                      {/* Fraud Reason */}
                      <td className="px-4 py-4 text-xs text-gray-600 dark:text-gray-400 max-w-xs">{row.reason}</td>

                      {/* Signals */}
                      <td className="px-4 py-4">
                        <div className="flex gap-1 flex-wrap">
                          {row.signals.map((signal, idx) => (
                            <div
                              key={idx}
                              title={signalLabels[idx]}
                              className={`w-5 h-5 rounded-sm border flex items-center justify-center text-xs font-bold flex-shrink-0 ${
                                signal
                                  ? 'bg-red-100 dark:bg-red-900 border-red-400 dark:border-red-600 text-red-700 dark:text-red-100'
                                  : 'bg-green-100 dark:bg-green-900 border-green-400 dark:border-green-600 text-green-700 dark:text-green-100'
                              }`}
                            >
                              {idx + 1}
                            </div>
                          ))}
                        </div>
                      </td>

                      {/* Fraud Score */}
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-sm text-gray-900 dark:text-white whitespace-nowrap">{row.fraudScore}/6</span>
                          <div className="w-10 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden flex-shrink-0">
                            <div
                              className={`h-full ${
                                row.fraudScore >= 5
                                  ? 'bg-red-600 dark:bg-red-500'
                                  : row.fraudScore >= 3
                                    ? 'bg-amber-600 dark:bg-amber-500'
                                    : 'bg-green-600 dark:bg-green-500'
                              }`}
                              style={{ width: `${(row.fraudScore / 6) * 100}%` }}
                            />
                          </div>
                        </div>
                      </td>

                      {/* Risk Level */}
                      <td className="px-4 py-4">
                        <span className={`inline-block px-2 py-1 rounded text-xs font-semibold ${getRiskBadgeColor(row.riskLevel)}`}>
                          {row.riskLevel === 'high' ? '🔴 High' : row.riskLevel === 'medium' ? '🟡 Medium' : '🟢 Low'}
                        </span>
                      </td>

                      {/* Path */}
                      <td className="px-4 py-4">
                        <span className={`inline-block px-2 py-1 rounded text-xs font-semibold ${getPathBadgeColor(row.path)}`}>
                          {row.pathLabel}
                        </span>
                      </td>

                      {/* Actions */}
                      <td className="px-4 py-4">
                        <div className="flex gap-1">
                          <button className="p-1.5 hover:bg-blue-100 dark:hover:bg-blue-900 rounded transition-colors text-blue-600 dark:text-blue-400" title="Review case">
                            <Eye className="w-4 h-4" />
                          </button>
                          <button className="p-1.5 hover:bg-amber-100 dark:hover:bg-amber-900 rounded transition-colors text-amber-600 dark:text-amber-400" title="Appeal">
                            <MessageSquare className="w-4 h-4" />
                          </button>
                          <button className="p-1.5 hover:bg-red-100 dark:hover:bg-red-900 rounded transition-colors text-red-600 dark:text-red-400" title="Blacklist">
                            <Ban className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Empty State */}
            {filteredRows.length === 0 && (
              <div className="p-12 text-center">
                <AlertTriangle className="w-12 h-12 text-gray-400 dark:text-gray-600 mx-auto mb-3 opacity-50" />
                <p className="text-gray-600 dark:text-gray-400 font-medium">No fraud cases match filters</p>
              </div>
            )}

            {/* Pagination Controls */}
            {filteredRows.length > 0 && (
              <div className="px-4 py-4 border-t dark:border-gray-700 bg-gray-50 dark:bg-gray-800 flex items-center justify-between">
                <div className="text-sm text-gray-600 dark:text-gray-400">
                  Showing {paginatedRows.length > 0 ? (currentPage - 1) * itemsPerPage + 1 : 0} to {Math.min(currentPage * itemsPerPage, filteredRows.length)} of {filteredRows.length} cases
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                    disabled={currentPage === 1}
                    className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    ← Prev
                  </button>
                  <div className="flex items-center gap-1">
                    {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                      <button
                        key={page}
                        onClick={() => setCurrentPage(page)}
                        className={`px-2 py-1 rounded text-sm font-medium transition-colors ${
                          page === currentPage
                            ? 'bg-gigkavach-orange text-white'
                            : 'border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                        }`}
                      >
                        {page}
                      </button>
                    ))}
                  </div>
                  <button
                    onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                    disabled={currentPage === totalPages}
                    className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    Next →
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Sidebar - 1/4 width */}
        <div className="space-y-6">
          {/* Zone Fraud Density Heatmap */}
          <div className="bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 p-4 shadow-sm">
            <h3 className="font-semibold text-gray-900 dark:text-white mb-4 text-sm flex items-center gap-2">
              <MapPin className="w-4 h-4 text-gigkavach-orange" />
              Zone Fraud Density
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">Last 7 Days</p>
            <div className="grid grid-cols-2 gap-2">
              {zoneData.map((z) => (
                <div
                  key={z.zone}
                  className={`${getHeatmapColor(z.activity)} text-white p-3 rounded-lg text-xs font-semibold text-center cursor-pointer hover:opacity-90 transition-opacity`}
                >
                  <p className="truncate text-xs leading-tight">{z.zone}</p>
                  <p className="text-xs opacity-90 mt-1">{z.workers} workers</p>
                </div>
              ))}
            </div>
          </div>

          {/* Operations Guide */}
          <div className="bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 p-4 shadow-sm">
            <h3 className="font-semibold text-gray-900 dark:text-white mb-4 text-sm">Path Guide</h3>
            <div className="space-y-3 text-xs">
              <div className="pb-3 border-b dark:border-gray-700">
                <p className="font-medium text-green-700 dark:text-green-400 mb-1">✓ Path A: Clean</p>
                <p className="text-gray-600 dark:text-gray-400">Consensus passed · Payout released immediately</p>
              </div>
              <div className="pb-3 border-b dark:border-gray-700">
                <p className="font-medium text-amber-700 dark:text-amber-400 mb-1">⚠ Path B: Soft Flag</p>
                <p className="text-gray-600 dark:text-gray-400">50% held in escrow · Awaiting manual review</p>
              </div>
              <div>
                <p className="font-medium text-red-700 dark:text-red-400 mb-1">✗ Path C: Hard Block</p>
                <p className="text-gray-600 dark:text-gray-400">Payout withheld · Escalate to blacklist</p>
              </div>
            </div>
          </div>

          {/* Signal Legend */}
          <div className="bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 p-4 shadow-sm">
            <h3 className="font-semibold text-gray-900 dark:text-white mb-3 text-sm">Fraud Signals</h3>
            <div className="grid grid-cols-3 gap-2">
              {signalLabels.map((label, idx) => (
                <div key={idx} className="text-center">
                  <div className="w-6 h-6 rounded-sm bg-red-100 dark:bg-red-900 border border-red-400 dark:border-red-600 flex items-center justify-center text-xs font-bold text-red-700 dark:text-red-100 mx-auto mb-1">
                    {idx + 1}
                  </div>
                  <p className="text-xs text-gray-600 dark:text-gray-400">{label}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
