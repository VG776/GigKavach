import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Lock, AlertCircle, Phone, Fingerprint } from 'lucide-react';
import axios from 'axios';
import { API_CONFIG } from '../../utils/constants';

const WorkerLogin = () => {
  const { token } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  // Handshake data
  const [phone, setPhone] = useState('');
  const [pin, setPin] = useState('');
  const [digiId, setDigiId] = useState('');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await axios.post(`${API_CONFIG.BASE_URL}/api/v1/share-tokens/session-login/${token}`, {
        phone,
        password: pin,
        digilocker_id: digiId
      });

      if (response.data.profile) {
        localStorage.setItem('worker_session', 'active');
        localStorage.setItem('worker_token', token || '');
        localStorage.setItem('worker_profile', JSON.stringify(response.data.profile));
        navigate('/worker/status');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Handshake failed. Check your details.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gigkavach-navy text-white flex flex-col items-center justify-center px-6 py-12 relative overflow-hidden font-sans">
      {/* Background Orbs */}
      <div className="absolute top-0 right-0 w-64 h-64 bg-gigkavach-orange/10 rounded-full blur-[100px] -mr-32 -mt-32"></div>
      <div className="absolute bottom-0 left-0 w-64 h-64 bg-gigkavach-orange/5 rounded-full blur-[100px] -ml-32 -mb-32"></div>

      <div className="w-full max-w-sm relative z-10">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-24 h-24 mb-6">
            <img src="/logo.png" alt="GigKavach Logo" className="w-full h-full object-contain drop-shadow-2xl brightness-110" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight mb-2">Gigkavach Worker Portal</h1>
          <p className="text-gray-400">Secure DigiLocker Handshake</p>
        </div>

        {/* Demo Credentials Card */}
        <div className="mb-6 bg-white/5 border border-white/10 rounded-2xl p-4 text-xs">
          <p className="text-gigkavach-orange font-bold uppercase tracking-widest mb-2 text-[10px] text-center">Judge's Demo Credentials</p>
          <div className="space-y-1 text-gray-400 font-mono pl-2">
            <p><span className="text-gray-500">Phone:</span> +919100000001</p>
            <p><span className="text-gray-500">PIN:</span> 123456</p>
            <p><span className="text-gray-500">ID:</span> ABC-999</p>
          </div>
        </div>

        <div className="bg-gigkavach-surface/50 backdrop-blur-xl rounded-3xl p-8 border border-white/5 shadow-2xl">
          <form onSubmit={handleLogin} className="space-y-6">
            {error && (
              <div className="flex items-center gap-3 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                <AlertCircle className="w-5 h-5 flex-shrink-0" />
                <p>{error}</p>
              </div>
            )}

            <div className="space-y-2">
              <label className="text-xs font-bold uppercase tracking-widest text-gray-500 ml-1">Phone Number</label>
              <div className="relative">
                <Phone className="absolute left-4 top-3.5 w-5 h-5 text-gray-500" />
                <input 
                  type="tel"
                  required
                  placeholder="919100000001"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-2xl py-3.5 pl-12 pr-4 focus:outline-none focus:ring-2 focus:ring-gigkavach-orange/50 transition-all font-mono"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-bold uppercase tracking-widest text-gray-500 ml-1">Secure PIN</label>
              <div className="relative">
                <Lock className="absolute left-4 top-3.5 w-5 h-5 text-gray-500" />
                <input 
                  type="password"
                  required
                  placeholder="123456"
                  maxLength={6}
                  value={pin}
                  onChange={(e) => setPin(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-2xl py-3.5 pl-12 pr-4 focus:outline-none focus:ring-2 focus:ring-gigkavach-orange/50 transition-all font-mono"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-bold uppercase tracking-widest text-gray-500 ml-1">DigiLocker ID (Demo)</label>
              <div className="relative">
                <Fingerprint className="absolute left-4 top-3.5 w-5 h-5 text-gray-500" />
                <input 
                  type="text"
                  required
                  placeholder="ABC-999-VERIFIED"
                  value={digiId}
                  onChange={(e) => setDigiId(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-2xl py-3.5 pl-12 pr-4 focus:outline-none focus:ring-2 focus:ring-gigkavach-orange/50 transition-all font-mono"
                />
              </div>
            </div>

            <button 
              type="submit"
              disabled={loading}
              className="w-full bg-gradient-to-r from-gigkavach-orange to-orange-600 hover:from-orange-500 hover:to-orange-700 text-white font-bold py-4 rounded-2xl shadow-lg shadow-gigkavach-orange/30 transition-all transform active:scale-95 disabled:opacity-50"
            >
              {loading ? 'Authenticating...' : 'Enter Dashboard'}
            </button>
          </form>
        </div>

        
        <p className="mt-6 text-center text-gray-500 text-[11px] px-6 leading-relaxed">
          By logging in, you authorize DigiLocker to share your identity data with GigKavach for insurance verification.
        </p>
      </div>
    </div>
  );
};

export default WorkerLogin;
