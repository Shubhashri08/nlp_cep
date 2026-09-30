import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { RecommendationItem } from '../types';
import { ShieldCheck, FileCheck, Layers, ArrowRight, CheckCircle2 } from 'lucide-react';

export const Recommendations: React.FC = () => {
  const [recommendations, setRecommendations] = useState<RecommendationItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [priorityFilter, setPriorityFilter] = useState<string>('');

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const data = await api.getRecommendations(undefined, undefined, priorityFilter || undefined);
        setRecommendations(data);
      } catch (err) {
        console.error('Failed to load recommendations', err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [priorityFilter]);

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-100">Evidence-Based Planning Recommendations</h2>
          <p className="text-sm text-slate-400">
            Multi-Criteria Decision Analysis (MCDA) generating transparent, traceable capital intervention recommendations backed by real datasets.
          </p>
        </div>

        <select
          value={priorityFilter}
          onChange={(e) => setPriorityFilter(e.target.value)}
          className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none self-start"
        >
          <option value="">All Priorities</option>
          <option value="HIGH">HIGH Priority Only</option>
          <option value="MEDIUM">MEDIUM Priority</option>
        </select>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500"></div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {recommendations.map((rec) => (
            <div
              key={rec.id}
              className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 shadow-sm hover:border-slate-700 transition"
            >
              <div className="flex items-center justify-between">
                <span className="px-2.5 py-0.5 rounded text-[10px] font-bold bg-brand-500/20 text-brand-300 border border-brand-500/30">
                  {rec.sector}
                </span>
                <span
                  className={`px-2.5 py-0.5 rounded text-[10px] font-bold ${
                    rec.priority_level === 'HIGH'
                      ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                      : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                  }`}
                >
                  {rec.priority_level} PRIORITY
                </span>
              </div>

              <div>
                <h3 className="text-sm font-bold text-slate-100">{rec.title}</h3>
                <p className="text-xs text-slate-400 mt-1">{rec.ward_name}</p>
              </div>

              <p className="text-xs text-slate-300 leading-relaxed bg-slate-950 p-3 rounded-lg border border-slate-800">
                {rec.recommendation_text}
              </p>

              {/* Supporting Evidence List */}
              <div className="space-y-1.5 text-xs">
                <span className="font-semibold text-slate-400">Traceable Supporting Evidence:</span>
                <div className="space-y-1">
                  {rec.supporting_evidence.map((ev, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between text-[11px] p-2 bg-slate-950 rounded border border-slate-800/80 text-slate-300"
                    >
                      <span className="font-mono text-slate-400">{ev.dataset} &rarr; {ev.field}</span>
                      <span className="font-bold text-emerald-400">{String(ev.val)}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="pt-2 border-t border-slate-800 flex items-center justify-between text-[10px] text-slate-500">
                <span>Methodology: {rec.methodology}</span>
                <span className="font-mono">MCDA Score: {rec.score.toFixed(1)}/100</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
