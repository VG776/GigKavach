import { useState, useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/layout/Layout';
import { Dashboard } from './pages/Dashboard';
import { Workers } from './pages/Workers';
import { Payouts } from './pages/Payouts';
import { Fraud } from './pages/Fraud';
import { Settings } from './pages/Settings';
import { Heatmap } from './pages/Heatmap';
import { Analytics } from './pages/Analytics';
import Login from './pages/Login';
import ProtectedRoute from './components/ProtectedRoute';
import { useBackendKeepAlive } from './services/keepAlive';

// Protected Layout wrapper
const ProtectedLayout = ({ children }) => {
  return (
    <ProtectedRoute>
      {children}
    </ProtectedRoute>
  );
};

// Dashboard Layout wrapper with navigation
const DashboardLayout = () => {
  const [activePage, setActivePage] = useState('dashboard');

  const renderPage = () => {
    switch (activePage) {
      case 'dashboard':
        return <Dashboard />;
      case 'heatmap':
        return <Heatmap />;
      case 'workers':
        return <Workers />;
      case 'payouts':
        return <Payouts />;
      case 'analytics':
        return <Analytics />;
      case 'fraud':
        return <Fraud />;
      case 'settings':
        return <Settings />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <Layout activePage={activePage} onNavigate={setActivePage}>
      {renderPage()}
    </Layout>
  );
};

export default function App() {
  // Keep backend awake on Render (prevents free tier spin-down)
  useBackendKeepAlive();

  // Initialize dark mode from localStorage
  useEffect(() => {
    const darkMode = localStorage.getItem('darkMode');
    if (darkMode === 'true' || (!darkMode && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
      document.documentElement.classList.add('dark');
    }
  }, []);

  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/login" element={<Login />} />
      
      {/* Protected Routes */}
      <Route
        path="/*"
        element={
          <ProtectedLayout>
            <DashboardLayout />
          </ProtectedLayout>
        }
      />
      
      {/* Redirect root to login */}
      <Route path="/" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
