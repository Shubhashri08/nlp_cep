import React from 'react';
import { AlertTriangle, Inbox, Loader2, RefreshCw } from 'lucide-react';
import { PROVENANCE_STYLE, SEVERITY_COLOR, STATUS_COLOR } from '../lib/theme';
import { titleCase } from '../lib/format';

export const PageHeader: React.FC<{ title: string; subtitle?: React.ReactNode; actions?: React.ReactNode; eyebrow?: string }> = ({ title, subtitle, actions, eyebrow }) => (
  <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between mb-6">
    <div>
      {eyebrow && <div className="label text-marigold-700 mb-1">{eyebrow}</div>}
      <h1 className="h-display text-3xl md:text-4xl">{title}</h1>
      {subtitle && <p className="text-muted mt-1.5 max-w-3xl text-sm leading-relaxed">{subtitle}</p>}
    </div>
    {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
  </div>
);

export const Card: React.FC<{ title?: React.ReactNode; subtitle?: React.ReactNode; actions?: React.ReactNode; className?: string; children: React.ReactNode; bodyClass?: string }> = ({ title, subtitle, actions, className = '', children, bodyClass = 'p-5' }) => (
  <section className={`card ${className}`}>
    {(title || actions) && (
      <header className="flex items-start justify-between gap-3 px-5 pt-4 pb-0">
        <div>
          {title && <h3 className="font-display text-lg text-police leading-tight">{title}</h3>}
          {subtitle && <p className="text-xs text-muted mt-0.5">{subtitle}</p>}
        </div>
        {actions}
      </header>
    )}
    <div className={bodyClass}>{children}</div>
  </section>
);

export const StatTile: React.FC<{ label: string; value: React.ReactNode; hint?: React.ReactNode; accent?: 'marigold' | 'police' | 'citrine' | 'buff'; icon?: React.ReactNode }> = ({ label, value, hint, accent = 'police', icon }) => {
  const bar = { marigold: 'bg-marigold', police: 'bg-police', citrine: 'bg-citrine', buff: 'bg-buff' }[accent];
  return (
    <div className="card p-4 relative overflow-hidden">
      <div className={`absolute left-0 top-0 h-full w-1 ${bar}`} />
      <div className="flex items-start justify-between">
        <div className="label">{label}</div>
        {icon && <div className="text-police/60">{icon}</div>}
      </div>
      <div className="font-display text-3xl text-police mt-1.5 leading-none">{value}</div>
      {hint && <div className="text-xs text-muted mt-2">{hint}</div>}
    </div>
  );
};

export const Loading: React.FC<{ label?: string; className?: string }> = ({ label = 'Loading…', className = '' }) => (
  <div className={`flex items-center justify-center gap-2 py-12 text-muted text-sm ${className}`} role="status">
    <Loader2 className="h-4 w-4 animate-spin text-marigold" /> {label}
  </div>
);

export const ErrorState: React.FC<{ message: string; onRetry?: () => void; className?: string }> = ({ message, onRetry, className = '' }) => (
  <div className={`flex flex-col items-center justify-center gap-3 py-10 px-4 text-center ${className}`} role="alert">
    <AlertTriangle className="h-6 w-6 text-citrine" />
    <p className="text-sm text-citrine-600 max-w-md">{message}</p>
    {onRetry && <button className="btn-outline text-xs" onClick={onRetry}><RefreshCw className="h-3.5 w-3.5" />Retry</button>}
  </div>
);

export const EmptyState: React.FC<{ message: string; hint?: string; className?: string }> = ({ message, hint, className = '' }) => (
  <div className={`flex flex-col items-center justify-center gap-2 py-10 text-center ${className}`}>
    <Inbox className="h-6 w-6 text-pearl-500" />
    <p className="text-sm text-muted">{message}</p>
    {hint && <p className="text-xs text-muted/80">{hint}</p>}
  </div>
);

/** Renders loading / error / empty, else children. */
export function AsyncBlock<T>({ state, children, empty, isEmpty }: {
  state: { data: T | null; error: string | null; loading: boolean; reload: () => void };
  children: (d: T) => React.ReactNode; empty?: string; isEmpty?: (d: T) => boolean;
}) {
  if (state.loading && !state.data) return <Loading />;
  if (state.error) return <ErrorState message={state.error} onRetry={state.reload} />;
  if (!state.data) return null;
  if (isEmpty && isEmpty(state.data)) return <EmptyState message={empty || 'No data'} />;
  return <>{children(state.data)}</>;
}

export const Badge: React.FC<{ color?: string; bg?: string; children: React.ReactNode; title?: string; className?: string }> = ({ color = '#2E4365', bg, children, title, className = '' }) => (
  <span title={title} className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold whitespace-nowrap ${className}`}
    style={{ color, background: bg ?? `${color}1A` }}>{children}</span>
);

export const SeverityBadge: React.FC<{ level: string }> = ({ level }) => (
  <Badge color={SEVERITY_COLOR[level] ?? '#5E6B80'}><span className="h-1.5 w-1.5 rounded-full" style={{ background: SEVERITY_COLOR[level] }} />{titleCase(level)}</Badge>
);
export const StatusBadge: React.FC<{ status: string }> = ({ status }) => (
  <Badge color={STATUS_COLOR[status] ?? '#5E6B80'}>{titleCase(status)}</Badge>
);
export const ProvenanceBadge: React.FC<{ value?: string | null }> = ({ value }) => {
  if (!value) return null;
  const key = Object.keys(PROVENANCE_STYLE).find((k) => value.toUpperCase().includes(k)) ?? 'IMPORTED';
  const s = PROVENANCE_STYLE[key];
  return <Badge color={s.fg} bg={s.bg} title={`Data provenance: ${value}`}>{value.includes('+') || value.includes('·') ? value : s.label}</Badge>;
};

export const Select: React.FC<React.SelectHTMLAttributes<HTMLSelectElement> & { label?: string }> = ({ label, className = '', children, ...rest }) => (
  <label className={`flex flex-col gap-1 ${className}`}>
    {label && <span className="label">{label}</span>}
    <select className="input py-1.5" {...rest}>{children}</select>
  </label>
);

export const Tabs: React.FC<{ tabs: { id: string; label: string }[]; value: string; onChange: (id: string) => void }> = ({ tabs, value, onChange }) => (
  <div className="flex gap-1 border-b border-line overflow-x-auto" role="tablist">
    {tabs.map((t) => (
      <button key={t.id} role="tab" aria-selected={value === t.id} onClick={() => onChange(t.id)}
        className={`px-3 py-2 text-sm font-semibold whitespace-nowrap border-b-2 -mb-px transition ${value === t.id ? 'border-marigold text-police' : 'border-transparent text-muted hover:text-police'}`}>
        {t.label}
      </button>
    ))}
  </div>
);

export const Meter: React.FC<{ value: number; max?: number; color?: string; label?: string }> = ({ value, max = 100, color = '#E59D2C', label }) => (
  <div className="w-full" aria-label={label}>
    <div className="h-2 w-full rounded-full bg-pearl-200 overflow-hidden">
      <div className="h-full rounded-full" style={{ width: `${Math.max(0, Math.min(100, (100 * value) / max))}%`, background: color }} />
    </div>
  </div>
);

export const Legend: React.FC<{ items: { label: string; color: string }[]; className?: string }> = ({ items, className = '' }) => (
  <div className={`flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted ${className}`}>
    {items.map((i) => (
      <span key={i.label} className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm" style={{ background: i.color }} />{i.label}</span>
    ))}
  </div>
);
