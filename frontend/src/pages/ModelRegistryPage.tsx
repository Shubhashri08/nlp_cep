import React from 'react';
import { api } from '../api/client';
import { useApi } from '../hooks/useApi';
import { AsyncBlock, Badge, Card, PageHeader } from '../components/ui';
import { fmtNum, titleCase } from '../lib/format';

const flatten = (obj: Record<string, any>, prefix = ''): [string, any][] =>
  Object.entries(obj).flatMap(([k, v]) => (v && typeof v === 'object' && !Array.isArray(v) ? flatten(v, `${prefix}${k}.`) : [[`${prefix}${k}`, v] as [string, any]]));

const ModelRegistryPage: React.FC = () => {
  const state = useApi(() => api.models(), []);
  return (
    <div className="animate-fade-in">
      <PageHeader eyebrow="MLOps" title="Model Registry"
        subtitle="Active model versions with metrics measured at training time: held-out and hand-written gold-set scores for the classifier, time-based back-tests for the forecasters." />
      <AsyncBlock state={state} isEmpty={(d) => d.length === 0} empty="No models registered – run the seed script.">{(models) => (
        <div className="grid lg:grid-cols-2 gap-4">
          {models.map((m) => {
            const metrics = flatten(m.metrics).filter(([k, v]) => typeof v === 'number' && !k.startsWith('per_class'));
            const perClass = m.metrics?.per_class_f1_held_out as Record<string, number> | undefined;
            return (
              <Card key={m.id}>
                <div className="flex items-start justify-between gap-2"><div><Badge color="#3A5A94">{titleCase(m.model_type)}</Badge>
                  <h3 className="font-display text-lg text-police mt-1">{m.model_name}</h3><div className="text-xs text-muted">{m.version} · trained {m.training_date}</div></div>
                  <Badge color="#3F8A5A">{m.status}</Badge></div>
                <p className="text-xs text-muted mt-2">{m.training_dataset}</p>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mt-3">
                  {metrics.slice(0, 12).map(([k, v]) => (
                    <div key={k} className="bg-pearl-100 rounded-lg px-2.5 py-2"><div className="text-[10px] uppercase tracking-wide text-muted truncate" title={k}>{k.replace(/_/g, ' ')}</div>
                      <div className="font-semibold text-police text-sm">{Math.abs(v) <= 1 && !k.includes('samples') && !k.includes('dimensions') ? fmtNum(v, 3) : fmtNum(v, 2)}</div></div>
                  ))}
                </div>
                {perClass && <div className="mt-3"><div className="label mb-1">Per-class F1 (held-out)</div>
                  <div className="flex flex-wrap gap-1">{Object.entries(perClass).map(([c, f]) => <Badge key={c} color={f >= 0.9 ? '#3F8A5A' : f >= 0.75 ? '#A26815' : '#8A3B08'}>{titleCase(c)} {fmtNum(f, 2)}</Badge>)}</div></div>}
                <details className="mt-3 text-xs"><summary className="cursor-pointer text-police font-semibold">Parameters</summary>
                  <pre className="mt-1 bg-pearl-100 rounded p-2 overflow-x-auto whitespace-pre-wrap">{JSON.stringify(m.parameters, null, 1)}</pre></details>
              </Card>
            );
          })}
        </div>
      )}</AsyncBlock>
    </div>
  );
};

export default ModelRegistryPage;
