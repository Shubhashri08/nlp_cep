import React from 'react';
import type { ChoroplethSpec } from '../../types';
import { GROWTH_COLORS, RAMPS, rampBreaks } from '../../lib/theme';
import { fmtNum, titleCase } from '../../lib/format';

export const ChoroplethLegend: React.FC<{ spec: ChoroplethSpec; min: number; max: number }> = ({ spec, min, max }) => {
  if (spec.ramp === 'categorical') {
    return (
      <div>
        <div className="label mb-1.5">{spec.label}</div>
        {Object.entries(GROWTH_COLORS).map(([k, c]) => (
          <div key={k} className="flex items-center gap-2 text-xs text-ink"><span className="h-3 w-4 rounded-sm" style={{ background: c }} />{titleCase(k)}</div>
        ))}
      </div>
    );
  }
  const ramp = RAMPS[spec.ramp];
  const breaks = rampBreaks(min, max, ramp.length);
  return (
    <div>
      <div className="label mb-1.5">{spec.label}{spec.unit ? ` (${spec.unit})` : ''}</div>
      <div className="flex">{ramp.map((c) => <span key={c} className="h-3 flex-1 first:rounded-l-sm last:rounded-r-sm" style={{ background: c }} />)}</div>
      <div className="flex justify-between text-[10px] text-muted mt-1"><span>{fmtNum(breaks[0], 1)}</span><span>{fmtNum(breaks[breaks.length - 1], 1)}</span></div>
    </div>
  );
};
