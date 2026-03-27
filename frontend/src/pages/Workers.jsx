import { useState, useMemo, useRef } from 'react';
import { Search, Eye, TrendingUp, AlertTriangle, X, Phone, MapPin, Clock, Zap, DollarSign, Activity } from 'lucide-react';
import { useEffect } from 'react';
import { formatPhoneNumber, formatCurrency, getInitials } from '../utils/formatters';
import { workerAPI } from '../api/workers';
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



export const Workers = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const handleRowClick = (worker) => {
  setSelectedWorkerId(worker.id);
  setIsModalOpen(true);
};

  // Modal state
const [selectedWorkerId, setSelectedWorkerId] = useState(null);
const [isModalOpen, setIsModalOpen] = useState(false);
 // const [selectedWorker, setSelectedWorker] = useState(null);
  //const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const [workers, setWorkers] = useState([]);
  const [loading, setLoading] = useState(true);

  // ✅ pagination state (MUST be at top)
  const [currentPage, setCurrentPage] = useState(1);
  const ITEMS_PER_PAGE = 5;

  // ✅ FETCH ONCE
  const fetchWorkers = async () => {
    setLoading(true);
    try {
      const response = await workerAPI.getAll();

      const formatted = response.data.map((w) => ({
        id: w.id,
        name: w.name,
        phone: w.phone,
        upi: w.upi_id || 'N/A',
        zone: w.zone || 'N/A',
        status: w.status || 'inactive',
        plan: w.plan,
        premium:
          w.plan === 'Shield Basic'
            ? 69
            : w.plan === 'Shield Plus'
            ? 89
            : 99,
        coverage: w.coverage,
        coverageWindow: 'Flexible',

        last7DaysEarnings: [500, 700, 600, 800, 650, 720, 900],
        dciHistory: [],
        fraudStatus: 'clean',
        payoutHistory: [],
      }));

      setWorkers(formatted);
    } catch (err) {
      console.error('Error fetching workers:', err);
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

    return result;
  }, [workers, searchQuery, filterStatus]);

  // ✅ RESET PAGE WHEN FILTER CHANGES
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, filterStatus]);

  // ✅ PAGINATION
  const totalPages = Math.ceil(filteredWorkers.length / ITEMS_PER_PAGE);

  const paginatedWorkers = filteredWorkers.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  );

  const start = (currentPage - 1) * ITEMS_PER_PAGE + 1;
  const end = Math.min(currentPage * ITEMS_PER_PAGE, filteredWorkers.length);

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

      {/* Controls */}
      <div className="bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 p-4 shadow-sm">
        <div className="flex flex-col md:flex-row gap-4">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search by name, phone, or zone..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-gigkavach-orange focus:border-transparent"
            />
          </div>

          {/* Filter Button */}
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="px-4 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-gigkavach-orange"
          >
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="expired">Expired</option>
          </select>
        </div>
      </div>

      {/* Workers Table */}
      <div className="bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                  Worker
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                  Zone
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                  Shield Policy
                </th>
                <th className="px-6 py-3 text-right text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {paginatedWorkers.map((worker) => (
                <tr
                  key={worker.id}
                  className="border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                >
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-gigkavach-orange flex items-center justify-center text-white font-bold">
                          {getInitials(worker.name?.split(' ')[0] || '',worker.name?.split(' ')[1] || '')}
                      </div>
                      <div>
                        <p
  onClick={() => handleRowClick(worker)} // new function for modal
  className="font-medium text-orange-500 cursor-pointer hover:underline"
>
  {worker.name}
</p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">{formatPhoneNumber(worker.phone)}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-300">{worker.zone}</td>
                  <td className="px-6 py-4">
                    <span
                      className={`inline-block px-3 py-1 rounded-full text-xs font-semibold ${
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
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium text-gray-900 dark:text-white">
                      <div className="flex items-center gap-2">
                        <div
                          className={`w-2 h-2 rounded-full ${             worker.plan === 'Shield Pro'                ? 'bg-amber-500'                : worker.plan === 'Shield Plus'                ? 'bg-blue-500'                : 'bg-green-500'            }`}
                        />
                        {worker.plan}
                      </div>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{worker.coverage}% coverage</p>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button
                      onClick={() => handleRowClick(worker)}
                      className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors text-gigkavach-orange hover:text-orange-700"
                      title="View profile"
                    >
                      <Eye className="w-5 h-5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
<div className="flex items-center justify-between mt-4 px-4 pb-4">
<p className="text-sm text-gray-600 dark:text-gray-400">
  Showing {start}-{end} of {filteredWorkers.length}
</p>

  <div className="flex gap-2">
    <button
      onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
      disabled={currentPage === 1}
      className="px-3 py-1 rounded-lg border text-sm disabled:opacity-50"
    >
      Prev
    </button>

    <button
      onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
      disabled={currentPage === totalPages || totalPages === 0}
      className="px-3 py-1 rounded-lg border text-sm disabled:opacity-50"
    >
      Next
    </button>
  </div>
</div>
        {/* Empty State */}
        {workers.length === 0 && (
          <div className="p-12 text-center">
            <Search className="w-12 h-12 text-gray-400 dark:text-gray-600 mx-auto mb-3" />
            <p className="text-gray-600 dark:text-gray-400 font-medium">No workers found</p>
            <p className="text-sm text-gray-500 dark:text-gray-500 mt-1">Try adjusting your filters or search criteria</p>
          </div>
        )}
      </div>

      {/* Stats Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
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

      {/* Worker Profile Drawer */}

<WorkerModal
  workerId={selectedWorkerId}
  isOpen={isModalOpen}
  onClose={() => setIsModalOpen(false)}
/>
    </div>
  );
};

// Worker Modal Component
const WorkerModal = ({ workerId, isOpen, onClose }) => {
  const [workerData, setWorkerData] = useState(null);
  const [loading, setLoading] = useState(false);
  const modalRef = useRef();

  // Fetch worker details when modal opens
  useEffect(() => {
    if (!workerId || !isOpen) {
      setWorkerData(null);
      return;
    }

    setLoading(true);
    setWorkerData(null); // Clear previous worker data
    const fetchWorker = async () => {
      try {
        const data = await workerAPI.getById(workerId);
        console.log('API Response:', data); // Debug log

        const formatPlan = (plan) => {
          if (!plan) return 'N/A';
          if (plan.toLowerCase().includes('basic')) return 'Shield Basic';
          if (plan.toLowerCase().includes('plus')) return 'Shield Plus';
          if (plan.toLowerCase().includes('pro')) return 'Shield Pro';
          return plan;
        };

        // Determine status based on policy
        const status = data.policy?.status || 'inactive';

        const mappedWorker = {
          id: data.worker.id,
          name: data.worker.name,
          phone: data.worker.phone,
          upi: data.worker.upi_id || 'N/A',
          zone: data.worker.pin_codes?.join(', ') || 'N/A',
          shift: data.worker.shift,
          shift_start: data.worker.shift_start,
          shift_end: data.worker.shift_end,
          language: data.worker.language,
          plan: formatPlan(data.policy?.plan || data.worker.plan),
          premium: data.policy?.weekly_premium || 0,
          coverage: data.policy?.coverage_pct || data.worker.coverage_pct || 0,
          status: status,
          payoutHistory: data.payouts || [],
          activityLog: data.activities || [],
        };

        console.log('Mapped Worker:', mappedWorker); // Debug log
        setWorkerData(mappedWorker);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchWorker();
  }, [workerId, isOpen]);

  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (modalRef.current && !modalRef.current.contains(e.target)) {
        onClose();
      }
    };
    if (isOpen) document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const maskedUPI = workerData?.upi
    ? workerData.upi.substring(0, 5) + '****' + workerData.upi.substring(workerData.upi.length - 4)
    : 'N/A';

  const getPlanColor = (plan) => {
    if (!plan) return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200';
    if (plan.toLowerCase().includes('pro')) return 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200';
    if (plan.toLowerCase().includes('plus')) return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
    return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
  };

  const getStatusColor = (status) => {
    if (status === 'active') return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
    if (status === 'inactive') return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200';
    if (status === 'expired') return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
    return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex justify-center items-start z-50 p-4 overflow-y-auto pt-8">
      <div 
        ref={modalRef} 
        className="bg-white dark:bg-gigkavach-navy rounded-2xl max-w-2xl w-full shadow-2xl overflow-hidden animate-in fade-in slide-in-from-top-4 duration-300"
      >
        {/* Header with Profile */}
        <div className="bg-gradient-to-r from-gigkavach-orange to-orange-600 p-6 text-white">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-full bg-white/20 flex items-center justify-center text-2xl font-bold">
                {getInitials(workerData?.name?.split(' ')[0] || '', workerData?.name?.split(' ')[1] || '')}
              </div>
              <div>
                <h2 className="text-2xl font-bold">{workerData?.name || 'Loading...'}</h2>
                <div className="flex gap-2 mt-2 flex-wrap">
                  <span className={`text-xs px-3 py-1 rounded-full font-semibold ${getPlanColor(workerData?.plan)}`}>
                    {workerData?.plan || 'N/A'}
                  </span>
                  <span className={`text-xs px-3 py-1 rounded-full font-semibold ${getStatusColor(workerData?.status)}`}>
                    {workerData?.status ? workerData.status.charAt(0).toUpperCase() + workerData.status.slice(1) : 'Inactive'}
                  </span>
                </div>
              </div>
            </div>
            <button 
              onClick={onClose} 
              className="p-2 rounded-lg hover:bg-white/20 transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
          </div>
        </div>

        {/* Content */}
        {loading ? (
          <div className="p-8 text-center">
            <div className="animate-pulse flex justify-center mb-4">
              <div className="w-8 h-8 border-4 border-gigkavach-orange border-t-transparent rounded-full animate-spin"></div>
            </div>
            <p className="text-gray-500 dark:text-gray-400">Loading worker details...</p>
          </div>
        ) : (
          <div className="p-6 space-y-6 max-h-[calc(100vh-300px)] overflow-y-auto">
            {/* Contact Info Grid */}
            <section>
              <h3 className="text-sm font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <Phone className="w-4 h-4 text-gigkavach-orange" />
                Contact Information
              </h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                  <p className="text-xs text-gray-600 dark:text-gray-400 mb-1 font-semibold">Phone</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">{formatPhoneNumber(workerData?.phone)}</p>
                </div>
                <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                  <p className="text-xs text-gray-600 dark:text-gray-400 mb-1 font-semibold">UPI ID</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white font-mono">{maskedUPI}</p>
                </div>
                <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                  <p className="text-xs text-gray-600 dark:text-gray-400 mb-1 font-semibold">Language</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white capitalize">{workerData?.language || 'N/A'}</p>
                </div>
                <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                  <p className="text-xs text-gray-600 dark:text-gray-400 mb-1 font-semibold">Shift Type</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white capitalize">{workerData?.shift || 'N/A'}</p>
                </div>
              </div>
            </section>

            {/* Zone & Shift Timings */}
            <section>
              <h3 className="text-sm font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <MapPin className="w-4 h-4 text-gigkavach-orange" />
                Service Area & Schedule
              </h3>
              <div className="space-y-3">
                <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                  <p className="text-xs text-gray-600 dark:text-gray-400 mb-2 font-semibold">Operating Zones</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">{workerData?.zone}</p>
                </div>
                <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                  <p className="text-xs text-gray-600 dark:text-gray-400 mb-2 font-semibold flex items-center gap-2">
                    <Clock className="w-3 h-3" />
                    Shift Timings
                  </p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {workerData?.shift_start} - {workerData?.shift_end}
                  </p>
                </div>
              </div>
            </section>

            {/* Policy Details */}
            <section>
              <h3 className="text-sm font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <Zap className="w-4 h-4 text-gigkavach-orange" />
                Insurance Policy
              </h3>
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-gradient-to-br from-gigkavach-orange/10 to-orange-50 dark:from-gigkavach-orange/20 dark:to-gigkavach-navy p-4 rounded-lg border border-gigkavach-orange/20">
                  <p className="text-xs text-gray-600 dark:text-gray-400 mb-2 font-semibold">Plan Tier</p>
                  <p className="text-lg font-bold text-gigkavach-orange">{workerData?.plan || 'N/A'}</p>
                </div>
                <div className="bg-gradient-to-br from-green-50 to-green-100 dark:from-green-900/20 dark:to-gigkavach-navy p-4 rounded-lg border border-green-200 dark:border-green-800">
                  <p className="text-xs text-gray-600 dark:text-gray-400 mb-2 font-semibold">Weekly Premium</p>
                  <p className="text-lg font-bold text-green-700 dark:text-green-400">{formatCurrency(workerData?.premium)}</p>
                </div>
                <div className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/20 dark:to-gigkavach-navy p-4 rounded-lg border border-blue-200 dark:border-blue-800">
                  <p className="text-xs text-gray-600 dark:text-gray-400 mb-2 font-semibold">Coverage</p>
                  <p className="text-lg font-bold text-blue-700 dark:text-blue-400">{workerData?.coverage}%</p>
                </div>
              </div>
            </section>

            {/* Payout History */}
            <section>
              <h3 className="text-sm font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <DollarSign className="w-4 h-4 text-gigkavach-orange" />
                Recent Payouts
              </h3>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {workerData?.payoutHistory && workerData.payoutHistory.length > 0 ? (
                  workerData.payoutHistory.slice(0, 10).map((p, idx) => (
                    <div 
                      key={idx} 
                      className="flex items-center justify-between bg-gray-50 dark:bg-gray-800 p-3 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                    >
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-900 dark:text-white">
                          {new Date(p.triggered_at).toLocaleDateString()}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {new Date(p.triggered_at).toLocaleTimeString()}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-bold text-green-600 dark:text-green-400">
                          {formatCurrency(p.final_amount)}
                        </p>
                        <span className={`text-xs px-2 py-1 rounded font-semibold ${
                          p.status === 'paid' 
                            ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                            : 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200'
                        }`}>
                          {p.status.charAt(0).toUpperCase() + p.status.slice(1)}
                        </span>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">No payouts yet</p>
                )}
              </div>
            </section>

            {/* Activity Log */}
            <section>
              <h3 className="text-sm font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <Activity className="w-4 h-4 text-gigkavach-orange" />
                Recent Activity
              </h3>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {workerData?.activityLog && workerData.activityLog.length > 0 ? (
                  workerData.activityLog.slice(0, 20).map((act, idx) => (
                    <div 
                      key={idx}
                      className="flex gap-3 bg-gray-50 dark:bg-gray-800 p-3 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                    >
                      <div className="w-2 h-2 rounded-full bg-gigkavach-orange mt-1.5 flex-shrink-0"></div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 dark:text-white">
                          {act.description}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {new Date(act.date).toLocaleDateString()} • {new Date(act.date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </p>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">No activities recorded</p>
                )}
              </div>
            </section>
          </div>
        )}
      </div>
    </div>
  );
};
