import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { DataSourceItem } from '../types';
import { Database, ShieldCheck, CheckCircle2, ExternalLink, RefreshCw } from 'lucide-react';

export const DataSources: React.FC = () => {
  const [sources, setSources] = useState<DataSourceItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    async function loadSources() {
      try {
        setLoading(true);
        const data = await api.getDataSources();
        setSources(data);
      } catch (err) {
        console.error('Failed to load data sources', err);
      } finally {
        setLoading(false);
      }
    }
    loadSources();
  }, []);

  return (
    <div className="space-y-6 pb-12">
      <div>
        <h2 className="text-2xl font-bold text-slate-100">Data Sources & Quality Monitor</h2>
        <p className="text-sm text-slate-400">
          Transparent data catalog with provenance, open-data licensing, collection dates, and real-time quality validation metrics.
        </p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500"></div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {sources.map((src) => (
            <div
              key={src.id}
              className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 shadow-sm"
            >
              <div className="flex items-center justify-between">
                <span className="px-2.5 py-0.5 rounded text-[10px] font-bold bg-brand-500/20 text-brand-300 border border-brand-500/30">
                  {src.dataset_type}
                </span>
                <span className="text-xs font-mono text-emerald-400 font-bold">
                  Quality: {(src.quality_score * 100).toFixed(1)}%
                </span>
              </div>

              <div>
                <h3 className="text-sm font-bold text-slate-100">{src.source_name}</h3>
                <p className="text-xs text-slate-400 mt-0.5">{src.provider}</p>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs text-slate-300">
                <div className="p-2 bg-slate-950 rounded border border-slate-800">
                  <div className="text-[10px] text-slate-500">License</div>
                  <div className="font-semibold text-slate-200 mt-0.5">{src.license}</div>
                </div>
                <div className="p-2 bg-slate-950 rounded border border-slate-800">
                  <div className="text-[10px] text-slate-500">Coverage</div>
                  <div className="font-semibold text-slate-200 mt-0.5">{src.geographic_scope}</div>
                </div>
              </div>

              {src.quality_report && (
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-2 text-xs">
                  <div className="font-semibold text-slate-300 flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    Automated Data Quality Audit
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-[11px] text-slate-400">
                    <div>Completeness: <strong className="text-slate-200 font-mono">{(src.quality_report.completeness_score * 100).toFixed(0)}%</strong></div>
                    <div>Duplicates: <strong className="text-slate-200 font-mono">{(src.quality_report.duplicate_rate * 100).toFixed(1)}%</strong></div>
                    <div>Geo Validity: <strong className="text-slate-200 font-mono">{(src.quality_report.geographic_validity_rate * 100).toFixed(0)}%</strong></div>
                  </div>
                </div>
              )}

              {src.source_url && (
                <a
                  href={src.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-brand-400 hover:underline"
                >
                  <span>Official Portal Link</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
