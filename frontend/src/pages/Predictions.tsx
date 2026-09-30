import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { ForecastResponse, WardSummary } from '../types';
import { TrendingUp, Cpu, Sliders, CheckCircle2, BarChart2 } from 'lucide-react';
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis,
  Tooltip, CartesianGrid, Legend, AreaChart, Area, BarChart, Bar
} from 'recharts';

export const Predictions: React.FC = () => {
  const [wards, setWards] = useState<WardSummary[]>([]);
  const [selectedWardId, setSelectedWardId] = useState<number | undefined>(undefined);
  const [horizonMonths, setHorizonMonths] = useState<number>(12);
  const [forecastData, setForecastData] = useState<ForecastResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    async function loadWards() {
      try {
        const wList = await api.getWards();
        setWards(wList);
      } catch (err) {
        console.error('Failed to load wards', err);
      }
    }
    loadWards();
  }, []);

  useEffect(() => {
    async function loadForecast() {
      try {
        setLoading(true);
        const data = await api.getForecast(selectedWardId, horizonMonths);
        setForecastData(data);
      } catch (err) {
        console.error('Failed to load forecast', err);
      } finally {
        setLoading(false);
      }
    }
    loadForecast();
  }, [selectedWardId, horizonMonths]);

  // Combine historical and forecast series for chart
  const combinedChartData = forecastData
    ? [
        ...forecastData.historical_data.map(h => ({
          date: h.date,
          actual: h.actual_value,
          forecast: null,
          lower: null,
          upper: null
        })),
        ...forecastData.forecast.map(f => ({
          date: f.date,
          actual: null,
          forecast: f.predicted_value,
          lower: f.lower_bound,
          upper: f.upper_bound
        }))
      ]
    : [];

  const featureImportanceList = forecastData
    ? Object.entries(forecastData.feature_importance).map(([k, v]) => ({
        feature: k.replace('_', ' '),
        importance: v
      }))
    : [];

  return (
    <div className="space-y-6 pb-12">
      {/* Header & Filter Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-100">Predictive Analytics & Demand Forecasting</h2>
          <p className="text-sm text-slate-400">
            Trained RandomForest Lag Regressor generating 12-month demand curves with 95% confidence intervals and feature importance analysis.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={selectedWardId || ''}
            onChange={(e) => setSelectedWardId(e.target.value ? Number(e.target.value) : undefined)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none"
          >
            <option value="">Metropolitan (All Wards)</option>
            {wards.map((w) => (
              <option key={w.id} value={w.id}>{w.name}</option>
            ))}
          </select>

          <select
            value={horizonMonths}
            onChange={(e) => setHorizonMonths(Number(e.target.value))}
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none"
          >
            <option value={6}>6 Months Horizon</option>
            <option value={12}>12 Months Horizon</option>
            <option value={18}>18 Months Horizon</option>
            <option value={24}>24 Months Horizon</option>
          </select>
        </div>
      </div>

      {loading || !forecastData ? (
        <div className="flex items-center justify-center h-96">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-brand-500"></div>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Metrics Header Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl space-y-1">
              <span className="text-xs text-slate-500 font-semibold">MODEL ALGORITHM</span>
              <div className="text-base font-bold text-slate-100">{forecastData.model_name}</div>
              <p className="text-[11px] text-brand-400 font-mono">{forecastData.model_version}</p>
            </div>
            <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl space-y-1">
              <span className="text-xs text-slate-500 font-semibold">MEAN ABSOLUTE ERROR (MAE)</span>
              <div className="text-2xl font-bold text-emerald-400">{forecastData.metrics.mae}</div>
              <p className="text-[11px] text-slate-400">Evaluated on out-of-time test split</p>
            </div>
            <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl space-y-1">
              <span className="text-xs text-slate-500 font-semibold">ROOT MEAN SQUARED ERROR</span>
              <div className="text-2xl font-bold text-slate-100">{forecastData.metrics.rmse}</div>
              <p className="text-[11px] text-slate-400">Standard error deviation</p>
            </div>
            <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl space-y-1">
              <span className="text-xs text-slate-500 font-semibold">COEFFICIENT OF DETERMINATION (R²)</span>
              <div className="text-2xl font-bold text-brand-400">{forecastData.metrics.r2_score}</div>
              <p className="text-[11px] text-slate-400">Variance explained</p>
            </div>
          </div>

          {/* Forecasting Curve with Confidence Bands */}
          <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-200">
                Service Demand Forecast: {forecastData.ward_name}
              </h3>
              <span className="text-xs text-slate-500">Historical Actuals vs 95% Confidence Prediction</span>
            </div>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={combinedChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="date" stroke="#64748b" fontSize={11} />
                  <YAxis stroke="#64748b" fontSize={11} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                  />
                  <Legend />
                  <Line type="monotone" dataKey="actual" name="Historical Actual" stroke="#0ea5e9" strokeWidth={2.5} dot={{ r: 4 }} />
                  <Line type="monotone" dataKey="forecast" name="Forecast Point" stroke="#10b981" strokeWidth={2.5} strokeDasharray="4 4" dot={{ r: 4 }} />
                  <Line type="monotone" dataKey="upper" name="Upper 95% Bound" stroke="#f59e0b" strokeWidth={1} strokeDasharray="2 2" dot={false} />
                  <Line type="monotone" dataKey="lower" name="Lower 95% Bound" stroke="#f59e0b" strokeWidth={1} strokeDasharray="2 2" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Feature Importance Bar Chart */}
          <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-200">Model Feature Importance (Gini Impurity Reduction)</h3>
              <span className="text-xs text-slate-500">Explainable ML</span>
            </div>
            <div className="h-60">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={featureImportanceList} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis type="number" stroke="#64748b" fontSize={11} />
                  <YAxis dataKey="feature" type="category" stroke="#64748b" fontSize={11} width={150} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                  />
                  <Bar dataKey="importance" fill="#8b5cf6" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
