import React, { useState } from 'react';
import { UserPlus } from 'lucide-react';
import { api } from '../api/client';
import { useApi } from '../hooks/useApi';
import { AsyncBlock, Badge, Card, PageHeader, Select } from '../components/ui';
import type { Role } from '../types';
import { ROLE_LABEL } from '../components/layout/nav';

const AuditAdmin: React.FC = () => {
  const logs = useApi(() => api.audit(200), []);
  const users = useApi(() => api.users(), []);
  const [form, setForm] = useState({ email: '', full_name: '', password: '', role: 'VIEWER' as Role });
  const [msg, setMsg] = useState<string | null>(null);

  const create = async (e: React.FormEvent) => {
    e.preventDefault(); setMsg(null);
    try { await api.createUser(form); setMsg(`Created ${form.email}`); setForm({ email: '', full_name: '', password: '', role: 'VIEWER' }); users.reload(); logs.reload(); }
    catch (err) { setMsg((err as Error).message); }
  };

  return (
    <div className="animate-fade-in">
      <PageHeader eyebrow="Administration" title="Audit Trail & Users" subtitle="All logins, data changes, model retraining and assistant queries are recorded with user and IP address." />
      <div className="grid lg:grid-cols-[1fr_360px] gap-6">
        <Card title="Audit log" bodyClass="p-0 pt-3">
          <AsyncBlock state={logs} isEmpty={(d) => d.length === 0} empty="No audit events.">{(rows) => (
            <div className="max-h-[70vh] overflow-y-auto"><table className="table-base">
              <thead><tr><th>Time</th><th>User</th><th>Action</th><th>Resource</th><th>Details</th></tr></thead>
              <tbody>{rows.map((l) => (
                <tr key={l.id}><td className="text-xs whitespace-nowrap text-muted">{new Date(l.timestamp).toLocaleString('en-IN')}</td>
                  <td className="text-xs">{l.user_email ?? 'system'}</td><td><Badge color="#3A5A94">{l.action}</Badge></td>
                  <td className="text-xs">{l.resource_type}{l.resource_id ? ` #${l.resource_id}` : ''}</td>
                  <td className="text-[11px] font-mono text-muted max-w-xs truncate" title={JSON.stringify(l.details)}>{l.details ? JSON.stringify(l.details) : ''}</td></tr>
              ))}</tbody>
            </table></div>
          )}</AsyncBlock>
        </Card>
        <div className="space-y-6">
          <Card title="Create user">
            <form className="space-y-2" onSubmit={create}>
              <input className="input" placeholder="Full name" required value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
              <input className="input" type="email" placeholder="Email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
              <input className="input" type="password" placeholder="Password (min 8)" minLength={8} required value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
              <Select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as Role })} aria-label="Role">
                {(Object.keys(ROLE_LABEL) as Role[]).map((r) => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}
              </Select>
              <button className="btn-primary w-full"><UserPlus className="h-4 w-4" />Create</button>
              {msg && <p className="text-xs text-police">{msg}</p>}
            </form>
          </Card>
          <Card title="Users" bodyClass="p-0 pt-2">
            <AsyncBlock state={users}>{(list) => (
              <ul className="divide-y divide-line">{list.map((u) => (
                <li key={u.id} className="px-5 py-2.5"><div className="text-sm font-semibold text-police">{u.full_name}</div>
                  <div className="text-[11px] text-muted">{u.email} · {ROLE_LABEL[u.role]}{u.is_active ? '' : ' · inactive'}</div></li>
              ))}</ul>
            )}</AsyncBlock>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default AuditAdmin;
