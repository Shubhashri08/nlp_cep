import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { CitizenRequest } from '../types';
import {
  MessageSquareText, Search, Filter, Plus, CheckCircle,
  Clock, AlertCircle, MapPin, Sparkles, Send
} from 'lucide-react';

export const CitizenFeedback: React.FC = () => {
  const [requests, setRequests] = useState<CitizenRequest[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [semanticQuery, setSemanticQuery] = useState<string>('');
  const [semanticResults, setSemanticResults] = useState<any[] | null>(null);
  const [searching, setSearching] = useState<boolean>(false);

  // Filter state
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');

  // New Request Form Modal State
  const [showModal, setShowModal] = useState<boolean>(false);
  const [newText, setNewText] = useState<string>('');
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [submitSuccess, setSubmitSuccess] = useState<string | null>(null);

  const fetchRequests = async () => {
    try {
      setLoading(true);
      const data = await api.getCitizenRequests({
        category: categoryFilter || undefined,
        status: statusFilter || undefined,
      });
      setRequests(data);
    } catch (err) {
      console.error('Error fetching complaints', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRequests();
  }, [categoryFilter, statusFilter]);

  const handleSemanticSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!semanticQuery.trim()) {
      setSemanticResults(null);
      return;
    }
    try {
      setSearching(true);
      const results = await api.semanticSearch(semanticQuery);
      setSemanticResults(results);
    } catch (err) {
      console.error('Semantic search error', err);
    } finally {
      setSearching(false);
    }
  };

  const handleCreateRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newText.trim()) return;
    try {
      setSubmitting(true);
      const created = await api.createCitizenRequest({ text: newText });
      setSubmitSuccess(`Grievance ${created.request_uid} processed & tagged as ${created.primary_category}`);
      setNewText('');
      fetchRequests();
      setTimeout(() => {
        setSubmitSuccess(null);
        setShowModal(false);
      }, 2500);
    } catch (err: any) {
      alert(`Error submitting request: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-100">Citizen Grievances & Multilingual NLP</h2>
          <p className="text-sm text-slate-400">
            Real citizen reports ingested, translated, classified, geocoded, and embedded into 64-D semantic space.
          </p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-500 text-white rounded-lg text-xs font-semibold shadow-lg shadow-brand-500/20 transition self-start"
        >
          <Plus className="w-4 h-4" />
          Submit Citizen Report
        </button>
      </div>

      {/* Dense Semantic Search Bar */}
      <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl space-y-3">
        <form onSubmit={handleSemanticSearch} className="flex gap-2">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
            <input
              type="text"
              value={semanticQuery}
              onChange={(e) => setSemanticQuery(e.target.value)}
              placeholder="Dense Semantic Search: 'waterlogging near station', 'choked sewers', 'potholes'..."
              className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-4 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-brand-500"
            />
          </div>
          <button
            type="submit"
            disabled={searching}
            className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-brand-400 rounded-lg text-xs font-semibold border border-slate-700 transition"
          >
            <Sparkles className="w-4 h-4 text-brand-400" />
            {searching ? 'Vector Searching...' : 'Semantic Search'}
          </button>
          {semanticResults && (
            <button
              type="button"
              onClick={() => { setSemanticResults(null); setSemanticQuery(''); }}
              className="px-3 py-2 bg-slate-800 text-slate-400 hover:text-slate-200 rounded-lg text-xs"
            >
              Clear
            </button>
          )}
        </form>

        {/* Semantic Search Match Results */}
        {semanticResults && (
          <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-2 text-xs">
            <div className="font-semibold text-brand-400 flex items-center gap-2">
              <Sparkles className="w-3.5 h-3.5" />
              Found {semanticResults.length} Semantically Relevant Records:
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {semanticResults.map((r, i) => (
                <div key={i} className="p-2.5 bg-slate-900 rounded border border-slate-800 space-y-1">
                  <div className="flex justify-between text-slate-400">
                    <span className="font-mono text-slate-300">{r.request_uid}</span>
                    <span className="text-emerald-400 font-mono">Similarity: {(r.similarity_score * 100).toFixed(1)}%</span>
                  </div>
                  <p className="text-slate-200 italic">"{r.text}"</p>
                  <div className="text-[10px] text-slate-500 flex gap-2">
                    <span>Category: {r.primary_category}</span>
                    <span>•</span>
                    <span>Ward: {r.ward_name || 'Unassigned'}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Filters & Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        <div className="p-4 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3 bg-slate-950/40">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
            <Filter className="w-4 h-4 text-brand-400" />
            <span>Database Records ({requests.length})</span>
          </div>
          <div className="flex items-center gap-3 text-xs">
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1 text-slate-200 focus:outline-none"
            >
              <option value="">All Categories</option>
              <option value="FLOODING">FLOODING</option>
              <option value="DRAINAGE">DRAINAGE</option>
              <option value="ROAD_INFRASTRUCTURE">ROAD_INFRASTRUCTURE</option>
              <option value="WASTE_MANAGEMENT">WASTE_MANAGEMENT</option>
              <option value="WATER_SUPPLY">WATER_SUPPLY</option>
              <option value="STREETLIGHT">STREETLIGHT</option>
              <option value="TRAFFIC">TRAFFIC</option>
            </select>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1 text-slate-200 focus:outline-none"
            >
              <option value="">All Statuses</option>
              <option value="OPEN">OPEN</option>
              <option value="IN_PROGRESS">IN_PROGRESS</option>
              <option value="RESOLVED">RESOLVED</option>
            </select>
          </div>
        </div>

        {/* Requests Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950 text-slate-400 font-semibold border-b border-slate-800">
              <tr>
                <th className="p-3">UID</th>
                <th className="p-3">ORIGINAL CITIZEN TEXT</th>
                <th className="p-3">LANGUAGE</th>
                <th className="p-3">CLASSIFICATION</th>
                <th className="p-3">WARD & GEOCODE</th>
                <th className="p-3">STATUS</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-slate-300">
              {requests.map((req) => (
                <tr key={req.id} className="hover:bg-slate-800/40 transition">
                  <td className="p-3 font-mono font-bold text-slate-400">{req.request_uid}</td>
                  <td className="p-3 max-w-sm">
                    <p className="text-slate-100 line-clamp-2">{req.original_text}</p>
                    {req.summary && <p className="text-[11px] text-slate-500 italic mt-0.5">{req.summary}</p>}
                  </td>
                  <td className="p-3">
                    <span className="px-2 py-0.5 bg-slate-800 text-slate-300 rounded font-mono text-[10px]">
                      {req.language} ({(req.language_confidence * 100).toFixed(0)}%)
                    </span>
                  </td>
                  <td className="p-3">
                    <span className="px-2 py-0.5 rounded font-bold text-[10px] bg-brand-500/20 text-brand-300 border border-brand-500/30">
                      {req.primary_category}
                    </span>
                    <div className="text-[10px] text-slate-500 mt-1 font-mono">
                      Conf: {(req.confidence * 100).toFixed(0)}%
                    </div>
                  </td>
                  <td className="p-3">
                    <div className="font-semibold text-slate-200">{req.ward_name || 'Unassigned'}</div>
                    <div className="text-[10px] text-slate-400 flex items-center gap-1 mt-0.5">
                      <MapPin className="w-3 h-3 text-emerald-400" />
                      <span>{req.address || (req.latitude ? `${req.latitude?.toFixed(4)}, ${req.longitude?.toFixed(4)}` : 'Unresolved')}</span>
                    </div>
                  </td>
                  <td className="p-3">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        req.status === 'RESOLVED'
                          ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                          : req.status === 'IN_PROGRESS'
                          ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                          : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                      }`}
                    >
                      {req.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* New Request Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-slate-100">Submit New Citizen Grievance</h3>
              <button
                onClick={() => setShowModal(false)}
                className="text-slate-400 hover:text-slate-200"
              >
                ✕
              </button>
            </div>
            <p className="text-xs text-slate-400">
              Submit text in English, Hindi, Marathi, or Hinglish. The real NLP pipeline will clean, classify, extract entities, geocode coordinates, and calculate dense embeddings.
            </p>

            <form onSubmit={handleCreateRequest} className="space-y-4">
              <textarea
                value={newText}
                onChange={(e) => setNewText(e.target.value)}
                placeholder="e.g. Waterlogging near school on Linking Road Bandra and garbage not collected..."
                rows={4}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-slate-100 focus:outline-none focus:border-brand-500"
              />

              {submitSuccess && (
                <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-lg text-xs font-semibold">
                  ✓ {submitSuccess}
                </div>
              )}

              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting || !newText.trim()}
                  className="flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-500 text-white rounded-lg text-xs font-semibold shadow-lg shadow-brand-500/20"
                >
                  <Send className="w-3.5 h-3.5" />
                  {submitting ? 'Running NLP Pipeline...' : 'Process & Ingest'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
