import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { ModelRegistryItem } from '../types';
import { Cpu, CheckCircle2, GitBranch, Terminal } from 'lucide-react';

export const ModelRegistryPage: React.FC = () => {
  const [models, setModels] = useState<ModelRegistryItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    async function loadModels() {
      try {
        setLoading(true);
        const data = await api.getRegisteredModels();
        setModels(data);
      } catch (err) {
        console.error('Failed to load models', err);
      } finally {
        setLoading(false);
      }
    }
    loadModels();
  }, []);

  return (
    <div className="space-y-6 pb-12">
      <div>
        <h2 className="text-2xl font-bold text-slate-100">Model Registry & Evaluation Hub</h2>
        <p className="text-sm text-slate-400">
          Trained Machine Learning, NLP, and Demand Forecasting model registry tracking version lineages, hyperparameters, and verifiable test metrics.
        </p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500"></div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {models.map((m) => (
            <div
              key={m.id}
              className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 shadow-sm"
            >
              <div className="flex items-center justify-between">
                <span className="px-2.5 py-0.5 rounded text-[10px] font-bold bg-brand-500/20 text-brand-300 border border-brand-500/30">
                  {m.model_type}
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                  {m.status}
                </span>
              </div>

              <div>
                <h3 className="text-sm font-bold text-slate-100">{m.model_name}</h3>
                <p className="text-xs text-brand-400 font-mono mt-0.5">Version: {m.version}</p>
              </div>

              <div className="text-xs text-slate-400">
                <span>Training Corpus: </span>
                <span className="text-slate-200 font-semibold">{m.training_dataset}</span>
              </div>

              {/* Evaluation Metrics */}
              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-2 text-xs">
                <span className="font-bold text-slate-300">Verified Evaluation Metrics:</span>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {Object.entries(m.metrics).map(([k, v], idx) => (
                    <div key={idx} className="p-2 bg-slate-900 rounded border border-slate-800/80">
                      <div className="text-[10px] text-slate-500 uppercase">{k.replace('_', ' ')}</div>
                      <div className="text-sm font-bold text-emerald-400 font-mono mt-0.5">{String(v)}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Hyperparameters */}
              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-1 text-xs">
                <span className="font-bold text-slate-400">Hyperparameters:</span>
                <pre className="text-[11px] text-slate-300 font-mono overflow-x-auto p-1">
                  {JSON.stringify(m.parameters, null, 2)}
                </pre>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
