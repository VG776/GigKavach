/**
 * AuthDebug.jsx — Authentication Debug Component
 * ───────────────────────────────────────────
 * Helps debug authentication state issues.
 * Add this to any page to see current auth state.
 */

import React from 'react';
import { useAuth } from '../context/AuthContext';

const AuthDebug = () => {
  const { user, userProfile, session, isAuthenticated, loading } = useAuth();

  // Only show in development
  if (process.env.NODE_ENV === 'production') {
    return null;
  }

  return (
    <div className="fixed bottom-4 right-4 p-4 bg-gray-900 text-white rounded-lg shadow-lg max-w-sm z-50">
      <h4 className="font-bold mb-2">Auth Debug</h4>
      <div className="text-xs space-y-1">
        <p><span className="text-gray-400">Loading:</span> {loading ? 'true' : 'false'}</p>
        <p><span className="text-gray-400">Authenticated:</span> {isAuthenticated ? '✅ true' : '❌ false'}</p>
        <p><span className="text-gray-400">User:</span> {user ? user.email : 'null'}</p>
        <p><span className="text-gray-400">Profile:</span> {userProfile ? 'loaded' : 'null'}</p>
        <p><span className="text-gray-400">Session:</span> {session ? 'active' : 'null'}</p>
      </div>
    </div>
  );
};

export default AuthDebug;
