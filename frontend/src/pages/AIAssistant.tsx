import React, { useState } from 'react';
import { api } from '../api/client';
import { AssistantQueryResponse } from '../types';
import {
  Sparkles, Send, Database, ArrowRight, ShieldCheck, CheckCircle2,
  Terminal, HelpCircle
} from 'lucide-react';

interface ChatMessage {
  sender: 'user' | 'assistant';
  text: string;
  responseObj?: AssistantQueryResponse;
}

const SAMPLE_PROMPTS = [
  "Which wards currently show the highest concentration of drainage-related complaints?",
  "What are the most critical infrastructure gaps across the city?",
  "What is the demographic profile and priority score for Kurla (Ward L)?",
  "What is the predicted service demand forecast over the next 12 months?"
];

export const AIAssistant: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      sender: 'assistant',
      text: "Hello, I am the Grounded Urban Planning Decision Support Assistant. I formulate answers strictly from verified municipal records, PostGIS layers, ML models, and infrastructure databases."
    }
  ]);
  const [inputText, setInputText] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);

  const handleSend = async (queryText?: string) => {
    const q = queryText || inputText;
    if (!q.trim()) return;

    const userMsg: ChatMessage = { sender: 'user', text: q };
    setMessages(prev => [...prev, userMsg]);
    setInputText('');
    setLoading(true);

    try {
      const res = await api.queryAssistant(q);
      const assistantMsg: ChatMessage = {
        sender: 'assistant',
        text: res.grounded_answer,
        responseObj: res
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (err: any) {
      setMessages(prev => [
        ...prev,
        {
          sender: 'assistant',
          text: `Error retrieving data: ${err.message || 'Service unavailable'}`
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-[calc(100vh-6.5rem)] flex flex-col space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between bg-slate-900 border border-slate-800 p-4 rounded-xl">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-brand-600/20 border border-brand-500/30 flex items-center justify-center text-brand-400">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-100">Grounded AI Urban Planning Assistant</h2>
            <p className="text-[11px] text-slate-400">Strict Hallucination Control • RAG Retrieval from Municipal DB & GIS</p>
          </div>
        </div>
        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
          ZERO-FABRICATION GUARANTEE
        </span>
      </div>

      {/* Chat Messages Area */}
      <div className="flex-1 bg-slate-900 border border-slate-800 rounded-xl p-4 overflow-y-auto space-y-4 text-xs">
        {messages.map((m, idx) => (
          <div
            key={idx}
            className={`flex ${m.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-2xl rounded-xl p-4 space-y-3 ${
                m.sender === 'user'
                  ? 'bg-brand-600 text-white rounded-br-none shadow-md'
                  : 'bg-slate-950 border border-slate-800 text-slate-200 rounded-bl-none shadow-sm'
              }`}
            >
              <div className="leading-relaxed font-sans text-xs sm:text-[13px]">
                {m.text}
              </div>

              {/* Grounded Evidence Citations & Structured Findings */}
              {m.responseObj && (
                <div className="pt-3 border-t border-slate-800 space-y-3">
                  {/* Evidence Sources */}
                  {m.responseObj.evidence_sources.length > 0 && (
                    <div className="space-y-1.5">
                      <span className="text-[10px] font-bold text-slate-400 flex items-center gap-1.5">
                        <Database className="w-3.5 h-3.5 text-brand-400" />
                        Verified Data Citations & SQL Queries:
                      </span>
                      {m.responseObj.evidence_sources.map((src, sIdx) => (
                        <div key={sIdx} className="p-2 bg-slate-900 rounded border border-slate-800 space-y-1 font-mono text-[10px]">
                          <div className="text-emerald-400 font-semibold">{src.description}</div>
                          <div className="text-slate-400 truncate">Query: {src.query_executed}</div>
                          <div className="text-slate-500 text-[9px]">Table: {src.table_name}</div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Suggested Follow-ups */}
                  {m.responseObj.suggested_actions.length > 0 && (
                    <div className="space-y-1">
                      <span className="text-[10px] font-bold text-slate-400">Suggested Actionable Next Steps:</span>
                      <div className="flex flex-wrap gap-1.5">
                        {m.responseObj.suggested_actions.map((act, aIdx) => (
                          <button
                            key={aIdx}
                            onClick={() => handleSend(act)}
                            className="px-2 py-1 bg-slate-900 hover:bg-slate-800 text-brand-300 rounded text-[10px] border border-slate-700 transition"
                          >
                            &rarr; {act}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-slate-950 border border-slate-800 p-3 rounded-xl rounded-bl-none text-xs text-slate-400 flex items-center gap-2">
              <div className="animate-spin rounded-full h-3.5 w-3.5 border-b-2 border-brand-500"></div>
              <span>Querying municipal database & synthesizing grounded evidence...</span>
            </div>
          </div>
        )}
      </div>

      {/* Suggested Quick Prompt Chips */}
      <div className="flex flex-wrap gap-2 text-xs">
        <span className="text-slate-500 text-[11px] self-center">Suggested:</span>
        {SAMPLE_PROMPTS.map((p, i) => (
          <button
            key={i}
            onClick={() => handleSend(p)}
            className="px-2.5 py-1 bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 rounded-lg text-[11px] truncate max-w-[280px] transition"
          >
            {p}
          </button>
        ))}
      </div>

      {/* Input Bar */}
      <form
        onSubmit={(e) => { e.preventDefault(); handleSend(); }}
        className="flex gap-2 bg-slate-900 border border-slate-800 p-2 rounded-xl"
      >
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="Ask a municipal planning question..."
          className="flex-1 bg-transparent px-3 text-xs text-slate-100 placeholder-slate-500 focus:outline-none"
        />
        <button
          type="submit"
          disabled={loading || !inputText.trim()}
          className="px-4 py-2 bg-brand-600 hover:bg-brand-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 shadow-md shadow-brand-500/20 transition"
        >
          <Send className="w-3.5 h-3.5" />
          <span>Ask</span>
        </button>
      </form>
    </div>
  );
};
