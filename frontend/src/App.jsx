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
import { JudgeConsole } from './components/demo/JudgeConsole';
import { API_CONFIG } from './utils/constants';
// PWA Worker Pages
import { WorkerProfile } from './pages/worker-pwa/Profile';
import { WorkerStatus } from './pages/worker-pwa/Status';
import { WorkerHistory } from './pages/worker-pwa/History';
// Shareable Link Pages
import { SharedLinkRoute } from './components/SharedLinkRoute';
import ProfileShare from './pages/link/ProfileShare';
import StatusShare from './pages/link/StatusShare';
import HistoryShare from './pages/link/HistoryShare';
import SharedWorkerProfile from './pages/SharedWorkerProfile';

// Protected Layout wrapper
const ProtectedLayout = ({ children }) => {
  return (
    <ProtectedRoute>
      {children}
      <JudgeConsole />
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
  const [backendReady, setBackendReady] = useState(false);
  const [backendStatus, setBackendStatus] = useState('Connecting to backend...');

  // Initialize dark mode from localStorage
  useEffect(() => {
    const darkMode = localStorage.getItem('darkMode');
    if (darkMode === 'true' || (!darkMode && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
      document.documentElement.classList.add('dark');
    }
  }, []);

  // Gate the app until backend is actually reachable.
  useEffect(() => {
    let cancelled = false;
    let retryTimerId;

    const checkBackend = async () => {
      let isBackendUp = false;
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 4000);

      try {
        const response = await fetch(`${API_CONFIG.BASE_URL}/api/v1/health/`, {
          method: 'GET',
          signal: controller.signal,
          cache: 'no-store',
        });

        if (response.ok) {
          isBackendUp = true;
          if (!cancelled) {
            setBackendReady(true);
            setBackendStatus('Backend is ready.');
          }
        } else if (!cancelled) {
          setBackendStatus(`Waiting for backend... (status ${response.status})`);
        }
      } catch {
        if (!cancelled) {
          setBackendStatus('Waiting for backend service to start...');
        }
      } finally {
        clearTimeout(timeoutId);
        if (!cancelled && !isBackendUp) {
          retryTimerId = setTimeout(checkBackend, 2000);
        }
      }
    };

    checkBackend();

    return () => {
      cancelled = true;
      if (retryTimerId) {
        clearTimeout(retryTimerId);
      }
    };
  }, []);

  if (!backendReady) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gigkavach-navy via-gigkavach-navy-light to-gigkavach-navy text-white px-6">
        <div className="text-center max-w-md">
          <div className="mx-auto mb-6 h-12 w-12 rounded-full border-4 border-white/25 border-t-gigkavach-orange animate-spin" />
          <h1 className="text-2xl font-bold tracking-tight mb-2">Starting GigKavach</h1>
          <p className="text-gray-300">{backendStatus}</p>
          <p className="text-gray-400 text-sm mt-3">The app will open automatically once the backend responds.</p>
        </div>
      </div>
    );
  }

  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/login" element={<Login />} />
      
      {/* Shared Worker Profile (via share token) */}
      <Route path="/share/worker/:token" element={<SharedWorkerProfile />} />
      
      {/* Shareable Link Routes (Token-authenticated) */}
      <Route path="/link/:shareToken/profile" element={<ProfileShare />} />
      <Route path="/link/:shareToken/status" element={<StatusShare />} />
      <Route path="/link/:shareToken/history" element={<HistoryShare />} />
      
      {/* PWA Worker Routes */}
      <Route
        path="/worker/profile"
        element={
          <ProtectedRoute>
            <WorkerProfile />
          </ProtectedRoute>
        }
      />
      <Route
        path="/worker/status"
        element={
          <ProtectedRoute>
            <WorkerStatus />
          </ProtectedRoute>
        }
      />
      <Route
        path="/worker/history"
        element={
          <ProtectedRoute>
            <WorkerHistory />
          </ProtectedRoute>
        }
      />
      
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
