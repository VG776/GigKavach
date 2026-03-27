import { useState, useEffect } from 'react';
import { Layout } from './components/layout/Layout';
import { Dashboard } from './pages/Dashboard';
import { Workers } from './pages/Workers';
import { Payouts } from './pages/Payouts';
import { Fraud } from './pages/Fraud';
import { Settings } from './pages/Settings';
import { Heatmap } from './pages/Heatmap';
import { Analytics } from './pages/Analytics';

export default function App() {
  const [activePage, setActivePage] = useState('dashboard');

  // Initialize dark mode from localStorage
  useEffect(() => {
    const darkMode = localStorage.getItem('darkMode');
    if (darkMode === 'true' || (!darkMode && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
      document.documentElement.classList.add('dark');
    }
  }, []);

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
}
