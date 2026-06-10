import React, { useEffect, useMemo, useState } from 'react';
import { Briefcase, TrendingUp, TrendingDown, Plus, Trash2, Eye, Clock, DollarSign, BarChart3, AlertTriangle, Sparkles, ArrowRight, Pencil } from 'lucide-react';
import { Button } from '../components/Button';
import { useNavigate } from 'react-router-dom';
import { usePortfolios } from '../context/PortfolioContext';
import { isKoreanTicker } from '../utils/helpers';
import { formatWeightPct, getConcentrationLabel, getPortfolioConcentrationSummary } from '../utils/portfolioConcentration';
import { previewPortfolio } from '../services/hedgemateApi';
import './MyPortfolios.css';

const riskConfig = {
  Low: { color: '#059669', bg: 'rgba(5,150,105,0.1)', label: '안정' },
  Moderate: { color: '#c084fc', bg: 'rgba(192,132,252,0.1)', label: '보통' },
  High: { color: '#f59e0b', bg: 'rgba(245,158,11,0.1)', label: '높음' },
};

const toFiniteNumber = (value, fallback = 0) => {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
};

const formatKrw = (value) => `₩${Math.round(toFiniteNumber(value)).toLocaleString()}`;

const formatPrice = (value, currency = 'KRW') => {
  const number = Number(value);
  if (!Number.isFinite(number)) return '-';
  if (currency === 'KRW') return `₩${Math.round(number).toLocaleString()}`;
  return `$${number.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

const signedPercent = (value) => {
  const number = toFiniteNumber(value);
  return `${number >= 0 ? '+' : ''}${number.toFixed(1)}%`;
};

const portfolioCostBasis = (portfolio) => toFiniteNumber(portfolio?.totalValue);

const assetCostBasisKrw = (asset, usdKrwRate) => {
  const qty = toFiniteNumber(asset.qty ?? asset.quantity);
  const cost = toFiniteNumber(asset.cost ?? asset.price ?? asset.unitPrice);
  if (!qty || !cost) return 0;
  const isUSD = asset.currency === 'USD' || (!asset.currency && !isKoreanTicker(asset.ticker));
  return qty * cost * (isUSD ? usdKrwRate : 1);
};

const buildPortfolioMetrics = (portfolio, previewState) => {
  const costBasis = portfolioCostBasis(portfolio);
  const preview = previewState?.data;
  const currentValue = Number.isFinite(Number(preview?.totalMarketValueKrw))
    ? Number(preview.totalMarketValueKrw)
    : costBasis;
  const profitKrw = currentValue - costBasis;
  const returnRate = costBasis > 0 ? (profitKrw / costBasis) * 100 : toFiniteNumber(portfolio.returnRate);
  const previewRows = new Map((preview?.rows || []).map((row) => [row.resolvedTicker || row.input, row]));
  const previewAssets = (preview?.rows || [])
    .filter((row) => row.resolvedTicker && row.resolvedTicker !== '__CASH__')
    .map((row) => ({
      ticker: row.resolvedTicker,
      name: row.displayName,
      weightPct: row.weightPct,
    }));
  const concentrationSummary = getPortfolioConcentrationSummary(
    previewAssets.length > 0 ? previewAssets : portfolio.assets,
  );
  const concentrationLabel = getConcentrationLabel(concentrationSummary);
  const analysisBlocked = preview?.canRunAnalysis === false || (!preview && concentrationSummary.blocksMultiAssetAnalysis);
  const analysisGuardMessage = analysisBlocked
    ? `${concentrationLabel || '비중 한도 초과'} · 분석 전 50% 이하 리밸런싱 필요`
    : concentrationSummary.isSingleAssetAnalysis
      ? `${concentrationLabel} · 단일자산 분석으로 진행 가능`
      : concentrationSummary.hasConcentration
        ? `${concentrationLabel} · 집중 포트폴리오`
        : '';

  return {
    costBasis,
    currentValue,
    profitKrw,
    returnRate,
    previewRows,
    isLive: Boolean(preview),
    isLoading: Boolean(previewState?.loading),
    error: previewState?.error || '',
    updatedAt: preview?.rows?.find((row) => row.priceAsOf)?.priceAsOf || '',
    canRunAnalysis: preview?.canRunAnalysis,
    analysisBlocked,
    analysisGuardMessage,
    previewErrors: preview?.errors || [],
    concentrationSummary,
  };
};

export const MyPortfolios = () => {
  const navigate = useNavigate();
  const { portfolios, deletePortfolio, usdKrwRate } = usePortfolios();
  const [expandedId, setExpandedId] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [previewById, setPreviewById] = useState({});

  useEffect(() => {
    if (portfolios.length === 0) {
      setPreviewById({});
      return undefined;
    }

    const controller = new AbortController();
    setPreviewById((prev) => {
      const next = {};
      portfolios.forEach((portfolio) => {
        next[portfolio.id] = {
          ...(prev[portfolio.id] || {}),
          loading: true,
          error: '',
        };
      });
      return next;
    });

    portfolios.forEach((portfolio) => {
      previewPortfolio(portfolio, {
        usdKrwRate,
        useLivePrices: true,
        signal: controller.signal,
        timeoutMs: 30 * 1000,
      })
        .then((preview) => {
          if (controller.signal.aborted) return;
          setPreviewById((prev) => ({
            ...prev,
            [portfolio.id]: {
              data: preview,
              loading: false,
              error: '',
            },
          }));
        })
        .catch((error) => {
          if (controller.signal.aborted || error.name === 'AbortError') return;
          setPreviewById((prev) => ({
            ...prev,
            [portfolio.id]: {
              ...(prev[portfolio.id] || {}),
              loading: false,
              error: error.message || '현재가 갱신 실패',
            },
          }));
        });
    });

    return () => controller.abort();
  }, [portfolios, usdKrwRate]);

  const handleDeleteClick = (e, id) => {
    e.stopPropagation();
    setDeletingId(id);
  };

  const confirmDelete = (e, id) => {
    e.stopPropagation();
    deletePortfolio(id);
    setDeletingId(null);
  };

  const cancelDelete = (e) => {
    e.stopPropagation();
    setDeletingId(null);
  };

  const handleView = (e, id) => {
    e.stopPropagation();
    navigate(`/report?portfolio=${encodeURIComponent(id)}`);
  };

  const handleEdit = (e, id) => {
    e.stopPropagation();
    navigate(`/register?edit=${encodeURIComponent(id)}`);
  };

  const toggleExpand = (id) => {
    if (deletingId) return; // Don't toggle while deleting
    setExpandedId(prev => prev === id ? null : id);
  };

  const metricsById = useMemo(() => {
    return Object.fromEntries(portfolios.map((portfolio) => [
      portfolio.id,
      buildPortfolioMetrics(portfolio, previewById[portfolio.id]),
    ]));
  }, [portfolios, previewById, usdKrwRate]);

  const totalAssetValue = portfolios.reduce((s, p) => s + (metricsById[p.id]?.currentValue ?? p.totalValue), 0);
  const avgReturn = portfolios.length > 0
    ? (portfolios.reduce((s, p) => s + (metricsById[p.id]?.returnRate ?? p.returnRate), 0) / portfolios.length)
    : 0;
  const newCount = portfolios.filter(p => p.status === 'new').length;

  return (
    <div className="my-portfolios-page">
      {/* Custom Delete Modal Overlay */}
      {deletingId && (
        <div className="modal-overlay" onClick={cancelDelete}>
          <div className="delete-modal" onClick={e => e.stopPropagation()}>
            <div className="modal-icon"><AlertTriangle size={32} className="text-red" /></div>
            <h3>포트폴리오 삭제</h3>
            <p>정말로 이 포트폴리오를 삭제하시겠습니까?<br/>삭제된 데이터는 복구할 수 없습니다.</p>
            <div className="modal-actions">
              <Button variant="secondary" onClick={cancelDelete}>취소</Button>
              <Button variant="primary" className="bg-red" onClick={(e) => confirmDelete(e, deletingId)}>삭제하기</Button>
            </div>
          </div>
        </div>
      )}

      {/* Flow Breadcrumb */}
      <div className="flow-breadcrumb mb-6">
        <span className="flow-crumb" onClick={() => navigate('/register')} style={{cursor:'pointer'}}>
          <span className="crumb-step">1</span> 포트폴리오 등록
        </span>
        <span className="flow-arrow">→</span>
        <span className="flow-crumb active">
          <span className="crumb-step">2</span> 내 포트폴리오
        </span>
        <span className="flow-arrow">→</span>
        <span className="flow-crumb" onClick={() => navigate('/report')} style={{cursor:'pointer'}}>
          <span className="crumb-step">3</span> 분석 리포트
        </span>
      </div>

      <div className="report-header mb-6">
        <span className="text-secondary text-xs font-semibold tracking-wider flex items-center gap-2">
          <span className="badge-purple">PORTFOLIO MANAGER</span>
          • Dashboard Overview
        </span>
        <h1 className="mt-2 mb-2">내 포트폴리오</h1>
        <p className="text-secondary text-sm">등록한 포트폴리오를 한눈에 관리하고 분석하세요.</p>
      </div>

      {/* Summary Bar */}
      <div className="portfolio-summary-bar mb-8">
        <div className="summary-stat">
          <div className="summary-icon"><Briefcase size={18} /></div>
          <div>
            <div className="text-xs text-secondary">총 포트폴리오</div>
            <div className="text-xl font-bold">{portfolios.length}개</div>
          </div>
        </div>
        <div className="summary-stat">
          <div className="summary-icon"><DollarSign size={18} /></div>
          <div>
            <div className="text-xs text-secondary">총 자산 규모</div>
            <div className="text-xl font-bold">{formatKrw(totalAssetValue)}</div>
          </div>
        </div>
        <div className="summary-stat">
          <div className="summary-icon"><BarChart3 size={18} /></div>
          <div>
            <div className="text-xs text-secondary">평균 수익률</div>
            <div className={`text-xl font-bold ${Number(avgReturn) >= 0 ? 'text-green' : 'text-red'}`}>
              {signedPercent(avgReturn)}
            </div>
          </div>
        </div>
        {newCount > 0 && (
          <div className="summary-stat new-highlight">
            <div className="summary-icon new-icon"><Sparkles size={18} /></div>
            <div>
              <div className="text-xs text-secondary">신규 등록</div>
              <div className="text-xl font-bold text-accent-light">{newCount}개</div>
            </div>
          </div>
        )}
        <div className="summary-stat">
          <Button variant="primary" className="text-sm" onClick={() => navigate('/register')}>
            <Plus size={16} /> 새 포트폴리오
          </Button>
        </div>
      </div>

      {/* Portfolio Cards Grid */}
      {portfolios.length === 0 ? (
        <div className="empty-state card-box">
          <Briefcase size={48} className="text-secondary" />
          <h3 className="mt-4">등록된 포트폴리오가 없습니다</h3>
          <p className="text-secondary text-sm mt-2">새 포트폴리오를 만들어 HedgeMate 분석을 시작하세요.</p>
          <Button variant="primary" className="mt-6" onClick={() => navigate('/register')}>
            <Plus size={16} /> 포트폴리오 만들기
          </Button>
        </div>
      ) : (
        <div className="portfolios-grid">
          {portfolios.map(p => {
            const risk = riskConfig[p.riskLevel] || riskConfig.Moderate;
            const metrics = metricsById[p.id] || buildPortfolioMetrics(p, null);
            const returnPositive = metrics.returnRate >= 0;
            const isExpanded = expandedId === p.id;
            const isNew = p.status === 'new';
            return (
              <div key={p.id} className={`portfolio-card ${isExpanded ? 'expanded' : ''} ${isNew ? 'is-new' : ''}`} onClick={() => toggleExpand(p.id)}>
                {/* Card Top Accent */}
                <div className="card-accent" style={{ background: isNew
                  ? 'linear-gradient(90deg, #c084fc, #e879f9)'
                  : `linear-gradient(90deg, ${risk.color}, var(--accent-light))`
                }} />

                <div className="portfolio-card-header">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold">{p.name}</h3>
                      {isNew && <span className="new-tag">NEW</span>}
                    </div>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs text-secondary flex items-center gap-1">
                        <Clock size={12} /> {p.createdAt}
                      </span>
                      <span className="portfolio-purpose-badge">{p.purpose}</span>
                    </div>
                  </div>
                  <div className="portfolio-return" style={{ color: returnPositive ? '#059669' : '#ef4444' }}>
                    {returnPositive ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
                    <span className="font-bold">{signedPercent(metrics.returnRate)}</span>
                  </div>
                </div>

                <div className="portfolio-card-body">
                  <div className="portfolio-stat-row">
                    <div className="portfolio-stat">
                      <span className="text-xs text-secondary">현재 평가액</span>
                      <span className="font-semibold">{formatKrw(metrics.currentValue)}</span>
                      {metrics.isLive && (
                        <span className={`portfolio-pnl ${metrics.profitKrw >= 0 ? 'text-green' : 'text-red'}`}>
                          {metrics.profitKrw >= 0 ? '+' : '-'}{formatKrw(Math.abs(metrics.profitKrw))}
                        </span>
                      )}
                    </div>
                    <div className="portfolio-stat">
                      <span className="text-xs text-secondary">종목 수</span>
                      <span className="font-semibold">{p.assets.length}개</span>
                    </div>
                    <div className="portfolio-stat">
                      <span className="text-xs text-secondary">위험 등급</span>
                      <span className="risk-badge" style={{ color: risk.color, background: risk.bg }}>
                        {p.riskLevel === 'High' && <AlertTriangle size={12} />}
                        {risk.label}
                      </span>
                    </div>
                  </div>

                  <div className="price-refresh-row mt-3">
                    {metrics.isLoading && <span>현재가 갱신 중...</span>}
                    {!metrics.isLoading && metrics.isLive && <span>현재가 반영됨{metrics.updatedAt ? ` · ${new Date(metrics.updatedAt).toLocaleDateString('ko-KR')}` : ''}</span>}
                    {!metrics.isLoading && metrics.error && <span className="text-red">현재가 갱신 실패 · 저장 기준 표시</span>}
                    <span>매입 기준 {formatKrw(metrics.costBasis)}</span>
                  </div>
                  {metrics.analysisGuardMessage && (
                    <div className={`portfolio-analysis-alert mt-3 ${metrics.analysisBlocked ? 'blocking' : ''}`}>
                      <AlertTriangle size={14} />
                      <span>{metrics.analysisGuardMessage}</span>
                    </div>
                  )}
                  {metrics.analysisBlocked && metrics.previewErrors.length > 0 && (
                    <div className="portfolio-analysis-detail mt-2">
                      {metrics.previewErrors.slice(0, 2).map((error) => (
                        <span key={error}>{error}</span>
                      ))}
                    </div>
                  )}

                  {/* Asset Weight Bar */}
                  <div className="weight-bar mt-4">
                    {p.assets.map((a, i) => (
                      <div
                        key={a.ticker}
                        className="weight-segment"
                        style={{
                          width: `${a.weightPct ?? a.weight}%`,
                          background: i === 0 ? 'var(--accent-light)' : i === 1 ? '#60a5fa' : '#34d399',
                        }}
                        title={`${a.ticker}: ${formatWeightPct(a.weightPct ?? a.weight)}`}
                      />
                    ))}
                  </div>
                  <div className="flex gap-3 mt-2">
                    {p.assets.map((a, i) => (
                      <span key={a.ticker} className="text-xs text-secondary flex items-center gap-1">
                        <span className="legend-dot" style={{
                          background: i === 0 ? 'var(--accent-light)' : i === 1 ? '#60a5fa' : '#34d399',
                        }} />
                        {a.ticker} {formatWeightPct(a.weightPct ?? a.weight)}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Expanded Detail */}
                {isExpanded && (
                  <div className="portfolio-card-detail">
                    <table className="detail-table">
                      <thead>
                        <tr>
                          <th>티커</th>
                          <th>종목명</th>
                          <th>수량</th>
                          <th>평단가</th>
                          <th>현재가</th>
                          <th>손익</th>
                          <th>비중</th>
                        </tr>
                      </thead>
                      <tbody>
                        {p.assets.map(a => {
                          const isUSD = a.currency === 'USD' || (!a.currency && !isKoreanTicker(a.ticker));
                          const previewRow = metrics.previewRows.get(a.ticker);
                          const costBasis = assetCostBasisKrw(a, usdKrwRate);
                          const currentValue = toFiniteNumber(previewRow?.marketValueKrw, costBasis);
                          const assetProfit = currentValue - costBasis;
                          const assetReturn = costBasis > 0 ? (assetProfit / costBasis) * 100 : 0;
                          return (
                            <tr key={a.ticker}>
                              <td className="font-semibold text-accent-light">{a.ticker}</td>
                              <td>{a.name}</td>
                              <td>{a.qty}</td>
                              <td>{isUSD ? `$${a.cost.toLocaleString()}` : `₩${a.cost.toLocaleString()}`}</td>
                              <td>
                                {formatPrice(previewRow?.latestPrice, previewRow?.currency || a.currency)}
                                {previewRow?.priceAsOf && <span className="detail-subtext">{new Date(previewRow.priceAsOf).toLocaleDateString('ko-KR')}</span>}
                              </td>
                              <td className={assetProfit >= 0 ? 'text-green' : 'text-red'}>
                                {assetProfit >= 0 ? '+' : '-'}{formatKrw(Math.abs(assetProfit))}
                                <span className="detail-subtext">{signedPercent(assetReturn)}</span>
                              </td>
                              <td>{formatWeightPct(a.weightPct ?? a.weight)}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                    <div className="flex gap-3 mt-4">
                      <Button variant="primary" className="flex-1 text-sm" onClick={(e) => handleView(e, p.id)}>
                        <Eye size={14} /> 분석 리포트 보기 <ArrowRight size={12} />
                      </Button>
                      <Button variant="secondary" className="text-sm" onClick={(e) => handleEdit(e, p.id)}>
                        <Pencil size={14} /> 수정
                      </Button>
                      <Button variant="outline" className="text-sm text-danger btn-delete" onClick={(e) => handleDeleteClick(e, p.id)}>
                        <Trash2 size={14} /> 삭제
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
