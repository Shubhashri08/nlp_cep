import React, { useState } from 'react';
import { api } from '../api/client';
import { NLPAnalysisResult } from '../types';
import {
  Sparkles, Globe, Tag, MapPin, FileText, Cpu, CheckCircle2, ArrowRight
} from 'lucide-react';

const SAMPLE_TEXTS = [
  "There is severe waterlogging near Andheri Station every monsoon and the road is completely submerged.",
  "Andheri SV road par bohot bade khadde pad gaye hain aur traffic jam ho raha hai.",
  "रस्त्यावर कचरा साचला आहे आणि दादर स्टेशन जवळ प्रचंड दुर्गंधी पसरली आहे.",
  "The road near the school is flooded and garbage has not been collected for three days on Linking Road Bandra.",
  "Streetlights not working on Link Road near Infinity Mall complete darkness at night."
];

export const NLPAnalytics: React.FC = () => {
  const [inputText, setInputText] = useState<string>(SAMPLE_TEXTS[0]);
  const [result, setResult] = useState<NLPAnalysisResult | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyze = async (textToRun?: string) => {
    const text = textToRun || inputText;
    if (!text.trim()) return;
    try {
      setLoading(true);
      setError(null);
      const res = await api.analyzeNLP(text);
      setResult(res);
    } catch (err: any) {
      setError(err.message || 'NLP analysis failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-slate-100">Multilingual NLP Analytics Studio</h2>
        <p className="text-sm text-slate-400">
          Live inspection of Tokenization, Code-Mixed Normalization (Hinglish/Marathi), Multi-Label Classifier, Named Entity Recognition, and Location Resolution.
        </p>
      </div>

      {/* Interactive Testing Box */}
      <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl space-y-4">
        <div className="flex items-center justify-between">
          <label className="text-xs font-bold text-slate-300">INPUT CITIZEN GRIEVANCE TEXT</label>
          <span className="text-xs text-slate-500">Supports English, Hindi, Marathi, & Transliterated Hinglish</span>
        </div>

        <textarea
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          rows={3}
          className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-slate-100 focus:outline-none focus:border-brand-500 font-sans"
          placeholder="Enter or paste complaint text..."
        />

        {/* Quick Sample Chips */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-slate-500">Quick Samples:</span>
          {SAMPLE_TEXTS.map((sample, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => {
                setInputText(sample);
                handleAnalyze(sample);
              }}
              className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-[11px] truncate max-w-[200px] border border-slate-700 transition"
            >
              {sample}
            </button>
          ))}
        </div>

        <div className="flex justify-end">
          <button
            onClick={() => handleAnalyze()}
            disabled={loading || !inputText.trim()}
            className="flex items-center gap-2 px-5 py-2.5 bg-brand-600 hover:bg-brand-500 text-white rounded-xl text-xs font-bold shadow-lg shadow-brand-500/25 transition"
          >
            <Sparkles className="w-4 h-4" />
            {loading ? 'Running Live NLP Engine...' : 'Execute NLP Pipeline'}
          </button>
        </div>
      </div>

      {/* NLP Pipeline Stages Output */}
      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-xl text-xs">
          {error}
        </div>
      )}

      {result && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Stage 1 & 2: Language & Classification */}
          <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                <Globe className="w-4 h-4 text-brand-400" />
                Language & Multi-Label Classification
              </h3>
              <span className="text-xs font-mono text-slate-500">{result.model_version}</span>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                <div className="text-slate-500">Detected Language</div>
                <div className="text-base font-bold text-slate-100 font-mono mt-0.5">{result.language.toUpperCase()}</div>
                <div className="text-[10px] text-slate-400">Confidence: {(result.language_confidence * 100).toFixed(1)}%</div>
              </div>
              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                <div className="text-slate-500">Primary Category</div>
                <div className="text-base font-bold text-brand-400 mt-0.5">{result.primary_category}</div>
                <div className="text-[10px] text-slate-400">Confidence: {(result.confidence * 100).toFixed(1)}%</div>
              </div>
            </div>

            {/* Multi-label scores */}
            <div className="space-y-2">
              <span className="text-xs font-semibold text-slate-400">All Detected Categories (Multi-Label):</span>
              <div className="space-y-1.5">
                {result.categories.map((c, i) => (
                  <div key={i} className="p-2 bg-slate-950 rounded border border-slate-800 flex items-center justify-between text-xs">
                    <span className="text-slate-200 font-medium">{c.category}</span>
                    <div className="flex items-center gap-2">
                      <div className="w-20 bg-slate-800 rounded-full h-1.5 overflow-hidden">
                        <div
                          className="bg-brand-500 h-full rounded-full"
                          style={{ width: `${Math.min(100, c.confidence * 100)}%` }}
                        ></div>
                      </div>
                      <span className="font-mono text-slate-400">{(c.confidence * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Normalized Text */}
            <div className="space-y-1 text-xs">
              <span className="text-slate-500 font-semibold">Normalized Concept Formulation:</span>
              <p className="p-2.5 bg-slate-950 rounded border border-slate-800 text-slate-300 font-mono text-[11px]">
                {result.cleaned_text}
              </p>
            </div>
          </div>

          {/* Stage 3 & 4: NER & Geocoding Resolution */}
          <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                <Tag className="w-4 h-4 text-emerald-400" />
                Named Entity Recognition & Geocoding
              </h3>
              <span className="text-xs text-slate-500">Gazetteer + Nominatim</span>
            </div>

            {/* Entities List */}
            <div className="space-y-2">
              <span className="text-xs font-semibold text-slate-400">Extracted Named Entities:</span>
              {result.entities.length === 0 ? (
                <div className="p-3 bg-slate-950 rounded text-slate-500 text-xs">No entities detected.</div>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {result.entities.map((e, i) => (
                    <div
                      key={i}
                      className="px-2.5 py-1 bg-slate-950 border border-slate-800 rounded-lg text-xs flex items-center gap-1.5"
                    >
                      <span className="text-slate-200 font-semibold">{e.text}</span>
                      <span className="px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-400 text-[10px] font-mono">
                        {e.label}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Geocoding Resolution Card */}
            <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-200 flex items-center gap-1.5">
                  <MapPin className="w-4 h-4 text-emerald-400" />
                  Geospatial Resolution Status
                </span>
                <span
                  className={`px-2 py-0.5 rounded font-bold text-[10px] ${
                    result.is_location_resolved
                      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                      : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                  }`}
                >
                  {result.is_location_resolved ? 'LOCATION RESOLVED' : 'UNRESOLVED'}
                </span>
              </div>

              {result.is_location_resolved ? (
                <div className="space-y-1 text-slate-300">
                  <div>Resolved Landmark: <strong>{result.resolved_location}</strong></div>
                  <div>Coordinates: <span className="font-mono text-emerald-400">{result.resolved_lat?.toFixed(5)}, {result.resolved_lng?.toFixed(5)}</span></div>
                  <div>Geocode Confidence: <span className="font-mono">{(result.geocoding_confidence * 100).toFixed(0)}%</span></div>
                </div>
              ) : (
                <div className="text-slate-400 italic">
                  No unambiguous municipal location entity identified. Geocode marked as unresolved to prevent arbitrary coordinate placement.
                </div>
              )}
            </div>

            {/* Structured Summary */}
            <div className="space-y-1 text-xs">
              <span className="text-slate-500 font-semibold">Generated Traceable Summary:</span>
              <p className="p-3 bg-brand-950/30 rounded border border-brand-800/40 text-brand-300 leading-relaxed">
                {result.summary}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
