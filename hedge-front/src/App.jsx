import React, { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import { PortfolioProvider, usePortfolios } from './context/PortfolioContext';

const namedPage = (loader, exportName) => lazy(() => loader().then((module) => ({ default: module[exportName] })));

const PortfolioRegistration = namedPage(() => import('./pages/PortfolioRegistration'), 'PortfolioRegistration');
const ImprovementReport = namedPage(() => import('./pages/ImprovementReport'), 'ImprovementReport');
const AssetSensitivity = namedPage(() => import('./pages/AssetSensitivity'), 'AssetSensitivity');
const MarketStateDashboard = namedPage(() => import('./pages/MarketStateDashboard'), 'MarketStateDashboard');
const Settings = namedPage(() => import('./pages/Settings'), 'Settings');
const MyPortfolios = namedPage(() => import('./pages/MyPortfolios'), 'MyPortfolios');
const StressTest = namedPage(() => import('./pages/StressTest'), 'StressTest');
const Onboarding = namedPage(() => import('./pages/Onboarding'), 'Onboarding');

const RequireAuth = ({ children }) => {
  const { currentUser, authLoading } = usePortfolios();
  if (authLoading) {
    return <div className="page-content">Loading session...</div>;
  }
  if (!currentUser) {
    return <Navigate to="/" replace />;
  }
  return children;
};

const RootRoute = () => {
  const { currentUser, authLoading } = usePortfolios();
  if (authLoading) {
    return <div className="page-content">Loading session...</div>;
  }
  if (currentUser) {
    return <Navigate to="/portfolios" replace />;
  }
  return <Onboarding />;
};

function App() {
  return (
    <PortfolioProvider>
      <Router>
        <Suspense fallback={<div className="page-content">로딩 중...</div>}>
          <Routes>
            <Route path="/" element={<RootRoute />} />
            <Route path="/*" element={
              <RequireAuth>
                <Layout>
                  <Routes>
                    <Route path="/register" element={<PortfolioRegistration />} />
                    <Route path="/report" element={<ImprovementReport />} />
                    <Route path="/analysis" element={<Navigate to="/report" replace />} />
                    <Route path="/sensitivity" element={<AssetSensitivity />} />
                    <Route path="/market-state" element={<MarketStateDashboard />} />
                    <Route path="/strategy" element={<Navigate to="/report" replace />} />
                    <Route path="/settings" element={<Settings />} />
                    <Route path="/portfolios" element={<MyPortfolios />} />
                    <Route path="/stress-test" element={<StressTest />} />
                    <Route path="/stress" element={<StressTest />} />
                  </Routes>
                </Layout>
              </RequireAuth>
            } />
          </Routes>
        </Suspense>
      </Router>
    </PortfolioProvider>
  );
}

export default App;
