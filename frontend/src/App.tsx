import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Navbar } from './components/layout/Navbar';
import { Sidebar } from './components/layout/Sidebar';

import { Dashboard } from './pages/Dashboard';
import { GISExplorer } from './pages/GISExplorer';
import { CitizenFeedback } from './pages/CitizenFeedback';
import { NLPAnalytics } from './pages/NLPAnalytics';
import { InfrastructureGaps } from './pages/InfrastructureGaps';
import { Demographics } from './pages/Demographics';
import { UrbanGrowth } from './pages/UrbanGrowth';
import { Predictions } from './pages/Predictions';
import { ScenarioStudio } from './pages/ScenarioStudio';
import { Recommendations } from './pages/Recommendations';
import { AIAssistant } from './pages/AIAssistant';
import { DataSources } from './pages/DataSources';
import { ModelRegistryPage } from './pages/ModelRegistryPage';
import { AuditAdmin } from './pages/AuditAdmin';
import { Login } from './pages/Login';

const ProtectedLayout: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-brand-500"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col font-sans">
      <Navbar />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 p-6 overflow-y-auto max-w-7xl mx-auto w-full">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/gis" element={<GISExplorer />} />
            <Route path="/citizen-feedback" element={<CitizenFeedback />} />
            <Route path="/nlp-analytics" element={<NLPAnalytics />} />
            <Route path="/infrastructure-gaps" element={<InfrastructureGaps />} />
            <Route path="/demographics" element={<Demographics />} />
            <Route path="/urban-growth" element={<UrbanGrowth />} />
            <Route path="/predictions" element={<Predictions />} />
            <Route path="/scenario-studio" element={<ScenarioStudio />} />
            <Route path="/recommendations" element={<Recommendations />} />
            <Route path="/ai-assistant" element={<AIAssistant />} />
            <Route path="/data-sources" element={<DataSources />} />
            <Route path="/model-registry" element={<ModelRegistryPage />} />
            <Route path="/audit-admin" element={<AuditAdmin />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/*" element={<ProtectedLayout />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
};
