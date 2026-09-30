import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { ScenarioResponse } from '../types';
import { Sliders, Play, Plus, ArrowRight, ShieldCheck, CheckCircle2, Info } from 'lucide-react';

export const ScenarioStudio: React.FC = () => {
  const [scenarios, setScenarios] = useState<ScenarioResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  // Form parameters
  const [title, setTitle] = useState<string>('Public Transit Expansion & Drainage Retrofit');
  const [description, setDescription] = useState<string>('Evaluate modal shift congestion relief and flood risk reduction.');
  const [transitDelta, setTransitDelta] = useState<number>(20);
  const [drainageCr, setDrainageCr] = useState<number>(35);
  const [popGrowth, setPopGrowth] = useState<number>(5);
  const [wasteExp, setWasteExp] = useState<number>(15);

  const [activeScenario, setActiveScenario] = useState<ScenarioResponse | null>(null);
  const [simulating, setSimulating] = useState<boolean>(false);

  const fetchScenarios = async () => {
    try {
      setLoading(true);
      const data = await api.getScenarios();
      setScenarios(data);
      if (data.length > 0 && !activeScenario) {
        setActiveScenario(data[0]);
      }
    } catch (err) {
      console.error('Failed to load scenarios', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchScenarios();
  }, []);

  const handleRunSimulation = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSimulating(true);
      const res = await api.createScenario({
        title,
        description,
        parameters: {
          transit_capacity_delta_pct: transitDelta,
          drainage_upgrade_investment_cr: drainageCr,
          population_growth_rate_pct: popGrowth,
          waste_processing_expansion_pct: wasteExp
        }
      });
      setActiveScenario(res);
      fetchScenarios();
    } catch (err: any) {
      alert(`Simulation error: ${err.message}`);
    } finally {
      setSimulating(false);
    }
  };

  return (
    <div className="space-y-6 pb-12">
      <div>
        <h2 className="text-2xl font-bold text-slate-100">Scenario Simulation Studio</h2>
        <p className="text-sm text-slate-400">
          Define municipal planning interventions. The simulation engine computes differential impacts on traffic congestion, flood resilience, and utility strain using empirical elasticity factors.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Form: Parameter Controls */}
        <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl space-y-5">
          <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
            <Sliders className="w-4 h-4 text-brand-400" />
            <h3 className="text-sm font-bold text-slate-200">Intervention Variables</h3>
          </div>

          <form onSubmit={handleRunSimulation} className="space-y-4 text-xs">
            <div>
              <label className="text-slate-400 font-semibold">SCENARIO TITLE</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full mt-1 bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-100 focus:outline-none focus:border-brand-500"
              />
            </div>

            {/* Slider 1: Transit Capacity */}
            <div className="space-y-1.5 p-3 bg-slate-950 rounded-lg border border-slate-800">
              <div className="flex justify-between font-semibold">
                <span className="text-slate-300">Public Transport Expansion</span>
                <span className="text-brand-400 font-mono">+{transitDelta}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="50"
                step="5"
                value={transitDelta}
                onChange={(e) => setTransitDelta(Number(e.target.value))}
                className="w-full accent-brand-500"
              />
              <span className="text-[10px] text-slate-500">Bus frequency & feeder routes</span>
            </div>

            {/* Slider 2: Drainage Investment */}
            <div className="space-y-1.5 p-3 bg-slate-950 rounded-lg border border-slate-800">
              <div className="flex justify-between font-semibold">
                <span className="text-slate-300">Storm Drain Capital Sanction</span>
                <span className="text-cyan-400 font-mono">₹{drainageCr} Cr</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                step="5"
                value={drainageCr}
                onChange={(e) => setDrainageCr(Number(e.target.value))}
                className="w-full accent-cyan-500"
              />
              <span className="text-[10px] text-slate-500">~{(drainageCr * 0.4).toFixed(1)} km added trunk capacity</span>
            </div>

            {/* Slider 3: Population Growth */}
            <div className="space-y-1.5 p-3 bg-slate-950 rounded-lg border border-slate-800">
              <div className="flex justify-between font-semibold">
                <span className="text-slate-300">Projected Population Growth</span>
                <span className="text-amber-400 font-mono">+{popGrowth}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="20"
                step="1"
                value={popGrowth}
                onChange={(e) => setPopGrowth(Number(e.target.value))}
                className="w-full accent-amber-500"
              />
              <span className="text-[10px] text-slate-500">Urban migration influx</span>
            </div>

            <button
              type="submit"
              disabled={simulating}
              className="w-full flex items-center justify-center gap-2 py-3 bg-brand-600 hover:bg-brand-500 text-white rounded-xl font-bold shadow-lg shadow-brand-500/25 transition mt-2"
            >
              <Play className="w-4 h-4 fill-white" />
              {simulating ? 'Calculating Impacts...' : 'Simulate Intervention'}
            </button>
          </form>
        </div>

        {/* Right 2 Columns: Baseline vs Scenario Differential Output */}
        <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl space-y-5 lg:col-span-2">
          {activeScenario ? (
            <div className="space-y-6">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div>
                  <h3 className="text-base font-bold text-slate-100">{activeScenario.title}</h3>
                  <p className="text-xs text-slate-400">{activeScenario.description}</p>
                </div>
                <span className="px-2.5 py-1 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded text-[10px] font-bold">
                  {activeScenario.evidence_status}
                </span>
              </div>

              {/* Impact Comparison Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Transit & Congestion */}
                <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-3">
                  <span className="text-xs font-bold text-slate-400">DAILY TRANSIT RIDERSHIP</span>
                  <div className="flex items-baseline gap-3">
                    <span className="text-slate-400 line-through text-sm">
                      {activeScenario.baseline_metrics.daily_transit_ridership?.toLocaleString()}
                    </span>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
                    <span className="text-2xl font-bold text-emerald-400">
                      {activeScenario.simulated_metrics.daily_transit_ridership?.toLocaleString()}
                    </span>
                  </div>
                  <div className="text-[11px] text-emerald-400 font-semibold">
                    +{activeScenario.delta_metrics.daily_transit_ridership_delta?.toLocaleString()} passengers / day (+65% modal shift elasticity)
                  </div>
                </div>

                <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-3">
                  <span className="text-xs font-bold text-slate-400">PEAK TRAFFIC CONGESTION INDEX</span>
                  <div className="flex items-baseline gap-3">
                    <span className="text-slate-400 line-through text-sm">
                      {activeScenario.baseline_metrics.avg_peak_congestion_index}
                    </span>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
                    <span className="text-2xl font-bold text-brand-400">
                      {activeScenario.simulated_metrics.avg_peak_congestion_index}
                    </span>
                  </div>
                  <div className="text-[11px] text-brand-400 font-semibold">
                    {activeScenario.delta_metrics.peak_congestion_index_delta} index reduction (Litman cross-elasticity)
                  </div>
                </div>

                {/* Flood Risk */}
                <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-3">
                  <span className="text-xs font-bold text-slate-400">FLOOD VULNERABILITY SCORE</span>
                  <div className="flex items-baseline gap-3">
                    <span className="text-slate-400 line-through text-sm">
                      {activeScenario.baseline_metrics.flood_risk_score}
                    </span>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
                    <span className="text-2xl font-bold text-cyan-400">
                      {activeScenario.simulated_metrics.flood_risk_score}
                    </span>
                  </div>
                  <div className="text-[11px] text-cyan-400 font-semibold">
                    {activeScenario.delta_metrics.flood_risk_score_delta} risk index reduction
                  </div>
                </div>

                {/* Flood Complaints */}
                <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-3">
                  <span className="text-xs font-bold text-slate-400">MONTHLY FLOOD COMPLAINTS</span>
                  <div className="flex items-baseline gap-3">
                    <span className="text-slate-400 line-through text-sm">
                      {activeScenario.baseline_metrics.monthly_flood_complaints}
                    </span>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
                    <span className="text-2xl font-bold text-emerald-400">
                      {activeScenario.simulated_metrics.monthly_flood_complaints}
                    </span>
                  </div>
                  <div className="text-[11px] text-emerald-400 font-semibold">
                    {activeScenario.delta_metrics.monthly_flood_complaints_delta} fewer emergency complaints/mo
                  </div>
                </div>
              </div>

              {/* Explicit Assumptions List */}
              <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-2 text-xs">
                <span className="font-bold text-slate-300 flex items-center gap-1.5">
                  <Info className="w-4 h-4 text-brand-400" />
                  Grounded Model Assumptions & Traceability:
                </span>
                <ul className="space-y-1.5 text-slate-400 list-disc list-inside">
                  {activeScenario.assumptions.map((asm, i) => (
                    <li key={i}>{asm}</li>
                  ))}
                </ul>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-64 text-slate-500 text-xs">
              No scenario simulated yet. Adjust sliders on the left and run simulation.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
