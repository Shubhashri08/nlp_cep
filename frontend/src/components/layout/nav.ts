import {
  BarChart3, Bot, Brain, Building2, ClipboardList, Database, FileText, Gauge, Layers, LineChart, Map, MessageSquareText,
  Satellite, ShieldCheck, Sparkles, Users,
} from 'lucide-react';
import type { Role } from '../../types';

export interface NavItem { to: string; label: string; icon: typeof Map; roles?: Role[]; }
export interface NavGroup { title: string; items: NavItem[]; }

export const NAV: NavGroup[] = [
  { title: 'Overview', items: [
    { to: '/', label: 'Dashboard', icon: Gauge },
    { to: '/gis', label: 'GIS Explorer', icon: Map },
    { to: '/ai-assistant', label: 'AI Assistant', icon: Bot },
  ] },
  { title: 'Citizen & Documents', items: [
    { to: '/citizen-feedback', label: 'Citizen Feedback', icon: MessageSquareText },
    { to: '/nlp-analytics', label: 'Text Analyzer', icon: Brain },
    { to: '/documents', label: 'Planning Documents', icon: FileText },
  ] },
  { title: 'Analysis', items: [
    { to: '/infrastructure-gaps', label: 'Infrastructure Gaps', icon: Building2 },
    { to: '/demographics', label: 'Demographics & Land Use', icon: Users },
    { to: '/urban-growth', label: 'Urban Growth', icon: Satellite },
    { to: '/predictions', label: 'Demand Forecasts', icon: LineChart },
  ] },
  { title: 'Decisions', items: [
    { to: '/scenario-studio', label: 'Scenario Studio', icon: Layers },
    { to: '/recommendations', label: 'Recommendations', icon: Sparkles },
  ] },
  { title: 'Governance', items: [
    { to: '/data-sources', label: 'Data Sources', icon: Database },
    { to: '/model-registry', label: 'Model Registry', icon: BarChart3 },
    { to: '/audit-admin', label: 'Audit & Users', icon: ShieldCheck, roles: ['ADMIN'] },
  ] },
];

export const ROLE_LABEL: Record<Role, string> = { ADMIN: 'Administrator', PLANNER: 'Town Planner', ANALYST: 'Data Analyst', VIEWER: 'Viewer' };
export const ROLE_ICON = ClipboardList;
