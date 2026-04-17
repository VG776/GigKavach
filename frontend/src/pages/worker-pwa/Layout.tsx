import React from 'react';
import { NavLink, Outlet, Navigate } from 'react-router-dom';
import { LayoutDashboard, User, History, LogOut } from 'lucide-react';

export const WorkerLayout = () => {
  // Check for worker session in localStorage
  const session = localStorage.getItem('worker_session');
  
  React.useEffect(() => {
    document.title = "GigKavach Worker Dashboard";
  }, []);

  if (!session) {
    return <Navigate to="/worker/login" replace />;
  }

  const handleLogout = () => {
    localStorage.removeItem('worker_session');
    localStorage.removeItem('worker_profile');
    window.location.href = '/worker/login';
  };

  return (
    <div className="min-h-screen bg-gigkavach-navy text-white flex flex-col font-sans">
      {/* Mobile-first Header */}
      <header className="sticky top-0 z-50 bg-gigkavach-surface/80 backdrop-blur-lg border-b border-white/10 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <img src="/logo.png" alt="Logo" className="w-8 h-8 object-contain" />
          <span className="font-bold text-lg tracking-tight">GigKavach</span>
        </div>
        <button 
          onClick={handleLogout}
          className="p-2 text-gray-400 hover:text-white transition-colors"
        >
          <LogOut className="w-5 h-5" />
        </button>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 overflow-y-auto pb-24">
        <div className="max-w-md mx-auto px-6 py-8">
          <Outlet />
        </div>
      </main>

      {/* Persistent Bottom Navigation (PWA Style) */}
      <nav className="fixed bottom-0 left-0 right-0 z-50 bg-gigkavach-surface/90 backdrop-blur-xl border-t border-white/10 px-6 py-3">
        <div className="max-w-md mx-auto flex items-center justify-between">
          <NavLink 
            to="/worker/status" 
            className={({ isActive }) => `flex flex-col items-center gap-1 transition-colors ${isActive ? 'text-gigkavach-orange' : 'text-gray-400'}`}
          >
            <LayoutDashboard className="w-6 h-6" />
            <span className="text-[10px] font-medium uppercase tracking-wider">Status</span>
          </NavLink>
          
          <NavLink 
            to="/worker/history" 
            className={({ isActive }) => `flex flex-col items-center gap-1 transition-colors ${isActive ? 'text-gigkavach-orange' : 'text-gray-400'}`}
          >
            <History className="w-6 h-6" />
            <span className="text-[10px] font-medium uppercase tracking-wider">History</span>
          </NavLink>

          <NavLink 
            to="/worker/profile" 
            className={({ isActive }) => `flex flex-col items-center gap-1 transition-colors ${isActive ? 'text-gigkavach-orange' : 'text-gray-400'}`}
          >
            <User className="w-6 h-6" />
            <span className="text-[10px] font-medium uppercase tracking-wider">Profile</span>
          </NavLink>
        </div>
      </nav>
    </div>
  );
};

export default WorkerLayout;
