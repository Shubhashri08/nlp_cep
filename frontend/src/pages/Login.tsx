import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { UserRole } from '../types';
import { Building2, Shield, Lock, ArrowRight, UserCheck } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const Login: React.FC = () => {
  const { login, quickLoginAs } = useAuth();
  const [email, setEmail] = useState<string>('admin@municipal.gov.in');
  const [password, setPassword] = useState<string>('Admin@2026#DSS');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const navigate = useNavigate();

  const handleManualLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      setError(null);
      await login(email, password);
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickRole = async (role: UserRole) => {
    try {
      setLoading(true);
      setError(null);
      await quickLoginAs(role);
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Quick login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-center items-center p-4 selection:bg-brand-500 selection:text-white">
      <div className="w-full max-w-md space-y-6">
        {/* Logo & Title */}
        <div className="text-center space-y-2">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-brand-600 to-emerald-500 flex items-center justify-center mx-auto shadow-xl shadow-brand-500/25">
            <Building2 className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-extrabold text-slate-100 tracking-tight">
            Urban Planning Decision Support
          </h1>
          <p className="text-xs text-slate-400">
            Municipal AI, NLP, PostGIS & Machine Learning Decision Platform
          </p>
        </div>

        {/* Quick Role Select Box */}
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-300">ONE-CLICK MUNICIPAL ROLE LOGIN:</span>
            <span className="text-[10px] text-brand-400 font-mono">JWT RBAC</span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <button
              onClick={() => handleQuickRole('ADMIN')}
              disabled={loading}
              className="p-2.5 bg-slate-950 hover:bg-slate-800 border border-slate-800 rounded-lg text-left transition"
            >
              <div className="font-bold text-slate-200">Admin Officer</div>
              <div className="text-[10px] text-slate-500">Full System Access</div>
            </button>
            <button
              onClick={() => handleQuickRole('PLANNER')}
              disabled={loading}
              className="p-2.5 bg-slate-950 hover:bg-slate-800 border border-slate-800 rounded-lg text-left transition"
            >
              <div className="font-bold text-slate-200">Town Planner</div>
              <div className="text-[10px] text-slate-500">Scenario & Interventions</div>
            </button>
            <button
              onClick={() => handleQuickRole('ANALYST')}
              disabled={loading}
              className="p-2.5 bg-slate-950 hover:bg-slate-800 border border-slate-800 rounded-lg text-left transition"
            >
              <div className="font-bold text-slate-200">GIS ML Analyst</div>
              <div className="text-[10px] text-slate-500">Models & Analytics</div>
            </button>
            <button
              onClick={() => handleQuickRole('VIEWER')}
              disabled={loading}
              className="p-2.5 bg-slate-950 hover:bg-slate-800 border border-slate-800 rounded-lg text-left transition"
            >
              <div className="font-bold text-slate-200">Public Committee</div>
              <div className="text-[10px] text-slate-500">Read-Only Views</div>
            </button>
          </div>
        </div>

        {/* Manual Login Form */}
        <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl space-y-4 shadow-xl">
          <h2 className="text-sm font-bold text-slate-200">Municipal Credentials Sign In</h2>

          {error && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-lg text-xs">
              {error}
            </div>
          )}

          <form onSubmit={handleManualLogin} className="space-y-4 text-xs">
            <div>
              <label className="text-slate-400 font-semibold">MUNICIPAL EMAIL</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full mt-1 bg-slate-950 border border-slate-800 rounded-xl p-3 text-slate-100 focus:outline-none focus:border-brand-500"
              />
            </div>
            <div>
              <label className="text-slate-400 font-semibold">PASSWORD</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full mt-1 bg-slate-950 border border-slate-800 rounded-xl p-3 text-slate-100 focus:outline-none focus:border-brand-500"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 py-3 bg-brand-600 hover:bg-brand-500 text-white rounded-xl font-bold shadow-lg shadow-brand-500/25 transition mt-2"
            >
              {loading ? 'Verifying Credentials...' : 'Authenticate'}
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
