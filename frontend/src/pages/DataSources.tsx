import React, { useState } from 'react';
import { ExternalLink, Upload } from 'lucide-react';
import { api } from '../api/client';
import { useApi } from '../hooks/useApi';
import { useAuth } from '../context/AuthContext';
import { AsyncBlock, Card, Meter, PageHeader, ProvenanceBadge, Select } from '../components/ui';
import { fmtInt, fmtNum } from '../lib/format';

const DataSources: React.FC = () => {
  const { hasRole } = useAuth();
  const state = useApi(() => api.dataSources(), []);
  return (
    <div className="animate-fade-in">
      <PageHeader eyebrow="Data governance" title="Data Sources & Quality"
        subtitle="Every dataset with its provider, licence, provenance class and measured quality (completeness, geographic validity, duplicates, freshness). Synthetic demonstration data is labelled as such throughout the system." />
      {hasRole('ANALYST') && <ImportCard onDone={state.reload} />}
      <AsyncBlock state={state} isEmpty={(d) => d.length === 0} empty="No sources registered.">{(list) => (
        <div className="grid lg:grid-cols-2 gap-4">
          {list.map((s) => (
            <Card key={s.id}>
              <div className="flex items-start justify-between gap-3">
                <div><ProvenanceBadge value={s.provenance} /><h3 className="font-display text-lg text-police mt-1 leading-snug">{s.source_name}</h3>
                  <div className="text-xs text-muted">{s.provider}</div></div>
                <div className="text-right shrink-0"><div className="font-display text-2xl text-police">{fmtNum(s.quality_score * 100, 0)}%</div><div className="label">quality</div></div>
              </div>
              {s.notes && <p className="text-xs text-ink/80 mt-2 leading-relaxed">{s.notes}</p>}
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 mt-3 text-xs">
                <span className="text-muted">Type</span><span>{s.dataset_type}</span>
                <span className="text-muted">Licence</span><span>{s.license}</span>
                <span className="text-muted">Update</span><span>{s.update_frequency}</span>
                <span className="text-muted">Collected</span><span>{s.date_collected}</span>
              </div>
              {s.quality_report && (
                <div className="mt-3 grid grid-cols-3 gap-3 text-[11px]">
                  {[['Completeness', s.quality_report.completeness_score], ['Geo validity', s.quality_report.geographic_validity_rate], ['Consistency', s.quality_report.consistency_score]].map(([l, v]) => (
                    <div key={l as string}><div className="flex justify-between"><span className="text-muted">{l}</span><span>{fmtNum((v as number) * 100, 0)}%</span></div><Meter value={(v as number) * 100} color="#3A5A94" /></div>
                  ))}
                  <div className="col-span-3 text-muted">{fmtInt(s.quality_report.total_records)} records · {s.quality_report.missing_values_count} missing · {fmtNum(s.quality_report.duplicate_rate * 100, 2)}% duplicates · {s.quality_report.freshness_days} days old</div>
                </div>
              )}
              {s.source_url && <a className="inline-flex items-center gap-1 text-xs text-police underline mt-3" href={s.source_url} target="_blank" rel="noreferrer">Source <ExternalLink className="h-3 w-3" /></a>}
            </Card>
          ))}
        </div>
      )}</AsyncBlock>
    </div>
  );
};

const ImportCard: React.FC<{ onDone: () => void }> = ({ onDone }) => {
  const [dataset, setDataset] = useState('complaints');
  const [name, setName] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;
    const f = new FormData();
    f.append('dataset', dataset); f.append('source_name', name || file.name); f.append('file', file);
    setBusy(true); setResult(null);
    try { const r = await api.importData(f); setResult(`Imported ${r.imported}/${r.total_records} records · quality ${fmtNum(r.quality_score * 100, 0)}% · ${r.invalid_locations} invalid locations · ${r.duplicates} duplicates. ${r.note}`); onDone(); }
    catch (err) { setResult((err as Error).message); } finally { setBusy(false); }
  };
  return (
    <Card className="mb-6" title="Import a dataset" subtitle="CSV or GeoJSON. Complaints need a 'text' column (optional latitude, longitude, ward_code, created_at, status); assets need name, asset_type, latitude, longitude.">
      <form onSubmit={submit} className="flex flex-wrap items-end gap-3">
        <Select label="Dataset" value={dataset} onChange={(e) => setDataset(e.target.value)}><option value="complaints">Citizen complaints</option><option value="assets">Infrastructure assets</option></Select>
        <label className="flex-1 min-w-[200px]"><span className="label">Source name</span><input className="input mt-1 py-1.5" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. MyBMC export Q3" /></label>
        <label className="btn-outline cursor-pointer"><Upload className="h-4 w-4" />{file ? file.name : 'Choose file'}<input type="file" accept=".csv,.json,.geojson" className="hidden" onChange={(e) => setFile(e.target.files?.[0] ?? null)} /></label>
        <button className="btn-primary" disabled={!file || busy}>{busy ? 'Importing…' : 'Import'}</button>
      </form>
      {result && <p className="text-xs text-police mt-3">{result}</p>}
    </Card>
  );
};

export default DataSources;
