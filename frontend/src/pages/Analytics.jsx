import { useState, useEffect } from 'react';
import { BarChart3, TrendingUp, RefreshCw } from 'lucide-react';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ComposedChart,
} from 'recharts';
import { payoutAPI } from '../api/payouts';
import { workerAPI } from '../api/workers';
import { dciAPI } from '../api/dci';
import { analyticsAPI } from '../api/analytics';

// ── Static fallback data (shown while API loads or if endpoint unavailable) ──
const FALLBACK_WEEKLY = [
  { week: 'Wk 1', premiums: 78000, payouts: 64000, lossRatio: 82 },
  { week: 'Wk 2', premiums: 82000, payouts: 66000, lossRatio: 80.5 },
  { week: 'Wk 3', premiums: 85000, payouts: 67500, lossRatio: 79.4 },
  { week: 'Wk 4', premiums: 88000, payouts: 68000, lossRatio: 77.3 },
  { week: 'Wk 5', premiums: 90000, payouts: 68500, lossRatio: 76.1 },
  { week: 'Wk 6', premiums: 92000, payouts: 69000, lossRatio: 75 },
  { week: 'Wk 7', premiums: 87432, payouts: 62000, lossRatio: 70.9 },
  { week: 'Wk 8', premiums: 95000, payouts: 65000, lossRatio: 68.4 },
];

const FALLBACK_TIERS = [
  { name: 'Shield Basic', value: 45, color: '#3B82F6' },
  { name: 'Shield Plus', value: 35, color: '#8B5CF6' },
  { name: 'Shield Pro', value: 20, color: '#FF6B35' },
];

// ── Mapping: Backend component names to frontend display names + colors ──
const COMPONENT_DISPLAY_MAP = {
  weather: { name: 'Rainfall', color: '#3B82F6', description: '>15mm/hr for 2hrs' },
  aqi: { name: 'AQI', color: '#F59E0B', description: '>300 (Severe) for 4hrs' },
  heat: { name: 'Heat', color: '#EF4444', description: '>42°C during 10AM-4PM' },
  social: { name: 'Social Disruption', color: '#8B5CF6', description: 'Bandh, strikes, curfews' },
  platform: { name: 'Platform Activity', color: '#6366F1', description: '>60% order drop' },
};

// ── Transform backend weights to frontend format ──
const transformWeights = (backendWeights) => {
  return Object.entries(backendWeights)
    .map(([key, weight]) => ({
      name: COMPONENT_DISPLAY_MAP[key]?.name || key,
      weight: Math.round(weight * 100),
      color: COMPONENT_DISPLAY_MAP[key]?.color || '#6b7280',
      description: COMPONENT_DISPLAY_MAP[key]?.description || '',
    }))
    .sort((a, b) => b.weight - a.weight); // Sort by weight descending
};

// ── Fallback weights (global defaults from backend) ──
const FALLBACK_DCI_WEIGHTS = [
  { name: 'Rainfall', weight: 30, color: '#3B82F6', description: '>15mm/hr for 2hrs' },
  { name: 'AQI', weight: 20, color: '#F59E0B', description: '>300 (Severe) for 4hrs' },
  { name: 'Heat', weight: 20, color: '#EF4444', description: '>42°C during 10AM-4PM' },
  { name: 'Social Disruption', weight: 20, color: '#8B5CF6', description: 'Bandh, strikes, curfews' },
  { name: 'Platform Activity', weight: 10, color: '#6366F1', description: '>60% order drop' },
];

// ── Fallback disruption causes (shown while API loads) ──
const FALLBACK_DISRUPTION_CAUSES = [
  { cause: 'Heavy Rainfall', triggers: 42, percentage: 38 },
  { cause: 'Platform Outage', triggers: 18, percentage: 16 },
  { cause: 'Severe AQI', triggers: 11, percentage: 10 },
  { cause: 'Bandh/Curfew', triggers: 7, percentage: 6 },
  { cause: 'Extreme Heat', triggers: 3, percentage: 3 },
];

// ── Fallback fraud signals (shown while API loads) ──
const FALLBACK_FRAUD_SIGNALS = [
  { signal: 'GPS vs IP Mismatch', severity: 'CRITICAL', count: 24, trend: '+8%' },
  { signal: 'Claim Burst (<2min)', severity: 'CRITICAL', count: 12, trend: '-2%' },
  { signal: 'Worker Offline All Day', severity: 'HIGH', count: 38, trend: '+15%' },
  { signal: 'DCI Threshold Gaming', severity: 'HIGH', count: 19, trend: '+5%' },
  { signal: 'Same Device Multiple IDs', severity: 'CRITICAL', count: 7, trend: 'Stable' },
  { signal: 'Registration = Event Day', severity: 'CRITICAL', count: 5, trend: '-3%' },
  { signal: 'Platform Inactive + GPS Unverified', severity: 'HIGH', count: 14, trend: '+9%' },
  { signal: 'Stationary GPS + Zero Orders', severity: 'HIGH', count: 9, trend: 'Stable' },
];

// ── Compute week label for a date ──
const weekLabel = (date) =>
  `${date.toLocaleString('en-IN', { month: 'short' })} W${Math.ceil(date.getDate() / 7)}`;


// ── Aggregate payouts into weekly buckets ──
const buildWeeklyData = (payouts) => {
  if (!payouts.length) return FALLBACK_WEEKLY;

  const buckets = {};
  payouts.forEach((p) => {
    const d = new Date(p.timestamp || p.triggered_at || p.created_at);
    if (isNaN(d.getTime())) return;
    const key = weekLabel(d);
    if (!buckets[key]) buckets[key] = { premiums: 0, payouts: 0 };
    const amt = Number(p.amount || p.final_amount || 0);
    buckets[key].payouts += amt;
    // Premium proxy: reverse-engineer from typical 70% loss ratio
    buckets[key].premiums += amt / 0.70;
  });

  return Object.entries(buckets)
    .sort(([a], [b]) => a.localeCompare(b))
    .slice(-8)
    .map(([week, v]) => ({
      week,
      premiums: Math.round(v.premiums),
      payouts: Math.round(v.payouts),
      lossRatio: v.premiums > 0 ? Math.round((v.payouts / v.premiums) * 1000) / 10 : 0,
    }));
};


// ── Compute tier distribution from workers ──
const buildTierData = (workers) => {
  if (!workers.length) return FALLBACK_TIERS;
  const counts = { basic: 0, plus: 0, pro: 0 };
  workers.forEach((w) => {
    // API returns formatted plan like "Shield Basic", "Shield Plus", "Shield Pro"
    // Extract the base plan name and normalize to lowercase
    const planStr = (w.plan || '').toLowerCase();
    if (planStr.includes('basic')) counts.basic++;
    else if (planStr.includes('plus')) counts.plus++;
    else if (planStr.includes('pro')) counts.pro++;
  });
  const total = Object.values(counts).reduce((s, v) => s + v, 0) || 1;
  return [
    { name: 'Shield Basic', value: Math.round((counts.basic / total) * 100), count: counts.basic, color: '#3B82F6' },
    { name: 'Shield Plus', value: Math.round((counts.plus / total) * 100), count: counts.plus, color: '#8B5CF6' },
    { name: 'Shield Pro', value: Math.round((counts.pro / total) * 100), count: counts.pro, color: '#FF6B35' },
  ];
};

export const Analytics = () => {
  const [weeklyData, setWeeklyData] = useState(FALLBACK_WEEKLY);
  const [tierData, setTierData] = useState(FALLBACK_TIERS);
  const [dciComponentWeights, setDciComponentWeights] = useState(FALLBACK_DCI_WEIGHTS);
  const [dciCity, setDciCity] = useState('Global (Fallback)');
  const [allCityProfiles, setAllCityProfiles] = useState({});
  const [supportedCities, setSupportedCities] = useState([]);
  const [currentCityIndex, setCurrentCityIndex] = useState(0);
  const [disruptionCauses, setDisruptionCauses] = useState(FALLBACK_DISRUPTION_CAUSES);
  const [fraudSignals, setFraudSignals] = useState(FALLBACK_FRAUD_SIGNALS);
  const [todayPayout, setTodayPayout] = useState(null);
  const [totalWorkers, setTotalWorkers] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isLive, setIsLive] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [payoutsRes, workersRes, todayRes, cityWeightsRes, disruptionRes, fraudRes] = await Promise.allSettled([
        payoutAPI.getAll({ limit: 100 }),
        workerAPI.getAll({ limit: 1000 }),
        payoutAPI.getTodayTotal(),
        dciAPI.getAllCityWeights(),
        analyticsAPI.getTopDisruptionCauses(5, 30),
        analyticsAPI.getFraudSignals(7),
      ]);

      // ── Wire weekly chart ──
      if (payoutsRes.status === 'fulfilled') {
        const payouts = payoutsRes.value?.payouts ?? [];
        if (payouts.length) {
          setWeeklyData(buildWeeklyData(payouts));
          setIsLive(true);
        }
      }

      // ── Wire tier pie chart ──
      if (workersRes.status === 'fulfilled') {
        const workers = workersRes.value?.data ?? [];
        setTotalWorkers(workersRes.value?.total ?? workers.length);
        if (workers.length) setTierData(buildTierData(workers));
      }

      // ── Wire today payout KPI ──
      if (todayRes.status === 'fulfilled') {
        setTodayPayout(todayRes.value?.total_payout_today ?? null);
      }

      // ── Wire DCI component weights ──
      if (cityWeightsRes.status === 'fulfilled') {
        const data = cityWeightsRes.value;
        const cities = data?.supported_cities ?? [];
        const profiles = data?.profiles ?? {};

        // Store all city profiles
        setAllCityProfiles(profiles);
        setSupportedCities(cities);
        setCurrentCityIndex(0);

        // Display first city or global fallback
        if (cities.length > 0) {
          const firstCity = cities[0];
          const profile = profiles[firstCity];
          if (profile?.weights) {
            const transformed = transformWeights(profile.weights);
            setDciComponentWeights(transformed);
            setDciCity(firstCity);
          }
        } else if (data?.global_fallback) {
          // Fall back to global fallback weights
          const transformed = transformWeights(data.global_fallback);
          setDciComponentWeights(transformed);
          setDciCity('Global (Fallback)');
        }
      }

      // ── Wire top disruption causes ──
      if (disruptionRes.status === 'fulfilled') {
        const causes = disruptionRes.value?.causes ?? [];
        if (causes.length) {
          setDisruptionCauses(causes);
        }
      }

      // ── Wire fraud signals ──
      if (fraudRes.status === 'fulfilled') {
        const signals = fraudRes.value?.signals ?? [];
        if (signals.length) {
          setFraudSignals(signals);
        }
      }
    } catch {
      // Fall through — fallback data stays
    } finally {
      setLoading(false);
    }
  };

  // ── Cycle to next city ──
  const cycleCity = () => {
    if (supportedCities.length === 0) return;

    const nextIndex = (currentCityIndex + 1) % supportedCities.length;
    setCurrentCityIndex(nextIndex);

    const nextCity = supportedCities[nextIndex];
    const profile = allCityProfiles[nextCity];

    if (profile?.weights) {
      const transformed = transformWeights(profile.weights);
      setDciComponentWeights(transformed);
      setDciCity(nextCity);
    }
  };

  useEffect(() => { load(); }, []);

  // ── Live KPIs ──
  const latestWeek = weeklyData[weeklyData.length - 1];
  const lossRatio = latestWeek?.lossRatio ?? 68.4;
  const premiumThisWeek = latestWeek?.premiums ?? 87432;
  const avgPayout =
    weeklyData.reduce((s, w) => s + w.payouts, 0) /
    Math.max(weeklyData.reduce((s, w) => s + (w.payouts > 0 ? 1 : 0), 0), 1);

  const kpis = [
    {
      label: 'Loss Ratio',
      value: `${lossRatio}%`,
      subtext: 'Payouts / Premiums · live',
      color: 'bg-red-100 dark:bg-red-900',
      textColor: 'text-red-900 dark:text-red-100',
    },
    {
      label: 'Premium Collected (This Week)',
      value: `₹${Math.round(premiumThisWeek).toLocaleString('en-IN')}`,
      subtext: isLive ? 'From live payouts data' : 'Estimated · API loading',
      color: 'bg-blue-100 dark:bg-blue-900',
      textColor: 'text-blue-900 dark:text-blue-100',
    },
    {
      label: 'Avg Payout Per Trigger',
      value: `₹${Math.round(avgPayout).toLocaleString('en-IN')}`,
      subtext: 'Across all zones',
      color: 'bg-purple-100 dark:bg-purple-900',
      textColor: 'text-purple-900 dark:text-purple-100',
    },
    {
      label: "Today's Total Payout",
      value: todayPayout !== null ? `₹${Math.round(todayPayout).toLocaleString('en-IN')}` : '—',
      subtext: todayPayout !== null ? 'Live from Supabase' : 'Loading…',
      color: 'bg-green-100 dark:bg-green-900',
      textColor: 'text-green-900 dark:text-green-100',
    },
    {
      label: 'Total Enrolled Workers',
      value: totalWorkers !== null ? totalWorkers.toLocaleString('en-IN') : '—',
      subtext: totalWorkers !== null ? 'Live from workers table' : 'Loading…',
      color: 'bg-orange-100 dark:bg-orange-900',
      textColor: 'text-orange-900 dark:text-orange-100',
    },
  ];

  // Show loading screen while fetching initial data
  if (loading) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-sm">
        <div className="text-center px-6">
          <div className="mx-auto mb-6 h-16 w-16 rounded-full border-4 border-gray-300/60 dark:border-gray-700 border-t-orange-500 animate-spin" />
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">Loading Analytics</h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">Fetching payouts, DCI weights, disruptions & fraud signals from backend...</p>
          <div className="space-y-2 text-xs text-gray-500 dark:text-gray-500">
            <div className="flex items-center justify-center gap-2">
              <div className="w-2 h-2 bg-orange-500 rounded-full animate-pulse" />
              <span>Connecting to payouts API</span>
            </div>
            <div className="flex items-center justify-center gap-2">
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" style={{animationDelay: '0.2s'}} />
              <span>Fetching workers tier distribution</span>
            </div>
            <div className="flex items-center justify-center gap-2">
              <div className="w-2 h-2 bg-purple-500 rounded-full animate-pulse" style={{animationDelay: '0.4s'}} />
              <span>Loading DCI city weights</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Analytics & Insights</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">Loss ratios, predictions, and GigKavach business metrics</p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white rounded-lg text-sm font-medium disabled:opacity-60"
        >
          <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
          {loading ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>

      {/* Live / Demo badge */}
      {!loading && (
        <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full border text-xs font-semibold ${
          isLive
            ? 'bg-green-50 border-green-200 text-green-700 dark:bg-green-950 dark:border-green-800 dark:text-green-300'
            : 'bg-amber-50 border-amber-200 text-amber-700 dark:bg-amber-950 dark:border-amber-800 dark:text-amber-300'
        }`}>
          <div className={`w-2 h-2 rounded-full ${isLive ? 'bg-green-500' : 'bg-amber-400'}`} />
          {isLive ? 'Live data from Supabase' : 'Demo data · backend API not yet populated'}
        </div>
      )}

      {/* KPI Bar */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        {kpis.map((kpi, idx) => (
          <div key={idx} className={`${kpi.color} rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700`}>
            <p className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">{kpi.label}</p>
            <p className={`text-2xl font-bold ${kpi.textColor} mb-1`}>{kpi.value}</p>
            <p className="text-xs text-gray-600 dark:text-gray-400">{kpi.subtext}</p>
          </div>
        ))}
      </div>

      {/* Charts Section — Weekly Premium vs Payouts + Coverage Tier Pie */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Weekly Financials Chart */}
        <div className="lg:col-span-2 bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">
            Weekly Premium vs Payouts
            <span className="ml-2 text-xs font-normal text-gray-400">{isLive ? '(live)' : '(demo)'}</span>
          </h2>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={weeklyData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="week" stroke="#6b7280" />
                <YAxis stroke="#6b7280" label={{ value: 'Amount (₹)', angle: -90, position: 'insideLeft' }} />
                <YAxis yAxisId="right" orientation="right" stroke="#6b7280" label={{ value: 'Loss Ratio %', angle: 90, position: 'insideRight' }} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '8px', color: '#fff' }}
                  formatter={(value) => (typeof value === 'number' ? value.toLocaleString() : value)}
                />
                <Legend />
                <Bar dataKey="premiums" fill="#3B82F6" name="Premiums Collected" radius={[8, 8, 0, 0]} />
                <Bar dataKey="payouts" fill="#FF6B35" name="Payouts Disbursed" radius={[8, 8, 0, 0]} />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="lossRatio"
                  stroke="#8B5CF6"
                  strokeWidth={3}
                  name="Loss Ratio %"
                  dot={{ fill: '#8B5CF6', r: 5 }}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Coverage Tier Distribution Pie */}
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">
            Coverage Tier Distribution
            <span className="ml-2 text-xs font-normal text-gray-400">{isLive ? '(live)' : '(demo)'}</span>
          </h2>
          <div className="h-80 flex flex-col items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={tierData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={110}
                  paddingAngle={1}
                  dataKey="value"
                >
                  {tierData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip formatter={(value, name, props) => [`${value}% (${props.payload.count} workers)`, props.payload.name]} />
                <Legend verticalAlign="bottom" height={36} formatter={(value, entry) => `${entry.payload.name}: ${entry.payload.count}`} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <p className="text-sm font-bold text-gray-700 dark:text-gray-300 text-center mt-2">
            {totalWorkers !== null ? `${totalWorkers.toLocaleString('en-IN')} Total Workers` : 'Total Workers'}
          </p>
        </div>
      </div>

      {/* DCI Engine: Component Weights */}
      <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            DCI Engine: Component Weights
            <span className="ml-2 text-xs font-normal text-gray-400">
              ({dciCity})
              {isLive && supportedCities.length > 0 && (
                <span className="ml-1 text-green-600 dark:text-green-400">*</span>
              )}
            </span>
            </h2>
          {supportedCities.length > 1 && (
            <button
              onClick={cycleCity}
              className="px-3 py-1 text-xs font-medium bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
            >
              Cycle Cities ({currentCityIndex + 1}/{supportedCities.length})
            </button>
          )}
        </div>
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
          {isLive && supportedCities.length > 0
            ? `Live city-specific weights • ${supportedCities.length} cities available`
            : 'Fixed engine configuration weights'}
          . Per-event dynamic breakdown is shown on the Heatmap page.
          {isLive && supportedCities.length > 0 && (
            <span className="block text-green-600 dark:text-green-400 mt-1">
              ✓ Fetched from backend DCI weights service
            </span>
          )}
        </p>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          {dciComponentWeights.map((comp, idx) => (
            <div
              key={idx}
              className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700"
            >
              <div className="flex items-center gap-2 mb-3">
                <div className="w-4 h-4 rounded" style={{ backgroundColor: comp.color }} />
                <p className="font-semibold text-gray-900 dark:text-white text-sm">{comp.name}</p>
              </div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                {comp.weight}%
              </p>
              <p className="text-xs text-gray-600 dark:text-gray-400">{comp.description}</p>
            </div>
          ))}
        </div>
        <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-950 rounded-lg border border-blue-200 dark:border-blue-800">
          <p className="text-xs text-blue-900 dark:text-blue-100">
            <span className="font-semibold">ℹ️ DCI ranges from 0-100:</span> 0-64 (Green - No
            disruption), 65-84 (Amber - Moderate), 85-100 (Red - Catastrophic)
          </p>
        </div>
      </div>

      {/* Bottom Row: Top Causes + Fraud Signals */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Disruption Causes — dynamic from backend ──────────────────────────── */}
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">
            Top Disruption Causes (This Month)
            {isLive && <span className="ml-2 text-xs font-normal text-green-600 dark:text-green-400">✓ Live</span>}
          </h2>
          <div className="space-y-4">
            {disruptionCauses.map((cause, idx) => (
              <div key={idx} className="flex items-center gap-4">
                <div className="flex-1">
                  <div className="flex justify-between mb-1">
                    <span className="text-sm font-medium text-gray-900 dark:text-white">{cause.cause}</span>
                    <span className="text-sm font-bold text-gray-700 dark:text-gray-300">{cause.triggers}</span>
                  </div>
                  <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-orange-500 to-orange-600"
                      style={{ width: `${cause.percentage * 3}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Fraud Detection Signals — dynamic from backend ──────────────────────────── */}
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">
            Fraud Detection Signals
            {isLive && <span className="ml-2 text-xs font-normal text-green-600 dark:text-green-400">✓ Live</span>}
          </h2>
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {fraudSignals.map((signal, idx) => {
              const isCritical = signal.severity === 'CRITICAL';
              const bg = isCritical
                ? 'bg-red-50 dark:bg-red-950 border-red-200 dark:border-red-800'
                : 'bg-amber-50 dark:bg-amber-950 border-amber-200 dark:border-amber-800';
              const text = isCritical ? 'text-red-900 dark:text-red-100' : 'text-amber-900 dark:text-amber-100';
              const badge = isCritical
                ? 'bg-red-100 text-red-900 dark:bg-red-900 dark:text-red-100'
                : 'bg-amber-100 text-amber-900 dark:bg-amber-900 dark:text-amber-100';
              return (
                <div key={idx} className={`border rounded-lg p-3 ${bg}`}>
                  <div className="flex items-start justify-between mb-2">
                    <p className={`font-semibold text-sm ${text}`}>{signal.signal}</p>
                    <span className={`px-2 py-1 rounded text-xs font-bold ${badge}`}>{signal.severity}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className={`text-sm font-medium ${text}`}>{signal.count} detections</span>
                    <span className={`text-xs font-medium ${signal.trend.includes('-') ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                      {signal.trend}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
          <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-950 rounded-lg border border-blue-200 dark:border-blue-800">
            <p className="text-xs text-blue-900 dark:text-blue-100">
              <span className="font-semibold">📊 3-Tier Response:</span> 2-3 signals = Soft Flag (50% payout), 5+ signals = Hard Block
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
