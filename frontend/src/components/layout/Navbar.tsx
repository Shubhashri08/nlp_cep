import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { UserRole } from '../../types';
import { Building2, Shield, UserCheck, LogOut, Activity } from 'lucide-react';

export const Navbar: React.FC = () => {
  const { user, role, quickLoginAs, logout } = useAuth();

  const handleRoleSwitch = (e: React.ChangeEvent<HTMLSelectElement>) => {
    quickLoginAs(e.target.value as UserRole);
  };

  return (
    <header className="h-16 border-b border-slate-800 bg-slate-900/80 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-30">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 to-emerald-500 flex items-center justify-center shadow-lg shadow-brand-500/20">
          <Building2 className="w-6 h-6 text-white" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-base font-bold text-slate-100 tracking-tight">Urban Planning DSS</h1>
            <span className="px-2 py-0.5 text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-full">
              LIVE SYSTEM
            </span>
          </div>
          <p className="text-xs text-slate-400">Metropolitan AI & Geospatial Decision Support</p>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700/60 text-xs text-slate-300">
          <Activity className="w-4 h-4 text-emerald-400 animate-pulse" />
          <span>PostGIS / ML Inference Active</span>
        </div>

        {/* Quick Role Switcher */}
        <div className="flex items-center gap-2 bg-slate-800/90 border border-slate-700 rounded-lg px-3 py-1.5">
          <Shield className="w-4 h-4 text-brand-400" />
          <span className="text-xs text-slate-400">Role:</span>
          <select
            value={role || 'ADMIN'}
            onChange={handleRoleSwitch}
            className="bg-transparent text-xs font-semibold text-brand-300 focus:outline-none cursor-pointer"
          >
            <option value="ADMIN" className="bg-slate-900 text-slate-200">ADMIN</option>
            <option value="PLANNER" className="bg-slate-900 text-slate-200">PLANNER</option>
            <option value="ANALYST" className="bg-slate-900 text-slate-200">ANALYST</option>
            <option value="VIEWER" className="bg-slate-900 text-slate-200">VIEWER</option>
          </select>
        </div>

        {/* User profile */}
        <div className="flex items-center gap-3 pl-3 border-l border-slate-800">
          <div className="text-right hidden sm:block">
            <div className="text-xs font-semibold text-slate-200">{user?.full_name || 'Municipal Officer'}</div>
            <div className="text-[11px] text-slate-400">{user?.email || 'user@municipal.gov.in'}</div>
          </div>
          <button
            onClick={logout}
            title="Logout"
            className="p-2 rounded-lg bg-slate-800 hover:bg-rose-500/20 hover:text-rose-400 text-slate-400 transition"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};
