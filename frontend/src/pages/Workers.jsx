import { useState, useMemo, useEffect } from 'react';
import { Search, Eye, Shield, SlidersHorizontal, TrendingDown, Building2, Clock, Zap, Share2, Copy, Check } from 'lucide-react';
import { formatPhoneNumber, getInitials, formatCurrency } from '../utils/formatters';
import { workerAPI } from '../api/workers';
import { premiumAPI } from '../api/premium';
import { WorkerModal } from '../components/workers/WorkerModal';
import { generateShareToken, copyToClipboard, shareOnWhatsApp } from '../utils/shareTokenUtils';
/*
const [selectedWorker, setSelectedWorker] = useState(null);
const [isPopupOpen, setIsPopupOpen] = useState(false);
const [isModalOpen, setIsModalOpen] = useState(false);
const [selectedWorkerId, setSelectedWorkerId] = useState(null);
*/

/*const handleWorkerClick = (worker) => {
  setSelectedWorker(worker);
  setIsPopupOpen(true);
};*/
// Worker Profile Drawer Component



const PLAN_OPTIONS = [
  {
    value: 'all',
    label: 'All',
    sub: 'plans',
    idle: 'text-gray-600 dark:text-gray-400 hover:bg-white/80 dark:hover:bg-gray-700/60 hover:text-gray-900 dark:hover:text-white',
    active: 'bg-gradient-to-b from-gigkavach-orange to-orange-600 text-white shadow-md shadow-orange-500/25 ring-1 ring-orange-400/40',
    dot: 'bg-gray-400 dark:bg-gray-500',
  },
  {
    value: 'Shield Basic',
    label: 'Basic',
    sub: 'Shield',
    idle: 'text-gray-600 dark:text-gray-400 hover:bg-white/80 dark:hover:bg-gray-700/60 hover:text-blue-700 dark:hover:text-blue-300',
    active: 'bg-gradient-to-b from-blue-500 to-blue-600 text-white shadow-md shadow-blue-500/25 ring-1 ring-blue-400/40',
    dot: 'bg-blue-500',
  },
  {
    value: 'Shield Plus',
    label: 'Plus',
    sub: 'Shield',
    idle: 'text-gray-600 dark:text-gray-400 hover:bg-white/80 dark:hover:bg-gray-700/60 hover:text-purple-700 dark:hover:text-purple-300',
    active: 'bg-gradient-to-b from-purple-500 to-purple-600 text-white shadow-md shadow-purple-500/25 ring-1 ring-purple-400/40',
    dot: 'bg-purple-500',
  },
  {
    value: 'Shield Pro',
    label: 'Pro',
    sub: 'Shield',
    idle: 'text-gray-600 dark:text-gray-400 hover:bg-white/80 dark:hover:bg-gray-700/60 hover:text-amber-800 dark:hover:text-amber-300',
    active: 'bg-gradient-to-b from-amber-500 to-amber-600 text-white shadow-md shadow-amber-500/25 ring-1 ring-amber-400/40',
    dot: 'bg-amber-500',
  },
];

function normalizeWorkerPlan(plan) {
  if (!plan) return '';
  const p = String(plan).toLowerCase();
  if (p.includes('basic')) return 'Shield Basic';
  if (p.includes('plus')) return 'Shield Plus';
  if (p.includes('pro')) return 'Shield Pro';
  return String(plan);
}

/**
 * Extracts just the plan tier ('basic', 'plus', 'pro') from full plan names
 * Used for API calls that expect lowercase tier values
 */
function extractPlanTier(plan) {
  if (!plan) return 'basic';
  const p = String(plan).toLowerCase();
  if (p.includes('basic')) return 'basic';
  if (p.includes('plus')) return 'plus';
  if (p.includes('pro')) return 'pro';
  return 'basic'; // fallback to basic
}

export const Workers = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [filterPlan, setFilterPlan] = useState('all');
  const [filterPlatform, setFilterPlatform] = useState('all');
  const [filterShift, setFilterShift] = useState('all');
  const [filterGigScore, setFilterGigScore] = useState('all');

  // Modal state
  const [selectedWorkerId, setSelectedWorkerId] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Share token state
  const [shareDropdownId, setShareDropdownId] = useState(null);
  const [shareLinks, setShareLinks] = useState({});
  const [copiedId, setCopiedId] = useState(null);
  const [sharingInProgress, setSharingInProgress] = useState({});

  const handleShareProfile = async (worker) => {
    if (sharingInProgress[worker.id]) return;

    setSharingInProgress((prev) => ({ ...prev, [worker.id]: true }));

    try {
      if (!worker.id) {
        throw new Error('Worker ID is missing');
      }

      console.log('[WORKERS] Generating share link for:', worker.id);

      // Generate share token via backend API
      const shareUrl = await generateShareToken(worker.id);
      
      setShareLinks((prev) => ({ ...prev, [worker.id]: shareUrl }));

      // Copy to clipboard
      const copied = await copyToClipboard(shareUrl);
      if (copied) {
        setCopiedId(worker.id);
        setTimeout(() => setCopiedId(null), 2000);
      }
    } catch (error) {
      console.error('[WORKERS] Error sharing profile:', error);
      const errorMsg = error.message || 'Failed to generate share link. Please try again.';
      alert(`Error: ${errorMsg}`);
    } finally {
      setSharingInProgress((prev) => ({ ...prev, [worker.id]: false }));
    }
  };


  const handleRowClick = (worker) => {
    setSelectedWorkerId(worker.id);
    setIsModalOpen(true);
  };



  const [workers, setWorkers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [premiumData, setPremiumData] = useState({});
  const [premiumLoading, setPremiumLoading] = useState(true); // Track premium data fetch status

  // ✅ pagination state (MUST be at top)
  const [currentPage, setCurrentPage] = useState(1);
  const ITEMS_PER_PAGE = 5;

  // ✅ FETCH ONCE
  const fetchWorkers = async () => {
    setLoading(true);
    try {
      console.log('[WORKERS] Fetching from API...');
      const response = await workerAPI.getAll();
      
      console.log('[WORKERS] API Response:', response);
      
      // Handle both direct array response and wrapped response
      const workersData = Array.isArray(response) ? response : (response.data || []);
      
      if (!Array.isArray(workersData)) {
        console.error('[WORKERS] Invalid response format:', response);
        setWorkers([]);
        return;
      }

      const formatted = workersData.map((w) => ({
        id: w.id,
        name: w.name || 'Unknown',
        phone: w.phone || '',
        upi: w.upi_id || 'N/A',
        zone: w.zone || 'N/A',
        status: w.status || 'inactive',
        plan: w.plan || 'Shield Basic',
        gig_score: w.gig_score || 0,
        portfolio_score: w.portfolio_score || 0,
        platform: w.gig_platform || w.platform || 'Zomato',
        shift: w.shift || 'Flexible',
        premium:
          w.plan === 'basic' || !w.plan
            ? 69
            : w.plan === 'plus'
            ? 89
            : w.plan === 'pro'
            ? 99
            : 69,
        coverage: w.coverage || 0,
        coverageWindow: 'Flexible',
        last7DaysEarnings: [500, 700, 600, 800, 650, 720, 900],
        dciHistory: [],
        fraudStatus: 'clean',
        payoutHistory: [],
      }));

      console.log('[WORKERS] Formatted workers:', formatted);
      setWorkers(formatted);
    } catch (err) {
      console.error('[WORKERS] Error fetching workers:', err);
      console.error('[WORKERS] Error details:', {
        message: err.message,
        status: err.response?.status,
        statusText: err.response?.statusText,
        data: err.response?.data,
        url: err.config?.url
      });
      setWorkers([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWorkers();
  }, []);

  // ✅ FILTERING
  const filteredWorkers = useMemo(() => {
    let result = workers;

    if (searchQuery) {
      result = result.filter(
        (w) =>
          w.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          w.phone.includes(searchQuery) ||
          w.zone.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    if (filterStatus !== 'all') {
      result = result.filter((w) => w.status === filterStatus);
    }

    if (filterPlan !== 'all') {
      result = result.filter((w) => normalizeWorkerPlan(w.plan) === filterPlan);
    }

    if (filterPlatform !== 'all') {
      result = result.filter((w) => (w.platform || '').toLowerCase().trim() === filterPlatform.toLowerCase().trim());
    }

    if (filterShift !== 'all') {
      result = result.filter((w) => (w.shift || '').toLowerCase().trim() === filterShift.toLowerCase().trim());
    }

    if (filterGigScore !== 'all') {
      if (filterGigScore === '80+') {
        result = result.filter((w) => w.gig_score >= 80);
      } else if (filterGigScore === '70+') {
        result = result.filter((w) => w.gig_score >= 70);
      } else if (filterGigScore === 'below70') {
        result = result.filter((w) => w.gig_score < 70);
      }
    }

    return result;
  }, [workers, searchQuery, filterStatus, filterPlan, filterPlatform, filterShift, filterGigScore]);

  // ✅ RESET PAGE WHEN FILTER CHANGES
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, filterStatus, filterPlan, filterPlatform, filterShift, filterGigScore]);

  // ✅ PAGINATION
  const totalPages = Math.ceil(filteredWorkers.length / ITEMS_PER_PAGE);

  const paginatedWorkers = filteredWorkers.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  );

  const start = (currentPage - 1) * ITEMS_PER_PAGE + 1;
  const end = Math.min(currentPage * ITEMS_PER_PAGE, filteredWorkers.length);

  // Fetch premium data for ALL workers (only once when workers list changes)
  // This shows "Calculating..." on first load, then caches and displays on page switches
  useEffect(() => {
    if (workers.length === 0) {
      setPremiumLoading(false);
      return;
    }

    const fetchPremiumDataForWorkers = async () => {
      setPremiumLoading(true);
      const quotes = {};
      
      for (const worker of workers) {
        if (!worker.id || worker.id.trim() === '') {
          continue;
        }
        try {
          const planTier = extractPlanTier(worker.plan);
          const quote = await premiumAPI.getQuote(worker.id, planTier);
          quotes[worker.id] = quote;
        } catch (err) {
          console.warn(`[WORKERS] Failed to fetch premium for worker ${worker.id}:`, err);
          quotes[worker.id] = null;
        }
      }
      
      setPremiumData(quotes);
      setPremiumLoading(false);
    };

    fetchPremiumDataForWorkers();
  }, [workers]); // Only depends on workers, not paginatedWorkers

  // ✅ LOADING (AFTER ALL HOOKS)
  if (loading) {
    return <div className="p-6">Loading workers...</div>;
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Workers</h1>
        <p className="text-gray-600 dark:text-gray-400 mt-1">Manage and monitor your delivery workforce</p>
      </div>

      {/* Main Layout: Grid with Left Content + Right Sidebar */}
      <div className="grid grid-cols-1 lg:grid-cols-[1.5fr_240px] gap-6">
        {/* Left Column: Search & Table */}
        <div className="space-y-4 min-w-0">
          {/* Search Bar */}
          <div className="relative overflow-hidden rounded-xl border border-gray-200/90 dark:border-gray-700/90 bg-white dark:bg-gigkavach-surface shadow-[0_1px_3px_rgba(0,0,0,0.06),0_8px_24px_-6px_rgba(15,27,45,0.08)] dark:shadow-[0_1px_3px_rgba(0,0,0,0.2),0_12px_40px_-12px_rgba(0,0,0,0.45)]">
            <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-gigkavach-orange/35 to-transparent" />
            <div className="p-4 space-y-2">
              <label className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                Search
              </label>
              <div className="relative">
                <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 dark:text-gray-500" />
                <input
                  type="text"
                  placeholder="Name, phone, or zone…"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-600 bg-gray-50/80 dark:bg-gray-800/50 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-500 text-sm focus:outline-none focus:ring-2 focus:ring-gigkavach-orange/80 focus:border-transparent transition-shadow"
                />
              </div>
            </div>
          </div>

          {/* Workers Table */}
          <div className="bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm">
            <table className="w-full table-fixed">
              <thead>
                <tr className="border-b dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                    Worker
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                    Zone
                  </th>
                  <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                    Gig
                  </th>
                  <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                    Port.
                  </th>
                  <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                    Platform
                  </th>
                  <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                    Shift
                  </th>
                  <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                    Plan
                  </th>
                  <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                    Premium
                  </th>
                  <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                    Share
                  </th>
                </tr>
              </thead>
              <tbody>
                {paginatedWorkers.map((worker) => (
                  <tr
                    key={worker.id}
                    className="border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                  >
                    <td className="px-4 py-3 min-w-0">
                      <div className="flex items-center gap-2">
                        <div className="w-9 h-9 rounded-full bg-gigkavach-orange flex items-center justify-center text-white font-bold text-sm flex-shrink-0">
                            {getInitials(worker.name?.split(' ')[0] || '',worker.name?.split(' ')[1] || '')}
                        </div>
                        <div className="min-w-0">
                          <p
        onClick={() => handleRowClick(worker)}
        className="text-sm font-medium text-orange-500 cursor-pointer hover:underline"
      >
        {worker.name}
      </p>
                          <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{formatPhoneNumber(worker.phone)}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-300 truncate">{worker.zone}</td>
                    <td className="px-4 py-3 text-center">
                      <span className="inline-flex px-2 py-1 rounded text-sm font-semibold bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 whitespace-nowrap">
                        {worker.gig_score}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className="inline-flex px-2 py-1 rounded text-sm font-semibold bg-purple-50 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 whitespace-nowrap">
                        {worker.portfolio_score}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`inline-flex px-2 py-1 rounded text-sm font-medium whitespace-nowrap ${
                        worker.platform === 'Zomato'
                          ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300'
                          : 'bg-gigkavach-orange/20 dark:bg-gigkavach-orange/30 text-gigkavach-orange dark:text-orange-300'
                      }`}>
                        {worker.platform}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className="inline-flex px-2 py-1 rounded text-sm font-medium bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 uppercase whitespace-nowrap">
                        {worker.shift}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={`inline-flex px-2 py-1 rounded text-sm font-semibold whitespace-nowrap ${
                          worker.status === 'active'
                            ? 'bg-green-100 dark:bg-green-900 text-green-900 dark:text-green-100'
                            : worker.status === 'inactive'
                            ? 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-300'
                            : worker.status === 'expired'
                            ? 'bg-red-100 dark:bg-red-900 text-red-900 dark:text-red-100'
                            : 'bg-yellow-100 dark:bg-yellow-900 text-yellow-900 dark:text-yellow-100'
                        }`}
                      >
                        {worker.status
        ? worker.status.charAt(0).toUpperCase() + worker.status.slice(1)
        : 'Unknown'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <div className="text-sm whitespace-nowrap">
                        <div className="flex items-center justify-center gap-1">
                          <div
                            className={`w-1.5 h-1.5 rounded-full ${
                              worker.plan === 'pro'
                                ? 'bg-amber-500'
                                : worker.plan === 'plus'
                                ? 'bg-purple-500'
                                : 'bg-blue-500'
                            }`}
                          />
                          <span className="font-medium text-gray-900 dark:text-white">
                            {normalizeWorkerPlan(worker.plan)}
                          </span>
                        </div>
                        <p className="text-xs text-gray-500 dark:text-gray-400">{worker.coverage}%</p>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-center">
                      {premiumLoading && !premiumData[worker.id] ? (
                        <div className="flex flex-col items-center gap-1">
                          <div className="h-4 w-16 bg-gray-200/50 dark:bg-gray-700 rounded animate-pulse" />
                          <p className="text-xs text-gray-500 dark:text-gray-400">Calculating...</p>
                        </div>
                      ) : premiumData[worker.id] ? (
                        <div className="text-sm">
                          <div className="flex items-center justify-center gap-1 whitespace-nowrap">
                            {premiumData[worker.id].discount_applied > 0 && (
                              <span className="text-xs font-semibold text-green-600 dark:text-green-400">
                                -{Math.round((premiumData[worker.id].discount_applied / premiumData[worker.id].base_premium) * 100)}%
                              </span>
                            )}
                            <span className="font-semibold text-gray-900 dark:text-white">
                              {formatCurrency(premiumData[worker.id].dynamic_premium)}
                            </span>
                          </div>
                          {premiumData[worker.id].bonus_coverage_hours > 0 && (
                            <p className="text-xs text-orange-600 dark:text-orange-400">
                              +{premiumData[worker.id].bonus_coverage_hours}h
                            </p>
                          )}
                        </div>
                      ) : (
                        <p className="text-xs text-gray-500 dark:text-gray-400">—</p>
                      )}
                    </td>

                    {/* Share Profile Button */}
                    <td className="px-4 py-3 text-center relative">
                      <button
                        onClick={() => {
                          setShareDropdownId(shareDropdownId === worker.id ? null : worker.id);
                        }}
                        disabled={sharingInProgress[worker.id]}
                        className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors text-gigkavach-orange hover:text-orange-700 inline-flex disabled:opacity-50"
                        title="Share profile"
                      >
                        <Share2 className="w-4 h-4" />
                      </button>

                      {/* Share Dropdown Menu */}
                      {shareDropdownId === worker.id && (
                        <div className="absolute right-0 top-full mt-2 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-10 min-w-max whitespace-nowrap">
                          <button
                            onClick={async () => {
                              await handleShareProfile(worker);
                              setShareDropdownId(null);
                            }}
                            disabled={sharingInProgress[worker.id]}
                            className="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2 rounded-t-lg disabled:opacity-50"
                          >
                            {sharingInProgress[worker.id] ? (
                              <>
                                <div className="w-4 h-4 border-2 border-gigkavach-orange border-t-transparent rounded-full animate-spin" />
                                <span>Generating...</span>
                              </>
                            ) : copiedId === worker.id ? (
                              <>
                                <Check className="w-4 h-4 text-green-600" />
                                <span>Copied!</span>
                              </>
                            ) : (
                              <>
                                <Copy className="w-4 h-4" />
                                <span>Copy Link</span>
                              </>
                            )}
                          </button>
                          {shareLinks[worker.id] && (
                            <button
                              onClick={() => {
                                shareOnWhatsApp(shareLinks[worker.id], worker.name);
                                setShareDropdownId(null);
                              }}
                              className="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2 border-t border-gray-200 dark:border-gray-700 rounded-b-lg"
                            >
                              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                                <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.67-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.076 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.288.173-1.413-.074-.125-.272-.198-.57-.347m-5.421-7.403h-.004a9.87 9.87 0 00-4.947 1.212 9.94 9.94 0 00-4.262 4.262 9.93 9.93 0 002.063 12.09 9.95 9.95 0 004.262 1.213 9.94 9.94 0 004.262-1.213 9.94 9.94 0 001.213-4.262 9.93 9.93 0 00-1.212-4.262 9.94 9.94 0 00-4.262-1.212z" />
                              </svg>
                              <span>WhatsApp</span>
                            </button>
                          )}
                        </div>
                      )}
                    </td>

                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between pt-4">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Showing{' '}
              <span className="font-medium text-gray-900 dark:text-white">
                {(currentPage - 1) * ITEMS_PER_PAGE + 1}
              </span>{' '}
              to{' '}
              <span className="font-medium text-gray-900 dark:text-white">
                {Math.min(currentPage * ITEMS_PER_PAGE, filteredWorkers.length)}
              </span>{' '}
              of{' '}
              <span className="font-medium text-gray-900 dark:text-white">{filteredWorkers.length}</span>
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="px-3 py-1 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <span className="px-3 py-1 text-sm text-gray-600 dark:text-gray-400">
                {currentPage} / {totalPages}
              </span>
              <button
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="px-3 py-1 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          </div>

          {/* Stats Summary */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-6">
            <div className="bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
              <p className="text-gray-600 dark:text-gray-400 text-sm mb-2">Total Workers</p>
              <p className="text-3xl font-bold text-gray-900 dark:text-white">{workers.length}</p>
            </div>
            <div className="bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
              <p className="text-gray-600 dark:text-gray-400 text-sm mb-2">Active</p>
              <p className="text-3xl font-bold text-green-600 dark:text-green-400">{workers.filter((w) => w.status === 'active').length}</p>
            </div>
            <div className="bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
              <p className="text-gray-600 dark:text-gray-400 text-sm mb-2">Average Coverage</p>
              <p className="text-3xl font-bold text-gigkavach-orange">
                {workers.length === 0 ? '0%' : (workers.reduce((sum, w) => sum + w.coverage, 0) / workers.length).toFixed(0) + '%'}
              </p>
            </div>
          </div>
        </div>

        {/* Right Column: Filters Sidebar (Sticky) */}
        <div className="sticky top-6 h-fit space-y-2">
          {/* Status Filter */}
          <div className="relative overflow-hidden rounded-lg border border-gray-200/90 dark:border-gray-700/90 bg-white dark:bg-gigkavach-surface shadow-[0_1px_3px_rgba(0,0,0,0.06),0_8px_24px_-6px_rgba(15,27,45,0.08)] dark:shadow-[0_1px_3px_rgba(0,0,0,0.2),0_12px_40px_-12px_rgba(0,0,0,0.45)]">
            <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-gigkavach-orange/35 to-transparent" />
            <div className="p-3 space-y-2">
              <label className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 flex items-center gap-2">
                <SlidersHorizontal className="w-3.5 h-3.5 text-gigkavach-orange" />
                Status
              </label>
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="w-full px-2.5 py-1.5 rounded-lg border border-gray-200 dark:border-gray-600 bg-gray-50/80 dark:bg-gray-800/50 text-gray-900 dark:text-white text-xs focus:outline-none focus:ring-2 focus:ring-gigkavach-orange/80 focus:border-transparent cursor-pointer appearance-none bg-[length:0.875rem] bg-[right_0.5rem_center] bg-no-repeat pr-8 transition-shadow"
                style={{
                  backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%239ca3af'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'%3E%3C/path%3E%3C/svg%3E")`,
                }}
              >
                <option value="all">All statuses</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
                <option value="expired">Expired</option>
              </select>
            </div>
          </div>

          {/* Plan Filter */}
          <div className="relative overflow-hidden rounded-lg border border-gray-200/90 dark:border-gray-700/90 bg-white dark:bg-gigkavach-surface shadow-[0_1px_3px_rgba(0,0,0,0.06),0_8px_24px_-6px_rgba(15,27,45,0.08)] dark:shadow-[0_1px_3px_rgba(0,0,0,0.2),0_12px_40px_-12px_rgba(0,0,0,0.45)]">
            <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-gigkavach-orange/35 to-transparent" />
            <div className="p-3 space-y-1.5">
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 flex items-center gap-2">
                  <Shield className="w-3.5 h-3.5 text-gigkavach-orange" />
                  Plan
                </p>
              </div>
              <div className="flex flex-col gap-1.5">
                {PLAN_OPTIONS.map(({ value, label, idle, active, dot }) => {
                  const isOn = filterPlan === value;
                  return (
                    <button
                      key={value}
                      type="button"
                      onClick={() => setFilterPlan(value)}
                      className={`w-full flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-semibold transition-all duration-200 text-left ${
                        isOn ? `${active} shadow-md` : `bg-white/70 dark:bg-gray-800/40 ${idle} ring-1 ring-transparent`
                      }`}
                    >
                      <span
                        className={`h-2 w-2 shrink-0 rounded-full ${dot} ${isOn ? 'ring-2 ring-white/40' : 'opacity-80'}`}
                        aria-hidden
                      />
                      <span>{label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Platform Filter */}
          <div className="relative overflow-hidden rounded-lg border border-gray-200/90 dark:border-gray-700/90 bg-white dark:bg-gigkavach-surface shadow-[0_1px_3px_rgba(0,0,0,0.06),0_8px_24px_-6px_rgba(15,27,45,0.08)] dark:shadow-[0_1px_3px_rgba(0,0,0,0.2),0_12px_40px_-12px_rgba(0,0,0,0.45)]">
            <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-gigkavach-orange/35 to-transparent" />
            <div className="p-3 space-y-1.5">
              <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 flex items-center gap-2">
                <Building2 className="w-3.5 h-3.5 text-gigkavach-orange" />
                Platform
              </p>
              <div className="flex flex-col gap-1.5">
                {['all', 'Zomato', 'Swiggy'].map((platform) => {
                  const isOn = filterPlatform === platform;
                  const label = platform === 'all' ? 'All Platforms' : platform;
                  return (
                    <button
                      key={platform}
                      type="button"
                      onClick={() => setFilterPlatform(platform)}
                      className={`w-full px-2 py-0.5 rounded text-xs font-medium transition-all duration-200 text-left ${
                        isOn
                          ? platform === 'Zomato'
                            ? 'bg-red-500 text-white shadow-md shadow-red-500/25'
                            : platform === 'Swiggy'
                            ? 'bg-gigkavach-orange text-white shadow-md shadow-orange-500/25'
                            : 'bg-gradient-to-b from-gigkavach-orange to-orange-600 text-white shadow-md shadow-orange-500/25'
                          : 'bg-gray-50 dark:bg-gray-800/50 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                      }`}
                    >
                      {label}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Shift Filter */}
          <div className="relative overflow-hidden rounded-lg border border-gray-200/90 dark:border-gray-700/90 bg-white dark:bg-gigkavach-surface shadow-[0_1px_3px_rgba(0,0,0,0.06),0_8px_24px_-6px_rgba(15,27,45,0.08)] dark:shadow-[0_1px_3px_rgba(0,0,0,0.2),0_12px_40px_-12px_rgba(0,0,0,0.45)]">
            <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-gigkavach-orange/35 to-transparent" />
            <div className="p-3 space-y-1.5">
              <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 flex items-center gap-2">
                <Clock className="w-3.5 h-3.5 text-gigkavach-orange" />
                Shift
              </p>
              <div className="flex flex-col gap-1.5">
                {['all', 'Flexible', 'Morning', 'Evening', 'Night'].map((shift) => {
                  const isOn = filterShift === shift;
                  const label = shift === 'all' ? 'All Shifts' : shift;
                  return (
                    <button
                      key={shift}
                      type="button"
                      onClick={() => setFilterShift(shift)}
                      className={`w-full px-2 py-0.5 rounded text-xs font-medium transition-all duration-200 text-left ${
                        isOn
                          ? 'bg-gradient-to-b from-amber-500 to-amber-600 text-white shadow-md shadow-amber-500/25'
                          : 'bg-gray-50 dark:bg-gray-800/50 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                      }`}
                    >
                      {label}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Gig Score Filter */}
          <div className="relative overflow-hidden rounded-lg border border-gray-200/90 dark:border-gray-700/90 bg-white dark:bg-gigkavach-surface shadow-[0_1px_3px_rgba(0,0,0,0.06),0_8px_24px_-6px_rgba(15,27,45,0.08)] dark:shadow-[0_1px_3px_rgba(0,0,0,0.2),0_12px_40px_-12px_rgba(0,0,0,0.45)]">
            <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-gigkavach-orange/35 to-transparent" />
            <div className="p-3 space-y-1.5">
              <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 flex items-center gap-2">
                <Zap className="w-3.5 h-3.5 text-gigkavach-orange" />
                Gig Score
              </p>
              <div className="flex flex-col gap-1.5">
                {[
                  { value: 'all', label: 'All Scores' },
                  { value: '80+', label: '80+ (Premium)' },
                  { value: '70+', label: '70+ (Good)' },
                  { value: 'below70', label: 'Below 70' },
                ].map(({ value, label }) => {
                  const isOn = filterGigScore === value;
                  return (
                    <button
                      key={value}
                      type="button"
                      onClick={() => setFilterGigScore(value)}
                      className={`w-full px-2 py-0.5 rounded text-xs font-medium transition-all duration-200 text-left ${
                        isOn
                          ? 'bg-gradient-to-b from-blue-500 to-blue-600 text-white shadow-md shadow-blue-500/25'
                          : 'bg-gray-50 dark:bg-gray-800/50 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                      }`}
                    >
                      {label}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Worker Count */}
          <div className="text-xs text-gray-500 dark:text-gray-400 pt-2 px-2 text-center">
            {filteredWorkers.length === workers.length
              ? `${workers.length} workers`
              : `${filteredWorkers.length} of ${workers.length}`}
          </div>
        </div>
      </div>

      {/* Worker Profile Drawer */}

      <WorkerModal
        workerId={selectedWorkerId}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />
    </div>
  );
};
