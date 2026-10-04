import React from 'react';
import { NavLink } from 'react-router-dom';
import { X } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { NAV } from './nav';

export const Sidebar: React.FC<{ open: boolean; onClose: () => void }> = ({ open, onClose }) => {
  const { hasRole } = useAuth();
  return (
    <>
      {open && <div className="fixed inset-0 z-30 bg-police-900/40 lg:hidden" onClick={onClose} />}
      <aside className={`fixed lg:sticky top-0 z-40 h-screen w-64 shrink-0 bg-police text-pearl-100 flex flex-col transition-transform
        ${open ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0`}>
        <div className="flex items-center justify-between px-5 h-16 border-b border-police-500/40">
          <div>
            <div className="font-display text-xl text-buff leading-none">Mumbai DSS</div>
            <div className="text-[10px] uppercase tracking-[0.18em] text-pearl-300/80 mt-1">Urban Planning Decision Support</div>
          </div>
          <button className="lg:hidden text-pearl-200" onClick={onClose} aria-label="Close menu"><X className="h-5 w-5" /></button>
        </div>
        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-5">
          {NAV.map((g) => {
            const items = g.items.filter((i) => !i.roles || hasRole(...i.roles));
            if (!items.length) return null;
            return (
              <div key={g.title}>
                <div className="px-2 mb-1.5 text-[10px] font-semibold uppercase tracking-[0.16em] text-pearl-300/70">{g.title}</div>
                {items.map((i) => (
                  <NavLink key={i.to} to={i.to} end={i.to === '/'} onClick={onClose}
                    className={({ isActive }) => `flex items-center gap-3 rounded-lg px-2.5 py-2 text-sm font-medium transition mb-0.5
                      ${isActive ? 'bg-marigold text-police-900 shadow-sm' : 'text-pearl-100/90 hover:bg-police-500/50 hover:text-white'}`}>
                    <i.icon className="h-4 w-4 shrink-0" />{i.label}
                  </NavLink>
                ))}
              </div>
            );
          })}
        </nav>
        <div className="px-5 py-3 border-t border-police-500/40 text-[10px] text-pearl-300/70 leading-relaxed">
          Data: © OpenStreetMap contributors (ODbL) · Census of India 2011 · Copernicus Sentinel-2 / DEM
        </div>
      </aside>
    </>
  );
};
