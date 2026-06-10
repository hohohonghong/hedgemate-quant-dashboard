import React, { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import { PortfolioProvider } from './context/PortfolioContext';

const namedPage = (loader, exportName) => lazy(() => loader().then((module) => ({ default: module[exportName] })));

const PortfolioRegistration = namedPage(() => import('./pages/PortfolioRegistration'), 'PortfolioRegistration');
const ImprovementReport = namedPage(() => import('./pages/ImprovementReport'), 'ImprovementReport');
const AssetAnalysis = namedPage(() => import('./pages/AssetAnalysis'), 'AssetAnalysis');
const AssetSensitivity = namedPage(() => import('./pages/AssetSensitivity'), 'AssetSensitivity');
const MarketStateDashboard = namedPage(() => import('./pages/MarketStateDashboard'), 'MarketStateDashboard');
const Settings = namedPage(() => import('./pages/Settings'), 'Settings');
const MyPortfolios = namedPage(() => import('./pages/MyPortfolios'), 'MyPortfolios');
const StressTest = namedPage(() => import('./pages/StressTest'), 'StressTest');
const Onboarding = namedPage(() => import('./pages/Onboarding'), 'Onboarding');

function App() {
  return (
    <PortfolioProvider>
      <Router>
        <Suspense fallback={<div className="page-content">로딩 중...</div>}>
          <Routes>
            <Route path="/" element={<Onboarding />} />
            <Route path="/*" element={
              <Layout>
                <Routes>
                  <Route path="/register" element={<PortfolioRegistration />} />
                  <Route path="/report" element={<ImprovementReport />} />
                  <Route path="/analysis" element={<AssetAnalysis />} />
                  <Route path="/sensitivity" element={<AssetSensitivity />} />
                  <Route path="/market-state" element={<MarketStateDashboard />} />
                  <Route path="/strategy" element={<Navigate to="/report" replace />} />
                  <Route path="/settings" element={<Settings />} />
                  <Route path="/portfolios" element={<MyPortfolios />} />
                  <Route path="/stress-test" element={<StressTest />} />
                  <Route path="/stress" element={<StressTest />} />
                </Routes>
              </Layout>
            } />
          </Routes>
        </Suspense>
      </Router>
    </PortfolioProvider>
  );
}

export default App;
