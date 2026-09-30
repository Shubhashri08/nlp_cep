import React from 'react';
import type { Entity } from '../types';

const LABEL_COLOR: Record<string, string> = {
  STATION: '#3A5A94', LOCATION: '#3A5A94', LANDMARK: '#5E8FD0', ROAD: '#2E4365', WARD: '#1F5360',
  TEMPORAL: '#7D8799', ORGANIZATION: '#553B6B',
};
export const entityColor = (label: string) =>
  LABEL_COLOR[label] ?? (label.endsWith('_INFRA') ? '#A26815' : '#A8490F');

/** Highlights entity spans inline in the original text. */
export const EntityText: React.FC<{ text: string; entities: Entity[] }> = ({ text, entities }) => {
  const spans = entities.filter((e) => e.start_char !== undefined && e.end_char !== undefined).sort((a, b) => a.start_char! - b.start_char!);
  const out: React.ReactNode[] = [];
  let pos = 0;
  spans.forEach((e, i) => {
    if (e.start_char! < pos) return;
    if (e.start_char! > pos) out.push(text.slice(pos, e.start_char));
    const c = entityColor(e.label);
    out.push(
      <mark key={i} title={`${e.label} · ${Math.round(e.confidence * 100)}% · ${e.source ?? ''}`} className="rounded px-1 py-0.5 mx-0.5"
        style={{ background: `${c}1F`, color: c, boxShadow: `inset 0 -2px 0 ${c}` }}>
        {text.slice(e.start_char, e.end_char)}<sup className="ml-0.5 text-[9px] font-bold">{e.label.replace('_INCIDENT', '').replace('_INFRA', '')}</sup>
      </mark>,
    );
    pos = e.end_char!;
  });
  out.push(text.slice(pos));
  return <p className="leading-8 text-ink">{out}</p>;
};
