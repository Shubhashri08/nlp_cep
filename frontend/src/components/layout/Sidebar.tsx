import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, Map, MessageSquareText, Sparkles,
  AlertTriangle, Network, Users, Satellite, TrendingUp,
  Sliders, ShieldCheck, Database, Cpu, ShieldAlert
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const navSections = [
    {
      title: 'OPERATIONS & GIS',
      links: [
        { to: '/', label: 'Executive Dashboard', icon: LayoutDashboard },
        { to: '/gis', label: 'Interactive GIS Explorer', icon: Map },
        { to: '/citizen-feedback', label: 'Citizen Grievances & NLP', icon: MessageSquareText },
        { to: '/nlp-analytics', label: 'Multilingual NLP Studio', icon: Sparkles },
      ]
    },
    {
      title: 'SPATIAL & SECTORAL ANALYSIS',
      links: [
        { to: '/infrastructure-gaps', label: 'Infrastructure Gaps', icon: Network },
        { to: '/demographics', label: 'Demographics & Land Use', icon: Users },
        { to: '/urban-growth', label: 'Urban Growth & Satellite', icon: Satellite },
      ]
    },
    {
      title: 'DECISION SUPPORT & ML',
      links: [
        { to: '/predictions', label: 'Demand Forecasting', icon: TrendingUp },
        { to: '/scenario-studio', label: 'Scenario Studio', icon: Sliders },
        { to: '/recommendations', label: 'Evidence Recommendations', icon: ShieldCheck },
        { to: '/ai-assistant', label: 'AI Planning Assistant', icon: MessageSquareText },
      ]
    },
    {
      title: 'GOVERNANCE & SYSTEM',
      links: [
        { to: '/data-sources', label: 'Data Sources & Quality', icon: Database },
        { to: '/model-registry', label: 'Model Registry', icon: Cpu },
        { to: '/audit-admin', label: 'Audit & Admin', icon: ShieldAlert },
      ]
    }
  ];

  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col h-[calc(100vh-4rem)] sticky top-16 overflow-y-auto select-none scrollbar-thin">
      <div className="p-4 space-y-6 flex-1">
        {navSections.map((section, idx) => (
          <div key={idx} className="space-y-1.5">
            <div className="px-3 text-[11px] font-bold text-slate-500 tracking-wider">
              {section.title}
            </div>
            {section.links.map((link, lIdx) => {
              const Icon = link.icon;
              return (
                <NavLink
                  key={lIdx}
                  to={link.to}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                      isActive
                        ? 'bg-brand-600/20 text-brand-400 border border-brand-500/30 shadow-sm'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                    }`
                  }
                >
                  <Icon className="w-4 h-4 flex-shrink-0" />
                  <span>{link.label}</span>
                </NavLink>
              );
            })}
          </div>
        ))}
      </div>
      <div className="p-4 border-t border-slate-800 bg-slate-950/40 text-[11px] text-slate-500 text-center">
        v1.0.0 • Production Municipal DSS
      </div>
    </aside>
  );
};
