import { useState } from 'react';
import { Users, Zap, IndianRupee, ShieldAlert, TrendingUp, TrendingDown, Clock, CheckCircle2, Clock3, AlertCircle } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, BarChart, Bar, Cell } from 'recharts';

// DCI Live Monitor Data - last 12 time points (5-minute intervals)
const dciLiveData = [
  { time: '2:00', dci: 48, zone: 'HSR Layout', rainfall: 'LOW' },
  { time: '2:05', dci: 52, zone: 'Indiranagar', rainfall: 'LOW' },
  { time: '2:10', dci: 58, zone: 'Koramangala', rainfall: 'MODERATE' },
  { time: '2:15', dci: 65, zone: 'Koramangala', rainfall: 'HIGH' },
  { time: '2:20', dci: 72, zone: 'Koramangala', rainfall: 'HIGH' },
  { time: '2:25', dci: 68, zone: 'Marathahalli', rainfall: 'MODERATE' },
  { time: '2:30', dci: 75, zone: 'Whitefield', rainfall: 'MODERATE' },
  { time: '2:35', dci: 82, zone: 'Koramangala', rainfall: 'HIGH' },
  { time: '2:40', dci: 78, zone: 'Koramangala', rainfall: 'HIGH' },
  { time: '2:45', dci: 71, zone: 'Electronic City', rainfall: 'LOW' },
  { time: '2:50', dci: 64, zone: 'HSR Layout', rainfall: 'LOW' },
  { time: '2:55', dci: 58, zone: 'Indiranagar', rainfall: 'LOW' },
];

// Sparkline data for stat cards (7 days)
const sparklineData7Days = [42, 48, 45, 52, 58, 55, 62];
const dciTriggersData = [8, 12, 10, 18, 22, 19, 34];
const payoutsData = [145000, 168000, 152000, 198000, 220000, 198000, 245680];
const fraudAlertsData = [4, 6, 5, 8, 10, 11, 12];

// Active Zones with Alerts
const activeZones = [
  {
    id: 1,
    name: 'Koramangala 5th Block',
    dci: 82,
    trigger: 'Heavy Rainfall · 23mm/hr',
    workersAffected: 48,
    status: 'critical'
  },
  {
    id: 2,
    name: 'Whitefield Tech Park',
    dci: 75,
    trigger: 'Rainfall + High Humidity',
    workersAffected: 35,
    status: 'high'
  },
  {
    id: 3,
    name: 'Marathahalli',
    dci: 68,
    trigger: 'Moderate Rainfall',
    workersAffected: 28,
    status: 'moderate'
  },
];

// Recent Payouts
const recentPayouts = [
  {
    id: 1,
    initials: 'RK',
    name: 'Rajesh Kumar',
    tier: 'Shield Pro',
    amount: 420,
    status: 'sent',
    timestamp: '2 min ago'
  },
  {
    id: 2,
    initials: 'SR',
    name: 'Sneha Reddy',
    tier: 'Shield Plus',
    amount: 315,
    status: 'processing',
    timestamp: '5 min ago'
  },
  {
    id: 3,
    initials: 'AP',
    name: 'Amit Patel',
    tier: 'Shield Basic',
    amount: 210,
    status: 'sent',
    timestamp: '12 min ago'
  },
];

// Recent Activity Feed
const activityFeed = [
  {
    id: 1,
    type: 'trigger',
    description: 'DCI triggered in Koramangala · 48 workers notified',
    timestamp: '2 min ago',
    icon: Zap,
  },
  {
    id: 2,
    type: 'payout',
    description: 'Payout of ₹420 sent to Rajesh Kumar',
    timestamp: '5 min ago',
    icon: IndianRupee,
  },
  {
    id: 3,
    type: 'fraud',
    description: 'Fraud alert flagged · GPS vs IP mismatch in HSR Layout',
    timestamp: '8 min ago',
    icon: ShieldAlert,
  },
  {
    id: 4,
    type: 'trigger',
    description: 'Whitefield zone entered MODERATE disruption',
    timestamp: '18 min ago',
    icon: Zap,
  },
];

export const Dashboard = () => {
  const statCards = [
    {
      label: 'Active Workers This Week',
      value: 1248,
      change: +12,
      icon: Users,
      color: 'blue',
      subtitle: 'Enrolled in Shield Basic/Plus/Pro',
      data: sparklineData7Days,
    },
    {
      label: 'DCI Triggers Today',
      value: 34,
      change: +8,
      icon: Zap,
      color: 'orange',
      subtitle: 'Disruption events detected',
      data: dciTriggersData,
    },
    {
      label: 'Payouts Processed',
      value: 245680,
      change: +15,
      icon: IndianRupee,
      color: 'green',
      subtitle: 'Auto-disbursed today',
      data: payoutsData,
    },
    {
      label: 'Fraud Alerts Active',
      value: 12,
      change: -5,
      icon: ShieldAlert,
      color: 'red',
      subtitle: 'Pending review · 2 High Risk',
      data: fraudAlertsData,
    },
  ];

  const getCardBgColor = (color) => {
    const colors = {
      blue: 'bg-blue-50 dark:bg-blue-950',
      orange: 'bg-orange-50 dark:bg-orange-950',
      green: 'bg-green-50 dark:bg-green-950',
      red: 'bg-red-50 dark:bg-red-950',
    };
    return colors[color];
  };

  const getIconColor = (color) => {
    const colors = {
      blue: 'text-blue-600 dark:text-blue-400',
      orange: 'text-orange-600 dark:text-orange-400',
      green: 'text-green-600 dark:text-green-400',
      red: 'text-red-600 dark:text-red-400',
    };
    return colors[color];
  };

  const getChangeColor = (change) => {
    const isPositive = change >= 0;
    return isPositive ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400';
  };

  const getDCIColor = (dci) => {
    if (dci >= 85) return 'bg-red-100 dark:bg-red-900 text-red-900 dark:text-red-100';
    if (dci >= 65) return 'bg-orange-100 dark:bg-orange-900 text-orange-900 dark:text-orange-100';
    if (dci >= 45) return 'bg-amber-100 dark:bg-amber-900 text-amber-900 dark:text-amber-100';
    return 'bg-green-100 dark:bg-green-900 text-green-900 dark:text-green-100';
  };

  const getDCIZoneColor = (dci) => {
    if (dci >= 85) return 'border-l-4 border-l-red-600';
    if (dci >= 65) return 'border-l-4 border-l-orange-500';
    if (dci >= 45) return 'border-l-4 border-l-amber-500';
    return 'border-l-4 border-l-green-600';
  };

  const getActivityColor = (type) => {
    const colors = {
      trigger: 'border-l-orange-500 bg-orange-50/30 dark:bg-orange-950/30',
      payout: 'border-l-green-500 bg-green-50/30 dark:bg-green-950/30',
      fraud: 'border-l-red-500 bg-red-50/30 dark:bg-red-950/30',
    };
    return colors[type];
  };

  const getActivityIconColor = (type) => {
    const colors = {
      trigger: '#FF6B35',
      payout: '#22C55E',
      fraud: '#EF4444',
    };
    return colors[type];
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">GigKavach Operations Hub</h1>
        <p className="text-gray-600 dark:text-gray-400 mt-1">Real-time worker protection and disruption monitoring</p>
      </div>

      {/* STAT CARDS - 4 Cards with Sparklines */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((card, idx) => {
          const Icon = card.icon;
          const isPositive = card.change >= 0;
          return (
            <div
              key={idx}
              className={`${getCardBgColor(card.color)} rounded-lg p-5 border border-gray-200 dark:border-gray-700 shadow-sm`}
            >
              {/* Header: Icon + Change Badge */}
              <div className="flex items-start justify-between mb-4">
                <Icon className={`w-6 h-6 ${getIconColor(card.color)}`} />
                <span className={`flex items-center gap-1 text-xs font-bold ${getChangeColor(card.change)}`}>
                  {isPositive ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                  {Math.abs(card.change)}%
                </span>
              </div>

              {/* Value in JetBrains Mono */}
              <p className="text-3xl font-black text-gray-900 dark:text-white mb-1 font-mono">
                {card.value > 1000 && card.color !== 'orange' && card.color !== 'red'
                  ? card.value.toLocaleString()
                  : card.value}
                {card.color === 'green' && ''}
              </p>

              {/* Label */}
              <p className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-3">{card.label}</p>

              {/* Mini Sparkline (7 bars) */}
              <div className="h-10 mb-2">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={card.data.map((v, i) => ({ value: v, index: i }))}>
                    <Bar dataKey="value" radius={[2, 2, 0, 0]}>
                      {card.data.map((_, i) => (
                        <Cell
                          key={`cell-${i}`}
                          fill={
                            card.color === 'blue'
                              ? '#3B82F6'
                              : card.color === 'orange'
                                ? '#FF6B35'
                                : card.color === 'green'
                                  ? '#22C55E'
                                  : '#EF4444'
                          }
                          opacity={i === card.data.length - 1 ? 1 : 0.5}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Subtitle */}
              <p className="text-xs text-gray-600 dark:text-gray-400">{card.subtitle}</p>
            </div>
          );
        })}
      </div>

      {/* MAIN CONTENT: DCI Monitor (60%) + Right Sidebar (40%) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* DCI LIVE MONITOR - Left 60% */}
        <div className="lg:col-span-2 bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
          {/* Live Badge */}
          <div className="flex items-center gap-3 mb-6">
            <div className="flex items-center gap-2 bg-red-50 dark:bg-red-950 px-3 py-2 rounded-full border border-red-200 dark:border-red-800">
              <div className="w-2 h-2 bg-red-600 rounded-full animate-pulse" />
              <span className="text-xs font-bold text-red-600 dark:text-red-400 uppercase">Live</span>
            </div>
            <span className="text-sm font-semibold text-gray-900 dark:text-white">3 Zones Above Trigger Threshold</span>
          </div>

          {/* Area Chart */}
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={dciLiveData}>
                <defs>
                  <linearGradient id="colorDci" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#FF6B35" stopOpacity={0.8} />
                    <stop offset="95%" stopColor="#FF6B35" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb"/>
                <XAxis dataKey="time" stroke="#9CA3AF" tick={{ fontSize: 12 }} />
                <YAxis domain={[0, 100]} stroke="#9CA3AF" label={{ value: 'DCI Score', angle: -90, position: 'insideLeft' }} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '8px', color: '#fff' }}
                  formatter={(value, name) => {
                    if (name === 'dci') return [`${value}`, 'DCI Score'];
                    return [value, name];
                  }}
                  labelFormatter={(label) => `Time: ${label}`}
                />
                <ReferenceLine y={65} stroke="#FF6B35" strokeDasharray="5 5" label={{ value: 'Trigger Threshold (65)', position: 'insideRight', offset: -10, fill: '#FF6B35', fontSize: 11 }} />
                <ReferenceLine y={85} stroke="#EF4444" strokeDasharray="5 5" label={{ value: 'Catastrophic (85)', position: 'insideRight', offset: -25, fill: '#EF4444', fontSize: 11 }} />
                <Area type="monotone" dataKey="dci" stroke="#FF6B35" fillOpacity={1} fill="url(#colorDci)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* RIGHT SIDEBAR - 40% */}
        <div className="flex flex-col gap-6">
          {/* ACTIVE ZONE ALERTS */}
          <div className="bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 p-5 shadow-sm">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Active Zone Alerts</h3>
            <div className="space-y-3">
              {activeZones.map((zone) => (
                <div key={zone.id} className={`${getDCIZoneColor(zone.dci)} bg-gray-50 dark:bg-gray-800 p-3 rounded-lg`}>
                  <div className="flex items-start justify-between mb-2">
                    <p className="font-semibold text-gray-900 dark:text-white text-sm">{zone.name}</p>
                    <span className={`text-sm font-bold px-2 py-1 rounded ${getDCIColor(zone.dci)}`}>
                      {zone.dci}
                    </span>
                  </div>
                  <p className="text-xs text-gray-600 dark:text-gray-400 mb-2">{zone.trigger}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-500 mb-2">{zone.workersAffected} workers affected</p>
                  {/* Mini Progress Bar */}
                  <div className="h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${
                        zone.dci >= 85
                          ? 'bg-red-600'
                          : zone.dci >= 65
                            ? 'bg-orange-500'
                            : 'bg-amber-500'
                      }`}
                      style={{ width: `${Math.min((zone.dci / 100) * 100, 100)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* PAYOUT PIPELINE */}
          <div className="bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 p-5 shadow-sm">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Payout Pipeline</h3>
            <div className="space-y-3">
              {recentPayouts.map((payout) => (
                <div key={payout.id} className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                  {/* Avatar */}
                  <div className="w-8 h-8 rounded-full bg-gigkavach-orange flex items-center justify-center text-white font-bold text-xs">
                    {payout.initials}
                  </div>
                  {/* Details */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{payout.name}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">{payout.tier}</p>
                  </div>
                  {/* Amount + Status */}
                  <div className="text-right">
                    <p className="text-sm font-bold text-green-600 dark:text-green-400">₹{payout.amount}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 flex items-center justify-end gap-1">
                      {payout.status === 'sent' ? (
                        <>
                          <CheckCircle2 className="w-3 h-3 text-green-600" /> Sent
                        </>
                      ) : (
                        <>
                          <Clock3 className="w-3 h-3 text-amber-600" /> Processing
                        </>
                      )}
                    </p>
                  </div>
                </div>
              ))}
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-3 text-center">Timestamp varies</p>
          </div>
        </div>
      </div>

      {/* RECENT ACTIVITY FEED - Bottom */}
      <div className="bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Recent Activity</h2>
        <div className="space-y-3">
          {activityFeed.map((activity) => {
            const Icon = activity.icon;
            return (
              <div
                key={activity.id}
                className={`border-l-4 p-3 rounded-lg ${getActivityColor(activity.type)} flex items-start gap-3`}
              >
                {/* Timeline Icon */}
                <div className="pt-1">
                  <Icon className="w-4 h-4" style={{ color: getActivityIconColor(activity.type) }} />
                </div>
                {/* Content */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-900 dark:text-white font-medium">{activity.description}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {activity.timestamp}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

