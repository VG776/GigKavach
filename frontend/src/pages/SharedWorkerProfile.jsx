/**
 * SharedWorkerProfile.jsx
 * Public profile page accessed via share token: /share/worker/:token
 * Shows LIMITED public worker data without authentication
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Loader, AlertCircle, CheckCircle, Briefcase, Zap, TrendingUp } from 'lucide-react';
import { getSharedWorkerProfile } from '../utils/shareTokenUtils';

export const SharedWorkerProfile = () => {
  const { token } = useParams();
  const navigate = useNavigate();
  
  const [worker, setWorker] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expired, setExpired] = useState(false);

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        if (!token) {
          setError('No share token provided');
          return;
        }

        console.log('[PROFILE] Loading shared worker profile...');
        setLoading(true);
        
        const profile = await getSharedWorkerProfile(token);
        setWorker(profile);
        
      } catch (err) {
        console.error('[PROFILE] Error loading profile:', err);
        
        if (err.message.includes('expired')) {
          setExpired(true);
          setError('This share link has expired');
        } else if (err.message.includes('404')) {
          setError('Worker profile not found');
        } else {
          setError(err.message || 'Failed to load profile');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchProfile();
  }, [token]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gigkavach-blue to-purple-900 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader className="w-12 h-12 text-white animate-spin" />
          <p className="text-white text-lg">Loading worker profile...</p>
        </div>
      </div>
    );
  }

  if (error || expired) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gigkavach-blue to-purple-900 flex items-center justify-center p-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full p-6">
          <div className="flex items-center gap-3 mb-4">
            <AlertCircle className="w-6 h-6 text-red-500" />
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">
              {expired ? 'Link Expired' : 'Profile Not Found'}
            </h1>
          </div>
          
          <p className="text-gray-600 dark:text-gray-300 mb-6">
            {error || 'This profile is no longer available.'}
          </p>
          
          <button
            onClick={() => navigate('/')}
            className="w-full px-4 py-2 bg-gigkavach-blue text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
          >
            Go Home
          </button>
        </div>
      </div>
    );
  }

  if (!worker) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gigkavach-blue to-purple-900 flex items-center justify-center">
        <p className="text-white text-lg">No profile data available</p>
      </div>
    );
  }

  // Helper function to get badge styles
  const getBadgeStyle = (type) => {
    const styles = {
      platform: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
      shift: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200',
      plan: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
      score: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    };
    return styles[type] || 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gigkavach-blue via-purple-900 to-black">
      {/* Header */}
      <div className="bg-gradient-to-r from-gigkavach-blue/10 to-purple-900/10 border-b border-purple-500/20">
        <div className="max-w-3xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <h1 className="text-3xl font-bold text-white">Worker Profile</h1>
            <CheckCircle className="w-8 h-8 text-green-400" />
          </div>
          <p className="text-purple-200 mt-2">Shared profile - Limited public information</p>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-3xl mx-auto px-4 py-12 sm:px-6 lg:px-8">
        {/* Profile Card */}
        <div className="bg-gray-900/80 backdrop-blur border border-purple-500/30 rounded-lg shadow-xl p-8 mb-6">
          {/* Name */}
          <div className="mb-8">
            <h2 className="text-4xl font-bold text-white mb-2">{worker.name}</h2>
            <p className="text-purple-300">GigKavach Worker Profile</p>
          </div>

          {/* Badges Row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            {/* Platform */}
            <div className="bg-gray-800/50 rounded-lg p-4 border border-purple-500/20">
              <p className="text-sm text-gray-400 mb-2 flex items-center gap-2">
                <Briefcase className="w-4 h-4" />
                Platform
              </p>
              <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${getBadgeStyle('platform')}`}>
                {worker.platform || '—'}
              </span>
            </div>

            {/* Shift */}
            <div className="bg-gray-800/50 rounded-lg p-4 border border-purple-500/20">
              <p className="text-sm text-gray-400 mb-2">Shift</p>
              <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${getBadgeStyle('shift')}`}>
                {worker.shift || '—'}
              </span>
            </div>

            {/* Plan */}
            <div className="bg-gray-800/50 rounded-lg p-4 border border-purple-500/20">
              <p className="text-sm text-gray-400 mb-2">Plan</p>
              <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${getBadgeStyle('plan')}`}>
                {worker.plan || '—'}
              </span>
            </div>
          </div>

          {/* Scores */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Gig Score */}
            <div className="bg-gradient-to-br from-blue-500/10 to-blue-600/10 rounded-lg p-6 border border-blue-500/30">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm text-gray-400 flex items-center gap-2">
                  <Zap className="w-4 h-4" />
                  Gig Score
                </p>
                <span className="text-xs px-2 py-1 rounded bg-blue-500/20 text-blue-300">Rating</span>
              </div>
              <p className="text-4xl font-bold text-blue-400">
                {worker.gig_score || 0}
                <span className="text-lg text-gray-500">/100</span>
              </p>
            </div>

            {/* Portfolio Score */}
            <div className="bg-gradient-to-br from-purple-500/10 to-purple-600/10 rounded-lg p-6 border border-purple-500/30">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm text-gray-400 flex items-center gap-2">
                  <TrendingUp className="w-4 h-4" />
                  Portfolio Score
                </p>
                <span className="text-xs px-2 py-1 rounded bg-purple-500/20 text-purple-300">Rating</span>
              </div>
              <p className="text-4xl font-bold text-purple-400">
                {worker.portfolio_score || 0}
                <span className="text-lg text-gray-500">/100</span>
              </p>
            </div>
          </div>
        </div>

        {/* Info Banner */}
        <div className="bg-gradient-to-r from-purple-500/10 to-blue-500/10 border border-purple-500/20 rounded-lg p-4 text-center">
          <p className="text-sm text-gray-400">
            This is a limited public profile shared via GigKavach. 
            <span className="text-purple-300"> Contact the worker directly for more information.</span>
          </p>
        </div>
      </div>
    </div>
  );
};

export default SharedWorkerProfile;
