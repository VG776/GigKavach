import { useState } from 'react';
import { BarChart3, TrendingUp } from 'lucide-react';
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

const weeklyData = [
  { week: 'Wk 1', premiums: 78000, payouts: 64000, lossRatio: 82 },
  { week: 'Wk 2', premiums: 82000, payouts: 66000, lossRatio: 80.5 },
  { week: 'Wk 3', premiums: 85000, payouts: 67500, lossRatio: 79.4 },
  { week: 'Wk 4', premiums: 88000, payouts: 68000, lossRatio: 77.3 },
  { week: 'Wk 5', premiums: 90000, payouts: 68500, lossRatio: 76.1 },
  { week: 'Wk 6', premiums: 92000, payouts: 69000, lossRatio: 75 },
  { week: 'Wk 7', premiums: 87432, payouts: 62000, lossRatio: 70.9 },
  { week: 'Wk 8', premiums: 95000, payouts: 65000, lossRatio: 68.4 },
];

const coverageTierData = [
  { name: 'Shield Basic', value: 45, color: '#3B82F6' },
  { name: 'Shield Plus', value: 35, color: '#8B5CF6' },
  { name: 'Shield Pro', value: 20, color: '#FF6B35' },
];

const disruptionCauses = [
  { cause: 'Heavy Rainfall', triggers: 42, percentage: 38 },
  { cause: 'Platform Outage', triggers: 18, percentage: 16 },
  { cause: 'Severe AQI', triggers: 11, percentage: 10 },
  { cause: 'Bandh/Curfew', triggers: 7, percentage: 6 },
  { cause: 'Extreme Heat', triggers: 3, percentage: 3 },
];

// DCI Component Weights - from README
const dciComponentWeights = [
  { name: 'Rainfall', weight: 30, color: '#3B82F6', description: '>15mm/hr for 2hrs' },
  { name: 'AQI', weight: 20, color: '#F59E0B', description: '>300 (Severe) for 4hrs' },
  { name: 'Heat', weight: 20, color: '#EF4444', description: '>42°C during 10AM-4PM' },
  { name: 'Social Disruption', weight: 20, color: '#8B5CF6', description: 'Bandh, strikes, curfews' },
  { name: 'Platform Activity', weight: 10, color: '#6366F1', description: '>60% order drop' },
];

// Fraud Detection Signals - from README
const fraudSignals = [
  { signal: 'GPS vs IP Mismatch', severity: 'CRITICAL', count: 24, trend: '+8%' },
  { signal: 'Claim Burst (<2min)', severity: 'CRITICAL', count: 12, trend: '-2%' },
  { signal: 'Worker Offline All Day', severity: 'HIGH', count: 38, trend: '+15%' },
  { signal: 'DCI Threshold Gaming', severity: 'HIGH', count: 19, trend: '+5%' },
  { signal: 'Same Device Multiple IDs', severity: 'CRITICAL', count: 7, trend: 'Stable' },
  { signal: 'Registration = Event Day', severity: 'CRITICAL', count: 5, trend: '-3%' },
  { signal: 'Platform Inactive + GPS Unverified', severity: 'HIGH', count: 14, trend: '+9%' },
  { signal: 'Stationary GPS + Zero Orders', severity: 'HIGH', count: 9, trend: 'Stable' },
];

const getRiskColor = (risk) => {
  if (risk === 'HIGH') return 'bg-red-100 dark:bg-red-900 text-red-900 dark:text-red-100';
  if (risk === 'MODERATE') return 'bg-amber-100 dark:bg-amber-900 text-amber-900 dark:text-amber-100';
  return 'bg-green-100 dark:bg-green-900 text-green-900 dark:text-green-100';
};

export const Analytics = () => {
  const kpis = [
    {
      label: 'Loss Ratio',
      value: '68.4%',
      subtext: 'Payouts / Premiums',
      icon: TrendingUp,
      color: 'bg-red-100 dark:bg-red-900',
      textColor: 'text-red-900 dark:text-red-100',
    },
    {
      label: 'Premium Collected (This Week)',
      value: '₹87,432',
      subtext: 'Week over week',
      icon: TrendingUp,
      color: 'bg-blue-100 dark:bg-blue-900',
      textColor: 'text-blue-900 dark:text-blue-100',
    },
    {
      label: 'Avg Payout Per Trigger',
      value: '₹312',
      subtext: 'Across all zones',
      icon: TrendingUp,
      color: 'bg-purple-100 dark:bg-purple-900',
      textColor: 'text-purple-900 dark:text-purple-100',
    },
    {
      label: 'Renewal Rate',
      value: '89.2%',
      subtext: 'Workers retained',
      icon: TrendingUp,
      color: 'bg-green-100 dark:bg-green-900',
      textColor: 'text-green-900 dark:text-green-100',
    },
    {
      label: 'Fraud Savings',
      value: '₹34,200',
      subtext: 'This month',
      icon: TrendingUp,
      color: 'bg-orange-100 dark:bg-orange-900',
      textColor: 'text-orange-900 dark:text-orange-100',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Analytics & Insights</h1>
        <p className="text-gray-600 dark:text-gray-400 mt-1">Loss ratios, predictions, and GigKavach business metrics</p>
      </div>

      {/* KPI Bar - 5 Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        {kpis.map((kpi, idx) => {
          const Icon = kpi.icon;
          return (
            <div key={idx} className={`${kpi.color} rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700`}>
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1">
                  <p className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">{kpi.label}</p>
                  <p className={`text-2xl font-bold ${kpi.textColor}`}>{kpi.value}</p>
                </div>
                <Icon className={`w-6 h-6 ${kpi.textColor} opacity-50`} />
              </div>
              <p className="text-xs text-gray-600 dark:text-gray-400">{kpi.subtext}</p>
            </div>
          );
        })}
      </div>

      {/* Charts Section - Premium vs Payouts + Coverage Tier */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Weekly Premium vs Payouts with Loss Ratio Line */}
        <div className="lg:col-span-2 bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">Weekly Premium vs Payouts (8-Week View)</h2>
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

        {/* Right: Coverage Tier Distribution */}
        <div className="bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">Coverage Tier Distribution</h2>
          <div className="h-80 flex flex-col items-center justify-center">
            <ResponsiveContainer width="100%" height="90%">
              <PieChart>
                <Pie
                  data={coverageTierData}
                  cx="50%"
                  cy="45%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={2}
                  dataKey="value"
                  label={({ name, value }) => `${name}: ${value}%`}
                >
                  {coverageTierData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
            <p className="text-sm font-bold text-gray-700 dark:text-gray-300 text-center mt-2">1,248 Total Workers</p>
          </div>
        </div>
      </div>

      {/* DCI Engine: Component Weights */}
      <div className="bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">DCI Engine: Component Weights</h2>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          {dciComponentWeights.map((comp, idx) => (
            <div key={idx} className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-4 h-4 rounded" style={{ backgroundColor: comp.color }} />
                <p className="font-semibold text-gray-900 dark:text-white text-sm">{comp.name}</p>
              </div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white mb-2">{comp.weight}%</p>
              <p className="text-xs text-gray-600 dark:text-gray-400">{comp.description}</p>
            </div>
          ))}
        </div>
        <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-950 rounded-lg border border-blue-200 dark:border-blue-800">
          <p className="text-xs text-blue-900 dark:text-blue-100">
            <span className="font-semibold">ℹ️ DCI ranges from 0-100:</span> 0-64 (Green - No disruption), 65-84 (Amber - Moderate), 85-100 (Red - Catastrophic)
          </p>
        </div>
      </div>

      {/* Bottom Row: Top Causes + Fraud Signals */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Disruption Causes */}
        <div className="bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">Top Disruption Causes (This Month)</h2>
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
                      className="h-full bg-gradient-to-r from-gigkavach-orange to-orange-600"
                      style={{ width: `${cause.percentage * 3}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Fraud Detection Signals */}
        <div className="bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">Fraud Detection Signals</h2>
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {fraudSignals.map((signal, idx) => {
              const isCritical = signal.severity === 'CRITICAL';
              const bgColor = isCritical ? 'bg-red-50 dark:bg-red-950 border-red-200 dark:border-red-800' : 'bg-amber-50 dark:bg-amber-950 border-amber-200 dark:border-amber-800';
              const textColor = isCritical ? 'text-red-900 dark:text-red-100' : 'text-amber-900 dark:text-amber-100';
              const badgeColor = isCritical ? 'bg-red-100 text-red-900 dark:bg-red-900 dark:text-red-100' : 'bg-amber-100 text-amber-900 dark:bg-amber-900 dark:text-amber-100';
              return (
                <div key={idx} className={`border rounded-lg p-3 ${bgColor}`}>
                  <div className="flex items-start justify-between mb-2">
                    <p className={`font-semibold text-sm ${textColor}`}>{signal.signal}</p>
                    <span className={`px-2 py-1 rounded text-xs font-bold ${badgeColor}`}>
                      {signal.severity}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className={`text-sm font-medium ${textColor}`}>{signal.count} detections</span>
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
