import React from 'react';
import { Activity, FilePlus, TrendingUp, BarChart3, Settings, LogOut, Briefcase, ChevronRight, FileBarChart2, Zap } from 'lucide-react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { usePortfolios } from '../context/PortfolioContext';
import { useUserProfile } from '../hooks/useUserProfile';
import './Sidebar.css';

export const Sidebar = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { portfolios } = usePortfolios();
  const { profile } = useUserProfile();

  const newCount = portfolios.filter(p => p.status === 'new').length;
  const userInitial = profile.name?.trim()?.charAt(0)?.toUpperCase() || 'U';

  const portfolioFlowItems = [
    { icon: <FilePlus size={18} />, label: '포트폴리오 등록', path: '/register', step: 1, desc: '자산 입력' },
    { icon: <Briefcase size={18} />, label: '내 포트폴리오', path: '/portfolios', step: 2, desc: '보관 & 관리', badge: newCount > 0 ? newCount : null },
    { icon: <FileBarChart2 size={18} />, label: '분석 리포트', path: '/report', step: 3, desc: '개선 효과' },
  ];

  const marketRiskItems = [
    { icon: <Activity size={18} />, label: '현재시장국면', path: '/market-state' },
    { icon: <Zap size={18} />, label: '위기 시뮬레이션', path: '/stress-test' },
  ];

  const analysisItems = [
    { icon: <TrendingUp size={18} />, label: '단일 종목 탐색', path: '/analysis' },
    { icon: <BarChart3 size={18} />, label: '종목 리스크', path: '/sensitivity' },
  ];

  const isInPortfolioFlow = ['/register', '/portfolios', '/report'].includes(location.pathname);

  return (
    <aside className="sidebar">
      <div className="sidebar-brand text-gradient">
        HedgeMate
      </div>
      <div className="sidebar-header">
        <h2 className="text-gradient">HedgeMate</h2>
        <p>DEFENSIVE ENGINE</p>
      </div>

      <nav className="sidebar-nav">
        {/* Portfolio Flow Group */}
        <div className="nav-group">
          <div className="nav-group-label">
            <span className="nav-group-dot"></span>
            포트폴리오 워크플로우
          </div>
          <div className={`nav-flow-container ${isInPortfolioFlow ? 'active-flow' : ''}`}>
            {portfolioFlowItems.map((item, index) => (
              <React.Fragment key={item.path}>
                <Link
                  to={item.path}
                  className={`sidebar-link flow-link ${location.pathname === item.path ? 'active' : ''}`}
                >
                  <span className="flow-step-indicator">
                    <span className="flow-step-number">{item.step}</span>
                  </span>
                  <div className="flow-link-content">
                    <span className="flow-link-label">{item.label}</span>
                    <span className="flow-link-desc">{item.desc}</span>
                  </div>
                  {item.badge && (
                    <span className="flow-badge">{item.badge}</span>
                  )}
                </Link>
                {index < portfolioFlowItems.length - 1 && (
                  <div className="flow-connector">
                    <ChevronRight size={10} />
                  </div>
                )}
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* Divider */}
        <div className="nav-divider"></div>

        {/* Market Risk Diagnostics */}
        <div className="nav-group market-risk-group">
          <div className="nav-group-label market-risk-label">
            <span className="nav-group-dot market-risk-dot"></span>
            시장 리스크 진단
          </div>
          {marketRiskItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`sidebar-link market-risk-link ${location.pathname === item.path ? 'active' : ''}`}
            >
              {item.icon}
              <span>{item.label}</span>
            </Link>
          ))}
        </div>

        <div className="nav-divider"></div>

        {/* Analysis Tools */}
        <div className="nav-group">
          <div className="nav-group-label">
            <span className="nav-group-dot analysis-dot"></span>
            분석 도구
          </div>
          {analysisItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`sidebar-link ${location.pathname === item.path ? 'active' : ''}`}
            >
              {item.icon}
              <span>{item.label}</span>
            </Link>
          ))}
        </div>
      </nav>

      <div className="sidebar-bottom">
        <div className="user-badge">
          <div className="user-avatar">{userInitial}</div>
          <div>
            <div className="text-sm font-medium">{profile.name}</div>
            <div className="text-xs text-secondary">{profile.email}</div>
          </div>
        </div>
        <button className="bottom-link" onClick={() => navigate('/settings')}>
          <Settings size={16} /> <span>Settings</span>
        </button>
        <button className="bottom-link text-danger mt-2" onClick={() => navigate('/', { replace: true })}>
          <LogOut size={16} /> <span>Logout</span>
        </button>
      </div>
    </aside>
  );
};
