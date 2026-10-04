import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronDown, LogOut, Menu } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import type { Role } from '../../types';
import { ROLE_LABEL } from './nav';

export const Navbar: React.FC<{ onMenu: () => void }> = ({ onMenu }) => {
  const { user, config, logout, demoLogin } = useAuth();
  const [open, setOpen] = useState(false);
  const [switching, setSwitching] = useState(false);
  const navigate = useNavigate();

  const switchRole = async (role: Role) => {
    setSwitching(true);
    try { await demoLogin(role); setOpen(false); navigate('/'); } catch { /* keep current session */ } finally { setSwitching(false); }
  };

  return (
    <header className="sticky top-0 z-20 h-16 bg-paper/90 backdrop-blur border-b border-line flex items-center justify-between px-4 md:px-6">
      <div className="flex items-center gap-3">
        <button className="lg:hidden btn-ghost px-2" onClick={onMenu} aria-label="Open menu"><Menu className="h-5 w-5" /></button>
        <div className="hidden sm:block text-sm text-muted">
          Greater Mumbai · <span className="text-police font-semibold">24 BMC wards</span>
        </div>
      </div>
      <div className="flex items-center gap-3">
        {config && (
          <span className="hidden md:inline-flex items-center gap-1.5 rounded-full border border-line bg-white px-2.5 py-1 text-[11px] font-semibold text-police"
            title="Assistant / summarisation engine">
            <span className={`h-1.5 w-1.5 rounded-full ${config.llm_provider !== 'none' ? 'bg-emerald-600' : 'bg-marigold'}`} />
            {config.llm_provider !== 'none' ? `LLM: ${config.llm_provider}` : 'LLM: offline rules'}
          </span>
        )}
        <div className="relative">
          <button className="flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-pearl-200" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
            <div className="h-8 w-8 rounded-full bg-police text-buff grid place-items-center font-display">{user?.full_name?.[0] ?? '?'}</div>
            <div className="hidden sm:block text-left leading-tight">
              <div className="text-sm font-semibold text-police">{user?.full_name}</div>
              <div className="text-[11px] text-muted">{user ? ROLE_LABEL[user.role] : ''}</div>
            </div>
            <ChevronDown className="h-4 w-4 text-muted" />
          </button>
          {open && (
            <div className="absolute right-0 mt-2 w-60 card p-2 animate-fade-in">
              <div className="px-2 py-1.5 text-xs text-muted truncate">{user?.email}</div>
              {config?.demo_mode && (
                <>
                  <div className="label px-2 pt-2 pb-1">Demo: switch role</div>
                  {(['ADMIN', 'PLANNER', 'ANALYST', 'VIEWER'] as Role[]).map((r) => (
                    <button key={r} disabled={switching || user?.role === r} onClick={() => switchRole(r)}
                      className="w-full text-left rounded-md px-2 py-1.5 text-sm hover:bg-pearl-100 disabled:opacity-50">
                      {ROLE_LABEL[r]}{user?.role === r ? ' (current)' : ''}
                    </button>
                  ))}
                </>
              )}
              <button onClick={() => { logout(); navigate('/login'); }} className="mt-1 w-full flex items-center gap-2 rounded-md px-2 py-1.5 text-sm text-citrine hover:bg-citrine-50">
                <LogOut className="h-4 w-4" /> Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
