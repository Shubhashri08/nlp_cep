import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import type { Role } from '../types';
import { ROLE_LABEL } from '../components/layout/nav';

const ROLE_BLURB: Record<Role, string> = {
  ADMIN: 'Users, audit trail, all tools',
  PLANNER: 'Scenarios, recommendations, case status',
  ANALYST: 'Models, data imports, documents',
  VIEWER: 'Read-only dashboards & maps',
};

export const Login: React.FC = () => {
  const { login, demoLogin, config } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const navigate = useNavigate();
  const from = (useLocation().state as { from?: string } | null)?.from ?? '/';

  const run = async (key: string, fn: () => Promise<void>) => {
    setBusy(key);
    setError(null);
    try { await fn(); navigate(from, { replace: true }); } catch (e) { setError((e as Error).message); } finally { setBusy(null); }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-[1.1fr_1fr]">
      <div className="hidden lg:flex flex-col justify-between bg-police p-12 text-pearl-100 relative overflow-hidden">
        <div className="absolute -right-24 -bottom-24 h-96 w-96 rounded-full border-[28px] border-marigold/25" />
        <div className="absolute right-20 top-20 h-32 w-32 rounded-full border-4 border-buff/20" />
        <div className="relative">
          <div className="label text-buff/80">Greater Mumbai · BMC</div>
          <h1 className="font-display text-5xl text-buff mt-3 leading-[1.05]">Urban Planning<br />Decision Support</h1>
          <p className="mt-5 max-w-md text-pearl-200/90 leading-relaxed">
            Citizen feedback NLP, OpenStreetMap & Census GIS, Sentinel-2 growth detection, demand forecasting,
            scenario evaluation and evidence-based recommendations for 24 wards.
          </p>
        </div>
        <div className="relative grid grid-cols-3 gap-4 text-sm">
          {[['24', 'wards (OSM)'], ['1.24 Cr', 'residents · Census 2011'], ['3', 'Sentinel-2 epochs']].map(([v, l]) => (
            <div key={l} className="border-l-2 border-marigold pl-3"><div className="font-display text-2xl text-buff">{v}</div><div className="text-pearl-300 text-xs">{l}</div></div>
          ))}
        </div>
      </div>

      <div className="flex items-center justify-center p-6">
        <div className="w-full max-w-md">
          <h2 className="h-display text-3xl lg:hidden mb-2">Mumbai DSS</h2>
          <h2 className="font-display text-2xl text-police">Sign in</h2>
          <p className="text-sm text-muted mt-1">Use your municipal account.</p>

          <form className="mt-6 space-y-3" onSubmit={(e) => { e.preventDefault(); run('form', () => login(email, password)); }}>
            <label className="block"><span className="label">Email</span>
              <input className="input mt-1" type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} />
            </label>
            <label className="block"><span className="label">Password</span>
              <input className="input mt-1" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
            </label>
            {error && <p className="text-sm text-citrine" role="alert">{error}</p>}
            <button className="btn-secondary w-full" disabled={!!busy}>
              {busy === 'form' && <Loader2 className="h-4 w-4 animate-spin" />} Sign in
            </button>
          </form>

          {config?.demo_mode && (
            <div className="mt-8">
              <div className="flex items-center gap-3 mb-3"><div className="h-px flex-1 bg-line" /><span className="label">Demo access</span><div className="h-px flex-1 bg-line" /></div>
              <div className="grid grid-cols-2 gap-2">
                {(['PLANNER', 'ANALYST', 'VIEWER', 'ADMIN'] as Role[]).map((r) => (
                  <button key={r} onClick={() => run(r, () => demoLogin(r))} disabled={!!busy}
                    className="card text-left p-3 hover:border-marigold transition disabled:opacity-60">
                    <div className="text-sm font-semibold text-police flex items-center gap-2">
                      {busy === r && <Loader2 className="h-3.5 w-3.5 animate-spin" />}{ROLE_LABEL[r]}
                    </div>
                    <div className="text-[11px] text-muted mt-0.5">{ROLE_BLURB[r]}</div>
                  </button>
                ))}
              </div>
              <p className="text-[11px] text-muted mt-3">Demo login is enabled by <code>DEMO_MODE=true</code> on the server and must be disabled in production.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
