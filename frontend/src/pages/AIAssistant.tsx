import React, { useEffect, useRef, useState } from 'react';
import { Bot, ChevronDown, ChevronUp, Database, Send, User as UserIcon } from 'lucide-react';
import { api } from '../api/client';
import { useApi } from '../hooks/useApi';
import { Badge, Card, PageHeader, Select } from '../components/ui';
import type { AssistantResponse } from '../types';
import { fmtNum } from '../lib/format';

const SUGGESTIONS = [
  'Which wards have the most flooding complaints?',
  'What are the critical infrastructure gaps?',
  'Forecast water demand for the next year',
  'Which wards show rapid urban expansion?',
  'What should we prioritise in M/E ward?',
  'What infrastructure will Mumbai need in 2036?',
];

interface Turn { q: string; a?: AssistantResponse; error?: string; }

const inline = (s: string) =>
  s.split(/(\*\*[^*]+\*\*|\*[^*\s][^*]*\*)/g).map((part, j) =>
    part.startsWith('**') ? <strong key={j} className="text-police">{part.slice(2, -2)}</strong>
      : part.startsWith('*') && part.endsWith('*') && part.length > 2 ? <em key={j} className="text-muted">{part.slice(1, -1)}</em>
        : <React.Fragment key={j}>{part}</React.Fragment>);

/** Minimal, safe Markdown (no HTML injection): headings, bullets / numbered lists, bold, italics. */
const Rich: React.FC<{ text: string }> = ({ text }) => (
  <div className="space-y-1.5 leading-relaxed">
    {text.split('\n').filter((l) => l.trim()).map((raw, i) => {
      const heading = raw.match(/^\s*#{1,6}\s+(.*)$/);
      if (heading) return <h4 key={i} className="font-display text-base text-police pt-2">{inline(heading[1])}</h4>;
      const bullet = raw.match(/^(\s*)[-*•]\s+(.*)$/);
      if (bullet) return <div key={i} className="flex gap-2" style={{ paddingLeft: `${Math.min(3, Math.floor(bullet[1].length / 2)) * 12 + 4}px` }}><span className="text-marigold">•</span><span>{inline(bullet[2])}</span></div>;
      const num = raw.match(/^\s*(\d+)\.\s+(.*)$/);
      if (num) return <div key={i} className="flex gap-2 pl-1"><span className="font-semibold text-police">{num[1]}.</span><span>{inline(num[2])}</span></div>;
      return <p key={i}>{inline(raw)}</p>;
    })}
  </div>
);

const AIAssistant: React.FC = () => {
  const status = useApi(() => api.assistantStatus(), []);
  const wards = useApi(() => api.wards(), []);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [q, setQ] = useState('');
  const [wardId, setWardId] = useState('');
  const [busy, setBusy] = useState(false);
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }, [turns]);

  const ask = async (question: string) => {
    if (!question.trim() || busy) return;
    setQ('');
    setBusy(true);
    setTurns((t) => [...t, { q: question }]);
    try {
      const a = await api.ask(question, wardId ? Number(wardId) : undefined);
      setTurns((t) => t.map((x, i) => (i === t.length - 1 ? { ...x, a } : x)));
    } catch (e) {
      setTurns((t) => t.map((x, i) => (i === t.length - 1 ? { ...x, error: (e as Error).message } : x)));
    } finally { setBusy(false); }
  };

  return (
    <div className="animate-fade-in">
      <PageHeader eyebrow="Grounded in the municipal database" title="AI Planning Assistant"
        subtitle="Questions are answered only from read-only database / GIS tools. Every answer lists the tables, record IDs and SQL that produced it."
        actions={status.data && <Badge color={status.data.llm_available ? '#3F8A5A' : '#A26815'}>{status.data.llm_available ? `${status.data.provider} · ${status.data.model}` : 'Rule-based (no LLM key)'}</Badge>} />
      <div className="grid lg:grid-cols-[1fr_280px] gap-6">
        <Card bodyClass="p-0">
          <div className="h-[58vh] overflow-y-auto p-5 space-y-5">
            {turns.length === 0 && (
              <div className="text-center py-10">
                <Bot className="h-8 w-8 text-marigold mx-auto" />
                <p className="text-sm text-muted mt-2">{status.data?.mode}</p>
                <div className="flex flex-wrap justify-center gap-2 mt-5">{SUGGESTIONS.map((s) => <button key={s} className="btn-outline text-xs py-1.5" onClick={() => ask(s)}>{s}</button>)}</div>
              </div>
            )}
            {turns.map((t, i) => (
              <div key={i} className="space-y-3">
                <div className="flex gap-3 justify-end"><div className="bg-police text-pearl-50 rounded-2xl rounded-tr-sm px-4 py-2 text-sm max-w-[80%]">{t.q}</div>
                  <div className="h-8 w-8 rounded-full bg-pearl-300 grid place-items-center shrink-0"><UserIcon className="h-4 w-4 text-police" /></div></div>
                <div className="flex gap-3">
                  <div className="h-8 w-8 rounded-full bg-marigold grid place-items-center shrink-0"><Bot className="h-4 w-4 text-police-900" /></div>
                  <div className="flex-1 min-w-0">
                    {!t.a && !t.error && <div className="text-sm text-muted animate-pulse">Querying municipal data…</div>}
                    {t.error && <div className="text-sm text-citrine">{t.error}</div>}
                    {t.a && <Answer a={t.a} onFollowUp={ask} />}
                  </div>
                </div>
              </div>
            ))}
            <div ref={end} />
          </div>
          <form className="flex gap-2 p-4 border-t border-line" onSubmit={(e) => { e.preventDefault(); ask(q); }}>
            <input className="input" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ask about wards, complaints, gaps, growth, forecasts or scenarios…" aria-label="Question" />
            <button className="btn-primary" disabled={busy || !q.trim()} aria-label="Send"><Send className="h-4 w-4" /></button>
          </form>
        </Card>
        <div className="space-y-4">
          <Card title="Context">
            <Select label="Focus ward (optional)" value={wardId} onChange={(e) => setWardId(e.target.value)}>
              <option value="">None</option>{wards.data?.slice().sort((a, b) => a.ward_code.localeCompare(b.ward_code)).map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
            </Select>
          </Card>
          <Card title="Try asking">
            <div className="flex flex-col gap-1.5">{SUGGESTIONS.map((s) => <button key={s} className="text-left text-xs text-police hover:underline" onClick={() => ask(s)}>{s}</button>)}</div>
          </Card>
        </div>
      </div>
    </div>
  );
};

const Answer: React.FC<{ a: AssistantResponse; onFollowUp: (q: string) => void }> = ({ a, onFollowUp }) => {
  const [showData, setShowData] = useState(false);
  const cols = a.structured_findings.length ? Object.keys(a.structured_findings[0]).filter((k) => typeof a.structured_findings[0][k] !== 'object').slice(0, 7) : [];
  return (
    <div className="card p-4 text-sm">
      <Rich text={a.grounded_answer} />
      <div className="flex flex-wrap items-center gap-2 mt-3 text-[11px] text-muted">
        <Badge color="#5E6B80">{a.provider}{a.model ? ` · ${a.model}` : ''}</Badge><span>intent: {a.intent}</span><span>confidence {fmtNum(a.confidence * 100, 0)}%</span>
      </div>
      {(a.evidence_sources.length > 0 || cols.length > 0) && (
        <button className="mt-3 text-xs font-semibold text-police inline-flex items-center gap-1" onClick={() => setShowData((s) => !s)} aria-expanded={showData}>
          {showData ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}<Database className="h-3.5 w-3.5" />Evidence ({a.evidence_sources.length} queries, {a.structured_findings.length} rows)
        </button>
      )}
      {showData && (
        <div className="mt-2 space-y-3 animate-fade-in">
          {a.evidence_sources.map((s, i) => (
            <div key={i} className="bg-pearl-100 rounded-lg p-2.5">
              <div className="text-xs font-semibold text-police">{s.table_name}</div>
              <div className="text-[11px] text-muted">{s.description}{s.record_ids.length ? ` · records ${s.record_ids.slice(0, 12).join(', ')}${s.record_ids.length > 12 ? '…' : ''}` : ''}</div>
              <pre className="mt-1 text-[10px] font-mono whitespace-pre-wrap break-all text-ink/80 max-h-28 overflow-y-auto">{s.query_executed}</pre>
            </div>
          ))}
          {cols.length > 0 && (
            <div className="overflow-x-auto max-h-60"><table className="table-base text-xs">
              <thead><tr>{cols.map((c) => <th key={c}>{c.replace(/_/g, ' ')}</th>)}</tr></thead>
              <tbody>{a.structured_findings.slice(0, 15).map((r, i) => <tr key={i}>{cols.map((c) => <td key={c}>{typeof r[c] === 'number' ? fmtNum(r[c], 2) : String(r[c] ?? '')}</td>)}</tr>)}</tbody>
            </table></div>
          )}
        </div>
      )}
      {a.suggested_actions.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-3">{a.suggested_actions.map((s) => (
          s.endsWith('?') ? <button key={s} className="btn-outline text-[11px] py-1" onClick={() => onFollowUp(s)}>{s}</button> : <span key={s} className="text-[11px] text-muted">→ {s}</span>
        ))}</div>
      )}
    </div>
  );
};

export default AIAssistant;
