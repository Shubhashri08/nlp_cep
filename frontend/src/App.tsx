import React, { Suspense, lazy, useState } from 'react';
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Navbar } from './components/layout/Navbar';
import { Sidebar } from './components/layout/Sidebar';
import { ErrorState, Loading } from './components/ui';
import type { Role } from './types';
import { Login } from './pages/Login';

const Dashboard = lazy(() => import('./pages/Dashboard'));
const GISExplorer = lazy(() => import('./pages/GISExplorer'));
const CitizenFeedback = lazy(() => import('./pages/CitizenFeedback'));
const NLPAnalytics = lazy(() => import('./pages/NLPAnalytics'));
const DocumentAnalysis = lazy(() => import('./pages/DocumentAnalysis'));
const InfrastructureGaps = lazy(() => import('./pages/InfrastructureGaps'));
const Demographics = lazy(() => import('./pages/Demographics'));
const UrbanGrowth = lazy(() => import('./pages/UrbanGrowth'));
const Predictions = lazy(() => import('./pages/Predictions'));
const ScenarioStudio = lazy(() => import('./pages/ScenarioStudio'));
const Recommendations = lazy(() => import('./pages/Recommendations'));
const AIAssistant = lazy(() => import('./pages/AIAssistant'));
const DataSources = lazy(() => import('./pages/DataSources'));
const ModelRegistryPage = lazy(() => import('./pages/ModelRegistryPage'));
const AuditAdmin = lazy(() => import('./pages/AuditAdmin'));

const RoleGate: React.FC<{ roles: Role[]; children: React.ReactNode }> = ({ roles, children }) => {
  const { hasRole } = useAuth();
  return hasRole(...roles) ? <>{children}</> : <ErrorState message="Your role does not have access to this page." />;
};

class PageBoundary extends React.Component<{ children: React.ReactNode; resetKey: string }, { error: Error | null }> {
  state = { error: null as Error | null };
  static getDerivedStateFromError(error: Error) { return { error }; }
  componentDidUpdate(prev: { resetKey: string }) { if (prev.resetKey !== this.props.resetKey && this.state.error) this.setState({ error: null }); }
  render() {
    return this.state.error ? <ErrorState message={`This page failed to render: ${this.state.error.message}`} /> : this.props.children;
  }
}

const ProtectedLayout: React.FC = () => {
  const { user, isLoading } = useAuth();
  const [menu, setMenu] = useState(false);
  const location = useLocation();
  if (isLoading) return <div className="min-h-screen grid place-items-center"><Loading label="Restoring session…" /></div>;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  const fullBleed = location.pathname.startsWith('/gis');
  return (
    <div className="min-h-screen flex">
      <Sidebar open={menu} onClose={() => setMenu(false)} />
      <div className="flex-1 min-w-0 flex flex-col">
        <Navbar onMenu={() => setMenu(true)} />
        <main className={fullBleed ? 'flex-1 min-h-0' : 'flex-1 px-4 py-6 md:px-8 md:py-8 max-w-[1400px] w-full mx-auto'}>
          <PageBoundary resetKey={location.pathname}>
            <Suspense fallback={<Loading />}>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/gis" element={<GISExplorer />} />
                <Route path="/citizen-feedback" element={<CitizenFeedback />} />
                <Route path="/nlp-analytics" element={<NLPAnalytics />} />
                <Route path="/documents" element={<DocumentAnalysis />} />
                <Route path="/infrastructure-gaps" element={<InfrastructureGaps />} />
                <Route path="/demographics" element={<Demographics />} />
                <Route path="/urban-growth" element={<UrbanGrowth />} />
                <Route path="/predictions" element={<Predictions />} />
                <Route path="/scenario-studio" element={<ScenarioStudio />} />
                <Route path="/recommendations" element={<Recommendations />} />
                <Route path="/ai-assistant" element={<AIAssistant />} />
                <Route path="/data-sources" element={<DataSources />} />
                <Route path="/model-registry" element={<ModelRegistryPage />} />
                <Route path="/audit-admin" element={<RoleGate roles={[]}><AuditAdmin /></RoleGate>} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Suspense>
          </PageBoundary>
        </main>
      </div>
    </div>
  );
};

const LoginRoute: React.FC = () => {
  const { user, isLoading } = useAuth();
  if (isLoading) return <div className="min-h-screen grid place-items-center"><Loading /></div>;
  return user ? <Navigate to="/" replace /> : <Login />;
};

export const App: React.FC = () => (
  <AuthProvider>
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginRoute />} />
        <Route path="/*" element={<ProtectedLayout />} />
      </Routes>
    </BrowserRouter>
  </AuthProvider>
);
