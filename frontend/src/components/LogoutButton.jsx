/**
 * LogoutButton.jsx — Logout Component
 * ───────────────────────────────────
 * Simple logout button component.
 */

import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';

const LogoutButton = ({ className = '' }) => {
  const { logout, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const handleLogout = async () => {
    if (!isAuthenticated) {
      console.log('No active session to logout');
      navigate('/login');
      return;
    }

    setLoading(true);
    try {
      const result = await logout();
      
      if (result.success) {
        console.log('Logout successful');
        // Force navigation to login page
        navigate('/login', { replace: true });
        // Optional: Force page reload to clear any cached state
        // window.location.href = '/login';
      } else {
        console.error('Logout failed:', result.error);
        // Still navigate to login even if logout failed
        navigate('/login', { replace: true });
      }
    } catch (error) {
      console.error('Logout error:', error);
      navigate('/login', { replace: true });
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={handleLogout}
      disabled={loading}
      className={`text-sm text-red-600 hover:text-red-800 font-medium disabled:opacity-50 ${className}`}
    >
      {loading ? 'Logging out...' : 'Logout'}
    </button>
  );
};

export default LogoutButton;
