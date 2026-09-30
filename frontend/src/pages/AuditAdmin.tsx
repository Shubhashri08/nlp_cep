import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { ShieldAlert, Users, Activity, Lock, Terminal } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const AuditAdmin: React.FC = () => {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const { user, role } = useAuth();

  useEffect(() => {
    async function loadLogs() {
      try {
        setLoading(true);
        const data = await api.getAuditLogs(50);
        setLogs(data);
      } catch (err) {
        console.error('Failed to load audit logs', err);
      } finally {
        setLoading(false);
      }
    }
    loadLogs();
  }, []);

  return (
    <div className="space-y-6 pb-12">
      <div>
        <h2 className="text-2xl font-bold text-slate-100">Municipal Security & Audit Log</h2>
        <p className="text-sm text-slate-400">
          Role-Based Access Control (RBAC) monitor, immutable decision audit trail, and security access logs.
        </p>
      </div>

      {/* Active User Privileges */}
      <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl space-y-3">
        <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
          <Lock className="w-4 h-4 text-brand-400" />
          Active Municipal Session Privileges
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
          <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
            <span className="text-slate-500">Authenticated Officer:</span>
            <div className="font-bold text-slate-100 mt-0.5">{user?.full_name}</div>
          </div>
          <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
            <span className="text-slate-500">Assigned Role:</span>
            <div className="font-bold text-brand-400 mt-0.5">{role}</div>
          </div>
          <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
            <span className="text-slate-500">Access Scope:</span>
            <div className="font-bold text-emerald-400 mt-0.5">
              {role === 'ADMIN' ? 'Full System & User Governance' : (role === 'PLANNER' ? 'Intervention & Analytics' : 'Read-Only Municipal Views')}
            </div>
          </div>
        </div>
      </div>

      {/* Audit Log Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        <div className="p-4 border-b border-slate-800 bg-slate-950/40">
          <h3 className="text-sm font-bold text-slate-200">Immutable System Action Audit Trail</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-950 text-slate-400 font-semibold border-b border-slate-800">
              <tr>
                <th className="p-3">TIMESTAMP</th>
                <th className="p-3">ACTION</th>
                <th className="p-3">RESOURCE TYPE</th>
                <th className="p-3">RESOURCE ID</th>
                <th className="p-3">DETAILS</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-slate-300">
              {logs.map((l) => (
                <tr key={l.id} className="hover:bg-slate-800/40 transition">
                  <td className="p-3 text-slate-400">{new Date(l.timestamp).toLocaleString()}</td>
                  <td className="p-3 font-bold text-brand-400">{l.action}</td>
                  <td className="p-3 text-slate-300">{l.resource_type}</td>
                  <td className="p-3 text-slate-400">{l.resource_id}</td>
                  <td className="p-3 text-slate-400 truncate max-w-xs">{JSON.stringify(l.details)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
