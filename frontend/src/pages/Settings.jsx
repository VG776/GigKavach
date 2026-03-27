import { useState } from 'react';
import { Settings as SettingsIcon, Bell, Lock, Volume2, Zap } from 'lucide-react';
import { Button } from '../components/common/Button';

export const Settings = () => {
  const [formData, setFormData] = useState({
    companyName: 'GigKavach',
    timezone: 'IST',
    payoutDelay: '24',
    fraudThreshold: '3',
    dciAlertThreshold: '75',
    enableNotifications: true,
    enableSimulation: true,
    enableFraudAlerts: true,
  });

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const handleSave = () => {
    console.log('Settings saved:', formData);
    alert('Settings saved successfully!');
  };

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Settings</h1>
        <p className="text-gray-600 dark:text-gray-400 mt-1">Manage system configuration and preferences</p>
      </div>

      {/* General Settings */}
      <div className="bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-6 flex items-center gap-2">
          <SettingsIcon className="w-5 h-5" />
          General Settings
        </h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Company Name</label>
            <input
              type="text"
              name="companyName"
              value={formData.companyName}
              onChange={handleChange}
              className="w-full px-4 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-gigkavach-orange"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Timezone</label>
              <select
                name="timezone"
                value={formData.timezone}
                onChange={handleChange}
                className="w-full px-4 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-gigkavach-orange"
              >
                <option>IST</option>
                <option>PST</option>
                <option>EST</option>
                <option>GMT</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Default Payout Delay (Hours)</label>
              <input
                type="number"
                name="payoutDelay"
                value={formData.payoutDelay}
                onChange={handleChange}
                className="w-full px-4 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-gigkavach-orange"
              />
            </div>
          </div>
        </div>
      </div>

      {/* DCI Configuration */}
      <div className="bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-6 flex items-center gap-2">
          <Zap className="w-5 h-5 text-amber-500" />
          DCI Engine Configuration
        </h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              DCI Alert Threshold (value above which alerts trigger)
            </label>
            <div className="flex items-center gap-4">
              <input
                type="range"
                name="dciAlertThreshold"
                min="0"
                max="100"
                value={formData.dciAlertThreshold}
                onChange={handleChange}
                className="flex-1 accent-gigkavach-orange"
              />
              <span className="px-3 py-2 bg-gray-100 dark:bg-gray-800 rounded text-sm font-semibold text-gray-900 dark:text-white min-w-[60px] text-right">
                {formData.dciAlertThreshold}
              </span>
            </div>
          </div>

          <div className="p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
            <p className="text-sm text-amber-900 dark:text-amber-100">
              When DCI for a zone exceeds {formData.dciAlertThreshold}, eligible workers receive automatic parametric payouts without claim.
            </p>
          </div>
        </div>
      </div>

      {/* Fraud Detection */}
      <div className="bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-6 flex items-center gap-2">
          <Lock className="w-5 h-5 text-red-500" />
          Fraud Detection Thresholds
        </h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Fraud Score Threshold for Path B (Escrow Hold)
            </label>
            <div className="flex items-center gap-4">
              <input
                type="range"
                name="fraudThreshold"
                min="0"
                max="6"
                value={formData.fraudThreshold}
                onChange={handleChange}
                className="flex-1 accent-gigkavach-orange"
              />
              <span className="px-3 py-2 bg-gray-100 dark:bg-gray-800 rounded text-sm font-semibold text-gray-900 dark:text-white min-w-[60px] text-right">
                {formData.fraudThreshold}/6
              </span>
            </div>
          </div>

          <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
            <p className="text-sm text-blue-900 dark:text-blue-100">
              Claims with fraud score ≥ {formData.fraudThreshold} are placed in Path B (Soft Flag) with 50% escrowed pending verification.
            </p>
          </div>
        </div>
      </div>

      {/* Notifications & Alerts */}
      <div className="bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-6 flex items-center gap-2">
          <Bell className="w-5 h-5 text-blue-500" />
          Notifications & Alerts
        </h2>

        <div className="space-y-3">
          <label className="flex items-center gap-3 cursor-pointer p-3 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-lg transition-colors">
            <input
              type="checkbox"
              name="enableNotifications"
              checked={formData.enableNotifications}
              onChange={handleChange}
              className="w-5 h-5 accent-gigkavach-orange rounded"
            />
            <span className="text-gray-700 dark:text-gray-300">Enable system notifications</span>
          </label>

          <label className="flex items-center gap-3 cursor-pointer p-3 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-lg transition-colors">
            <input
              type="checkbox"
              name="enableFraudAlerts"
              checked={formData.enableFraudAlerts}
              onChange={handleChange}
              className="w-5 h-5 accent-gigkavach-orange rounded"
            />
            <span className="text-gray-700 dark:text-gray-300">Fraud alert notifications</span>
          </label>

          <label className="flex items-center gap-3 cursor-pointer p-3 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-lg transition-colors">
            <input
              type="checkbox"
              name="enableSimulation"
              checked={formData.enableSimulation}
              onChange={handleChange}
              className="w-5 h-5 accent-gigkavach-orange rounded"
            />
            <span className="text-gray-700 dark:text-gray-300">Allow payout simulation triggers</span>
          </label>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3 justify-between">
        <Button variant="ghost" onClick={() => console.log('Reset')}>Reset to Defaults</Button>
        <Button variant="primary" onClick={handleSave}>Save Settings</Button>
      </div>
    </div>
  );
};
