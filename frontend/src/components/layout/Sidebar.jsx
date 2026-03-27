import { useState, useEffect } from 'react';
import { LayoutDashboard, Users, Wallet, ShieldAlert, Settings, X, Map, BarChart3 } from 'lucide-react';

const navigationItems = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'heatmap', label: 'Heatmap', icon: Map },
  { id: 'workers', label: 'Workers', icon: Users },
  { id: 'payouts', label: 'Payouts', icon: Wallet },
  { id: 'analytics', label: 'Analytics', icon: BarChart3 },
  { id: 'fraud', label: 'Fraud', icon: ShieldAlert },
  { id: 'settings', label: 'Settings', icon: Settings },
];

export const Sidebar = ({ activePage, onNavigate, isMobileOpen, onMobileClose }) => {
  return (
    <>
      {/* Mobile Overlay */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={onMobileClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
        sidebar fixed lg:sticky top-0 left-0 h-screen
        w-64 flex flex-col z-50 transition-transform duration-300
        bg-white dark:bg-gigkavach-navy border-r border-gray-200 dark:border-gray-800
        ${isMobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}
      >
        {/* Logo Header */}
        <div className="p-6 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 rounded-lg bg-gigkavach-orange flex items-center justify-center text-white font-bold text-sm">
              GK
            </div>
            <div className="hidden sm:block">
              <p className="text-sm font-bold text-gray-900 dark:text-white">GigKavach</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">Operations</p>
            </div>
          </div>
          <button
            onClick={onMobileClose}
            className="lg:hidden p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded text-gray-700 dark:text-gray-300"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="sidebar-nav flex-1 px-3 py-4">
          <ul className="space-y-2">
            {navigationItems.map((item) => {
              const Icon = item.icon;
              const isActive = activePage === item.id;

              return (
                <li key={item.id}>
                  <button
                    onClick={() => {
                      onNavigate(item.id);
                      onMobileClose();
                    }}
                    className={`sidebar-nav-item w-full flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all duration-200 ${
                      isActive
                        ? 'bg-gigkavach-orange text-white shadow-md'
                        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                    }`}
                  >
                    <Icon className="w-5 h-5 flex-shrink-0" />
                    <span className="font-medium text-sm">{item.label}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* User Info */}
        <div className="p-4 border-t border-gray-200 dark:border-gray-800">
          <div className="flex items-center gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
            <div className="w-10 h-10 rounded-full bg-gigkavach-orange flex items-center justify-center text-white font-bold text-sm flex-shrink-0">
              A
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-gray-900 dark:text-white font-medium truncate">Admin</p>
              <p className="text-xs text-gray-500 dark:text-gray-400 truncate">admin@gigkavach.com</p>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};
