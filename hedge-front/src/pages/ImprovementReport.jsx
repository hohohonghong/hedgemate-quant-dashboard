import React, { useEffect, useMemo, useState } from 'react';
import { Shield, Rocket, ChevronDown, ChevronUp, Briefcase, AlertCircle, ArrowRight, Loader2 } from 'lucide-react';
import { Button } from '../components/Button';
import { useLocation, useNavigate } from 'react-router-dom';
import { usePortfolios } from '../context/PortfolioContext';
import { getAssets, getHedgeMateStatus, getProductDashboard, pollRunStatus, previewPortfolio, runPortfolioAnalysis, toBackendPortfolioRows } from '../services/hedgemateApi';
import { METRIC_DEFINITIONS, formatMetricDelta, formatMetricValue, toHedgeMateViewModel } from '../services/hedgemateViewModel';
import { ASSET_DATABASE, normalizeTickerSymbol } from '../utils/helpers';
import {
  getStoredAnalysisRunForPortfolio,
  persistAnalysisRunForPortfolio,
  persistReportPortfolioId,
  portfolioRunKey,
  resolveReportPortfolioSelection,
} from '../services/reportPersistence';
import './ImprovementReport.css';

const metricKeys = ['cvar', 'mdd', 'beta', 'stress', 'sharpe'];
const ASSET_SEGMENT_COLORS = ['#38bdf8', '#a78bfa', '#34d399', '#fbbf24', '#fb7185', '#60a5fa'];

const getTickerColor = (ticker = '') => {
  const key = String(ticker).trim().toUpperCase() || 'ASSET';
  let hash = 0;
  for (let index = 0; index < key.length; index += 1) {
    hash = ((hash << 5) - hash) + key.charCodeAt(index);
    hash |= 0;
  }
  return ASSET_SEGMENT_COLORS[Math.abs(hash) % ASSET_SEGMENT_COLORS.length];
};

const cleanActionLabel = (label = '') => String(label)
  .replace(/검토 액션/g, '조정안')
  .replace(/추가 액션/g, '추가 조정안')
  .replace(/NO ACTION/g, '조정안 없음');

const formatDateTime = (value) => {
  if (!value) return '백엔드 산출물 기준 없음';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('ko-KR');
};

const formatKstDateTime = (value) => {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('ko-KR', {
    timeZone: 'Asia/Seoul',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const getImproveText = (portfolioData, type, metricKey) => {
  if (!portfolioData || type === 'base') return '0.00% 기준';
  return formatMetricDelta(portfolioData.base[metricKey], portfolioData[type][metricKey], metricKey);
};

const calcBarWidth = (portfolioData, type, metricKey) => {
  if (!portfolioData) return 0;
  const value = Math.abs(Number(portfolioData[type]?.[metricKey] || 0));
  const base = Math.abs(Number(portfolioData.base?.[metricKey] || 0));
  if (metricKey === 'sharpe') return Math.min(100, (value / 2.5) * 100);
  if (!base) return value ? 50 : 0;
  return Math.min(100, (value / (base * 1.15)) * 100);
};

const actionTypeLabel = (type) => {
  if (type === 'TRIM_AND_HEDGE') return '비중 축소 + 헷지';
  if (type === 'ADD_HEDGE') return '헷지 추가 검토';
  if (type === 'REPLACE_SLEEVE') return '대체 편입 검토';
  if (type === 'NO_ACTION') return '유효 액션 없음';
  return type || '조정 후보';
};

const normalizeAssetLabelKey = (ticker) => normalizeTickerSymbol(String(ticker || '').trim());

const splitAssetSymbols = (value) => {
  if (Array.isArray(value)) return value.map(normalizeAssetLabelKey).filter(Boolean);
  return String(value || '')
    .split(/[|,+]/)
    .map(normalizeAssetLabelKey)
    .filter(Boolean);
};

const buildAssetLabelMap = (assets = [], portfolios = []) => {
  const map = new Map();
  Object.entries(ASSET_DATABASE).forEach(([ticker, meta]) => {
    const normalized = normalizeAssetLabelKey(meta.aliasFor || ticker);
    if (normalized && meta?.name) map.set(normalized, meta.name);
  });
  assets.forEach((asset) => {
    const ticker = normalizeAssetLabelKey(asset.ticker);
    const label = asset.popularName || asset.label || asset.displayLabel || asset.name;
    if (ticker && label) map.set(ticker, String(label).replace(/\s*\([^)]*\)\s*$/, '').trim());
  });
  portfolios.forEach((portfolio) => {
    (portfolio.assets || []).forEach((asset) => {
      const ticker = normalizeAssetLabelKey(asset.ticker || asset.symbol || asset.name);
      if (ticker && asset.name && asset.name !== ticker) map.set(ticker, asset.name);
    });
  });
  return map;
};

const assetDisplayName = (ticker, assetLabelMap) => {
  const normalized = normalizeAssetLabelKey(ticker);
  return assetLabelMap.get(normalized) || ASSET_DATABASE[normalized]?.name || normalized || ticker || '-';
};

const formatAssetWithTicker = (ticker, assetLabelMap) => {
  const normalized = normalizeAssetLabelKey(ticker);
  const label = assetDisplayName(normalized, assetLabelMap);
  if (!normalized) return label;
  return label && label !== normalized ? `${label} (${normalized})` : normalized;
};

const formatAssetList = (value, assetLabelMap) => {
  const tickers = splitAssetSymbols(value);
  return tickers.length
    ? tickers.map((ticker) => formatAssetWithTicker(ticker, assetLabelMap)).join(', ')
    : '확인 필요';
};

const sourceAssetsText = (action, assetLabelMap) => {
  const source = action?.sourceTickers?.length ? action.sourceTickers : action?.sourceAsset;
  const hedge = action?.hedgeTickers?.length ? action.hedgeTickers : (action?.hedgeAsset || action?.candidateLabel);
  return `${formatAssetList(source, assetLabelMap)} → ${formatAssetList(hedge, assetLabelMap)}`;
};

const escapeRegExp = (value) => String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

const replaceTickerToken = (text, ticker, label) => {
  const pattern = new RegExp(`(^|[^A-Za-z0-9._-])(${escapeRegExp(ticker)})(?=$|[^A-Za-z0-9._-])`, 'g');
  return text.replace(pattern, `$1${label}`);
};

const humanizeAssetText = (value, assetLabelMap) => {
  let text = String(value || '');
  const tickers = [...assetLabelMap.keys()]
    .filter(Boolean)
    .sort((a, b) => b.length - a.length);
  tickers.forEach((ticker) => {
    const label = formatAssetWithTicker(ticker, assetLabelMap);
    if (label && label !== ticker) {
      text = replaceTickerToken(text, ticker, label);
    }
  });
  return text.replace(/\),(?=\S)/g, '), ');
};

const formatWeightPct = (value) => `${Number(value || 0).toFixed(1)}%`;

const formatDeltaPct = (value) => {
  const number = Number(value || 0);
  const sign = number > 0 ? '+' : '';
  return `${sign}${number.toFixed(1)}%p`;
};

const ActionAssetRoute = ({ source, hedge, assetLabelMap }) => (
  <div className="action-route mt-3">
    <span>{formatAssetList(source, assetLabelMap)}</span>
    <ArrowRight size={14} />
    <span>{formatAssetList(hedge, assetLabelMap)}</span>
  </div>
);

const AdjustmentRatioList = ({ rows = [], assetLabelMap, idPrefix }) => {
  if (!rows.length) return null;
  return (
    <div className="adjustment-ratio-list" aria-label="조정 비율">
      {rows.map((item) => (
        <div className={`adjustment-ratio-row ${item.delta < 0 ? 'trim' : 'add'}`} key={`${idPrefix}-${item.ticker}`}>
          <span>{formatAssetWithTicker(item.ticker, assetLabelMap)}</span>
          <strong>
            {formatWeightPct(item.currentWeight)} → {formatWeightPct(item.proposedWeight)}
          </strong>
          <em>{formatDeltaPct(item.delta)}</em>
        </div>
      ))}
    </div>
  );
};

const formatInternalScore = (value) => {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(3) : 'N/A';
};

const formatElapsed = (seconds = 0) => {
  const safe = Math.max(0, Number(seconds) || 0);
  const mins = Math.floor(safe / 60);
  const secs = Math.floor(safe % 60);
  return mins > 0 ? `${mins}분 ${secs}초` : `${secs}초`;
};

const keepElapsedMonotonic = (previous, next) => Math.max(
  Number(previous) || 0,
  Number(next) || 0,
);

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const selectedTickerText = (portfolio) => {
  const rows = toBackendPortfolioRows(portfolio || {});
  return rows.map((row) => row.ticker || row.asset).filter(Boolean).join(', ') || '선택 자산 없음';
};

const riskToneForRank = (rank) => {
  if (rank === 1) return { className: 'danger', label: '높은 위험' };
  if (rank === 2) return { className: 'caution', label: '주의' };
  return { className: 'watch', label: '경계' };
};

const PRODUCT_STATUS_VALUES = new Set(['READY', 'NEEDS_ANALYSIS', 'REFRESHING', 'STALE', 'ERROR', 'REVIEW_ONLY']);

const normalizeProductUiStatus = (value, fallback = 'NEEDS_ANALYSIS') => {
  const status = String(value || '').trim().toUpperCase();
  if (status === 'ACTION_READY') return 'READY';
  if (status === 'RUNNING' || status === 'QUEUED') return 'REFRESHING';
  if (status === 'BLOCKED' || status === 'MISMATCHED_PORTFOLIO') return 'ERROR';
  return PRODUCT_STATUS_VALUES.has(status) ? status : fallback;
};

const productStatusMessage = (status) => {
  if (status === 'READY') return 'Latest successful analysis is available for this portfolio.';
  if (status === 'REFRESHING') return 'Analysis or common data refresh is currently running.';
  if (status === 'STALE') return 'Saved analysis exists, but common market data should be refreshed.';
  if (status === 'REVIEW_ONLY') return 'Analysis is available for review, but execution is disabled.';
  if (status === 'ERROR') return 'The selected portfolio result cannot be displayed safely.';
  return 'No successful analysis run exists for this portfolio yet.';
};

const buildCauseSegments = (holdings = []) => {
  const prepared = holdings
    .map((holding, index) => {
      const pct = Number(holding.contributionPct);
      const contribution = Math.abs(Number(holding.contribution) || 0);
      const ticker = holding.ticker || `자산 ${index + 1}`;
      return {
        ticker,
        rawValue: Number.isFinite(pct) && pct > 0 ? pct : contribution,
        color: getTickerColor(ticker),
      };
    })
    .filter((segment) => segment.ticker);
  if (prepared.length === 0) return [];
  const total = prepared.reduce((sum, segment) => sum + segment.rawValue, 0);
  const equalPct = 100 / prepared.length;
  return prepared.map((segment) => ({
    ...segment,
    displayPct: total > 0 ? (segment.rawValue / total) * 100 : equalPct,
  }));
};

export const ImprovementReport = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { portfolios, updatePortfolio, usdKrwRate } = usePortfolios();

  const [selectedPortfolioId, setSelectedPortfolioId] = useState(null);
  const [selectedMetric, setSelectedMetric] = useState('cvar');
  const [animateBars, setAnimateBars] = useState(false);
  const [expandedCard, setExpandedCard] = useState(null);
  const [dashboardPayload, setDashboardPayload] = useState(null);
  const [portfolioPreview, setPortfolioPreview] = useState(null);
  const [previewError, setPreviewError] = useState('');
  const [backendAssets, setBackendAssets] = useState([]);
  const [serviceStatus, setServiceStatus] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [apiError, setApiError] = useState('');
  const [marketDataAutoStatus, setMarketDataAutoStatus] = useState({
    running: false,
    message: '',
    level: 'idle',
  });
  const [runState, setRunState] = useState({
    running: false,
    stage: '',
    error: '',
    startedAt: null,
    elapsedSeconds: 0,
    jobId: '',
    currentStep: '',
    estimatedRemainingMessage: '',
    timeoutSeconds: 15 * 60,
    stagnantStage: false,
  });
  const [lastAnalysisRun, setLastAnalysisRun] = useState(null);

  const selectedPortfolio = portfolios.find((p) => String(p.id) === String(selectedPortfolioId));
  const assetLabelMap = useMemo(() => buildAssetLabelMap(backendAssets, portfolios), [backendAssets, portfolios]);
  const selectedPortfolioRunKey = portfolioRunKey(selectedPortfolio);
  const lastRunAppliesToSelected = Boolean(lastAnalysisRun?.portfolioKey && lastAnalysisRun.portfolioKey === selectedPortfolioRunKey);
  const reportModel = useMemo(
    () => dashboardPayload ? toHedgeMateViewModel(dashboardPayload, selectedPortfolio, {
      expectedRunId: lastRunAppliesToSelected ? lastAnalysisRun?.runId : '',
      portfolioInputFingerprintHash: lastRunAppliesToSelected
        ? lastAnalysisRun?.portfolioInputFingerprintHash
        : portfolioPreview?.portfolioInputFingerprint?.hash,
      runStatus: lastRunAppliesToSelected ? lastAnalysisRun?.status : '',
    }) : null,
    [dashboardPayload, selectedPortfolio, lastAnalysisRun, lastRunAppliesToSelected, portfolioPreview]
  );
  const portfolioData = reportModel?.portfolioData;
  const lastUpdated = formatDateTime(reportModel?.updatedAt || serviceStatus?.generatedAtUtc);
  const marketDataAsOfText = formatKstDateTime(
    dashboardPayload?.dataFreshness?.marketDataDisplayAsOfKst
    || dashboardPayload?.dataFreshness?.intradayNowcastLatestTimestampKst
    || serviceStatus?.marketDataDisplayAsOfKst
    || serviceStatus?.intradayNowcastLatestTimestampKst
  );
  const showMatchedResults = Boolean(reportModel?.reportDisplayReady) && !runState.running;
  const productUiStatus = runState.running
    ? 'REFRESHING'
    : normalizeProductUiStatus(
      reportModel?.productStatus
      || dashboardPayload?.productStatus
      || serviceStatus?.selected_portfolio
      || serviceStatus?.productStatus,
    );
  const productUiMessage = productStatusMessage(productUiStatus);
  const selectedTickers = selectedTickerText(selectedPortfolio);
  const reportBlockReasons = useMemo(() => {
    if (!selectedPortfolio) return ['선택 포트폴리오가 없습니다.'];
    if (!reportModel) return [];
    const status = normalizeProductUiStatus(reportModel.productStatus);
    if (!['READY', 'STALE', 'REVIEW_ONLY'].includes(status)) {
      return [`${status}: ${productStatusMessage(status)}`];
    }
    const detail = reportModel.portfolioMatchDetail || {};
    const reasons = [];
    if (!detail.runMatches) reasons.push('방금 실행한 runId와 active manifest/bundle runId가 일치하지 않습니다.');
    if (!detail.portfolioHashMatches) reasons.push('방금 실행한 포트폴리오 fingerprint hash와 active bundle hash가 일치하지 않습니다.');
    if (!detail.tickersMatch && !detail.fingerprintMatchVerified) reasons.push('선택 포트폴리오와 active bundle의 ticker 구성이 다릅니다.');
    if (!detail.runCompleted) reasons.push('분석 job이 completed 상태가 아닙니다.');
    if (reportModel.freshnessStatus === 'STALE') {
      reasons.push(
        detail.marketDataFresh === false
          ? '실시간 시장데이터 확인 상태가 아직 준비되지 않았습니다.'
          : '최신 시장데이터 기준의 포트폴리오 분석 결과가 아직 준비되지 않았습니다.'
      );
    }
    if (!detail.artifactIntegrityOk) reasons.push('active bundle 필수 artifact가 누락되었습니다.');
    if (!['ACTION_READY', 'READY', 'REVIEW_ONLY', 'STALE'].includes(reportModel.productStatus)) reasons.push(`Backend productStatus is ${reportModel.productStatus || 'unknown'}.`);
    return reasons;
  }, [reportModel, selectedPortfolio]);
  const previewBlocksAnalysis = Boolean(portfolioPreview && portfolioPreview.canRunAnalysis === false);
  const previewBlockReasons = portfolioPreview?.errors || [];
  const freshness = dashboardPayload?.dataFreshness || {};
  const marketDataConfirmedFresh = freshness.marketDataFresh === true || reportModel?.portfolioMatchDetail?.marketDataFresh === true;
  const showMarketDataAutoStatus = Boolean(marketDataAutoStatus.message)
    && !runState.running
    && (!showMatchedResults || marketDataAutoStatus.level === 'warning');
  const staleAnalysisBundle = Boolean(
    selectedPortfolio
    && !previewBlocksAnalysis
    && marketDataConfirmedFresh
    && (
      freshness.activeBundleOlderThanMarketCache
      || freshness.portfolioInputMismatch
      || freshness.recommendationPortfolioMismatch
      || reportModel?.freshnessStatus === 'STALE'
      || reportModel?.productStatus === 'STALE'
    )
  );
  const analysisCtaLabel = runState.running
    ? '재분석 중'
    : staleAnalysisBundle
      ? '최신 데이터로 재분석'
      : '포트폴리오 분석 실행';
  const displayProductStatus = previewBlocksAnalysis ? 'ERROR' : productUiStatus;
  const analysisRequiredTitle = previewBlocksAnalysis
    ? '단일 자산 비중이 50%를 넘어 분석을 실행할 수 없습니다'
    : staleAnalysisBundle
      ? '최신 데이터로 재분석이 필요합니다'
      : '이 포트폴리오에 대한 최신 분석 결과가 없습니다';
  const analysisRequiredMessage = previewBlocksAnalysis
    ? '다중종목 포트폴리오는 한 종목 비중이 50%를 넘으면 정식 분석을 막습니다. 비중을 낮추거나 1종목 단일자산 분석으로 분리해 주세요.'
    : staleAnalysisBundle
      ? '최신 시장데이터는 반영됐지만 현재 리포트는 이전 분석 결과입니다. 최신 데이터로 재분석하세요.'
      : '이 포트폴리오에 대한 최신 분석 결과가 없습니다. 분석을 실행해야 리포트를 볼 수 있습니다.';
  const hasSingleAssetPreviewWarning = Boolean(
    portfolioPreview?.canRunAnalysis
    && (portfolioPreview?.analysisRows || []).length === 1
    && (portfolioPreview?.rows || []).some((row) => Number(row.weightPct) > 50),
  );
  const apiErrorIsTimeout = /요청 시간이 초과|timeout|timed out/i.test(apiError || '');

  useEffect(() => {
    let cancelled = false;
    getAssets({ timeoutMs: 30 * 1000 })
      .then((payload) => {
        if (!cancelled) setBackendAssets(payload.assets || []);
      })
      .catch(() => {
        if (!cancelled) setBackendAssets([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const loadBackendDashboard = async (requestOptions = {}) => {
    setIsLoading(true);
    setApiError('');
    try {
      const hedgeBudgetKrw = selectedPortfolio?.totalValue ? Math.round(selectedPortfolio.totalValue * 0.1) : '';
      const dashboard = await getProductDashboard(selectedPortfolio ? {
        snapshot: false,
        portfolio: selectedPortfolio,
        usdKrwRate,
        hedgeBudgetKrw,
        maxComboSize: 2,
        useLivePrices: true,
        mutateActiveBundle: false,
        signal: requestOptions.signal,
        timeoutMs: requestOptions.timeoutMs ?? 60 * 1000,
      } : {
        signal: requestOptions.signal,
        timeoutMs: requestOptions.timeoutMs ?? 60 * 1000,
      });
      const statusPayload = await getHedgeMateStatus({
        portfolio: selectedPortfolio,
        signal: requestOptions.signal,
        timeoutMs: requestOptions.timeoutMs ?? 30 * 1000,
      }).catch(() => null);
      setServiceStatus({
        ...(statusPayload || {}),
        generatedAtUtc: dashboard?.dataFreshness?.generatedAtUtc || dashboard?.manifest?.generated_at_utc,
        freshnessStatus: dashboard?.dataFreshness?.freshnessStatus || dashboard?.freshnessStatus,
        productStatus: dashboard?.productStatus,
        selected_portfolio: dashboard?.dataFreshness?.selectedPortfolioStatus || statusPayload?.selected_portfolio,
        marketDataDisplayAsOfKst: dashboard?.dataFreshness?.marketDataDisplayAsOfKst,
        intradayNowcastLatestTimestampKst: dashboard?.dataFreshness?.intradayNowcastLatestTimestampKst,
      });
      if (statusPayload || dashboard?.dataFreshness) {
        setMarketDataAutoStatus(marketDataStatusMessage(statusPayload || {}, dashboard));
      }
      setDashboardPayload(dashboard);
      return { dashboard };
    } catch (error) {
      if (error.name === 'AbortError') return null;
      setApiError(error.name === 'TimeoutError'
        ? '요청 시간이 초과되었습니다. 분석 결과는 백그라운드에서 생성 중일 수 있으니 잠시 후 다시 조회하세요.'
        : (error.message || 'HedgeMate 백엔드 연결에 실패했습니다.'));
      setDashboardPayload(null);
      return null;
    } finally {
      if (!requestOptions.signal?.aborted) setIsLoading(false);
    }
  };

  const marketDataStatusMessage = (statusPayload = {}, dashboard = {}) => {
    const freshness = dashboard?.dataFreshness || {};
    const marketStatus = String(statusPayload?.market_data || '').toUpperCase();
    const intradayStatus = String(statusPayload?.intraday_nowcast || '').toUpperCase();
    const asOfText = formatKstDateTime(
      freshness.marketDataDisplayAsOfKst
      || freshness.intradayNowcastLatestTimestampKst
      || statusPayload.marketDataDisplayAsOfKst
      || statusPayload.intradayNowcastLatestTimestampKst
    );
    const marketFresh = marketStatus === 'FRESH' || freshness.marketDataFresh === true;
    const intradayFresh = intradayStatus === 'FRESH' || freshness.intradayNowcastFresh === true;
    const refreshing = marketStatus === 'REFRESHING' || intradayStatus === 'REFRESHING';
    const staleTickers = freshness.marketDataStaleTickers || [];
    if (refreshing) {
      return {
        running: true,
        level: 'info',
        message: '공통 시장데이터 갱신이 백그라운드에서 진행 중입니다. 저장된 리포트를 먼저 표시합니다.',
      };
    }
    if (staleTickers.length > 0) {
      return {
        running: false,
        level: 'warning',
        message: `시장데이터 일부 종목(${staleTickers.length}개)이 지연 상태입니다. 스케줄러 갱신 후 다시 확인하세요.`,
      };
    }
    if (marketFresh && intradayFresh) {
      return {
        running: false,
        level: 'ok',
        message: asOfText ? `시장데이터 최신 확인 · ${asOfText}` : '시장데이터 최신 확인',
      };
    }
    if (freshness.marketDataRefreshAttempted && !freshness.marketDataFresh) {
      return {
        running: false,
        level: 'warning',
        message: '오늘 시장데이터 갱신을 이미 시도했습니다. 남은 지연 종목은 스케줄러가 다시 확인합니다.',
      };
    }
    return {
      running: false,
      level: 'warning',
      message: '시장데이터 갱신이 필요합니다. 자동 실행하지 않고 저장된 리포트를 먼저 표시합니다.',
    };
  };

  useEffect(() => {
    if (portfolios.length === 0) {
      if (selectedPortfolioId) setSelectedPortfolioId(null);
      return;
    }
    const selection = resolveReportPortfolioSelection(portfolios, location.search);
    if (selection.portfolioId && String(selectedPortfolioId || '') !== selection.portfolioId) {
      setSelectedPortfolioId(selection.portfolioId);
    }
    if (!selection.requestedValid && selection.portfolioId) {
      const params = new URLSearchParams(location.search);
      params.set('portfolio', selection.portfolioId);
      navigate({
        pathname: location.pathname,
        search: `?${params.toString()}`,
      }, { replace: true });
    }
  }, [portfolios, selectedPortfolioId, location.pathname, location.search, navigate]);

  useEffect(() => {
    if (!selectedPortfolio) {
      setLastAnalysisRun(null);
      return;
    }
    persistReportPortfolioId(selectedPortfolio.id);
    const restoredRun = getStoredAnalysisRunForPortfolio(selectedPortfolio);
    setLastAnalysisRun((prev) => {
      if (prev?.portfolioKey && selectedPortfolioRunKey && prev.portfolioKey === selectedPortfolioRunKey) return prev;
      return restoredRun;
    });
  }, [selectedPortfolio, selectedPortfolioRunKey]);

  useEffect(() => {
    if (selectedPortfolio) {
      const controller = new AbortController();
      loadBackendDashboard({ signal: controller.signal });
      return () => controller.abort();
    }
    return undefined;
  }, [selectedPortfolioId]);

  useEffect(() => {
    if (!selectedPortfolio) {
      setPortfolioPreview(null);
      setPreviewError('');
      return undefined;
    }
    const controller = new AbortController();
    setPreviewError('');
    previewPortfolio(selectedPortfolio, { usdKrwRate, useLivePrices: true, signal: controller.signal })
      .then((preview) => {
        if (!controller.signal.aborted) setPortfolioPreview(preview);
      })
      .catch((error) => {
        if (!controller.signal.aborted && error.name !== 'AbortError') {
          setPortfolioPreview(null);
          setPreviewError(error.message || '포트폴리오 preview를 불러오지 못했습니다.');
        }
      });
    return () => {
      controller.abort();
    };
  }, [selectedPortfolio, usdKrwRate]);

  useEffect(() => {
    if (!runState.running || !runState.startedAt) return undefined;
    const timer = setInterval(() => {
      setRunState((prev) => prev.running && prev.startedAt
        ? { ...prev, elapsedSeconds: keepElapsedMonotonic(prev.elapsedSeconds, Math.floor((Date.now() - prev.startedAt) / 1000)) }
        : prev);
    }, 1000);
    return () => clearInterval(timer);
  }, [runState.running, runState.startedAt]);

  useEffect(() => {
    setAnimateBars(false);
    const timer = setTimeout(() => setAnimateBars(true), 300);
    return () => clearTimeout(timer);
  }, [selectedPortfolioId, dashboardPayload, selectedMetric]);

  const handlePortfolioChange = (id) => {
    persistReportPortfolioId(id);
    const params = new URLSearchParams(location.search);
    params.set('portfolio', id);
    navigate({
      pathname: location.pathname,
      search: `?${params.toString()}`,
    }, { replace: true });
    setSelectedPortfolioId(id);
    setExpandedCard(null);
  };

  const ensureMarketDataCurrent = async () => {
    setRunState((prev) => ({
      ...prev,
      running: true,
      stage: '시장데이터 상태 확인 중',
      currentStep: 'market data freshness check',
      estimatedRemainingMessage: '공통 데이터가 이미 최신이면 바로 분석으로 넘어갑니다.',
      error: '',
    }));
    const statusPayload = await getHedgeMateStatus({
      portfolio: selectedPortfolio,
      timeoutMs: 30 * 1000,
    });
    const next = marketDataStatusMessage(statusPayload, dashboardPayload);
    setMarketDataAutoStatus(next);
    const marketStatus = String(statusPayload?.market_data || '').toUpperCase();
    const intradayStatus = String(statusPayload?.intraday_nowcast || '').toUpperCase();
    if (marketStatus === 'REFRESHING' || intradayStatus === 'REFRESHING') {
      throw new Error('공통 시장데이터 갱신이 백그라운드에서 진행 중입니다. 완료 후 포트폴리오 분석을 다시 실행해 주세요.');
    }
    if (marketStatus !== 'FRESH' || intradayStatus !== 'FRESH') {
      throw new Error('시장데이터가 최신 상태가 아닙니다. 스케줄러 갱신 또는 명시적 갱신 완료 후 분석을 실행해 주세요.');
    }
    setRunState((prev) => ({
      ...prev,
      running: true,
      stage: '',
      currentStep: '',
      error: '',
    }));
    return statusPayload;
  };

  const handleRunAnalysis = async () => {
    if (!selectedPortfolio) return;
    const startedAt = Date.now();
    const runKey = portfolioRunKey(selectedPortfolio);
    const startedRun = { status: 'running', runId: '', portfolioInputFingerprintHash: '', portfolioKey: runKey };
    setDashboardPayload(null);
    setLastAnalysisRun(startedRun);
    persistAnalysisRunForPortfolio(selectedPortfolio, startedRun);
    setRunState({
      running: true,
      stage: '포트폴리오 미리보기 확인 중',
      error: '',
      startedAt,
      elapsedSeconds: 0,
      jobId: '',
      currentStep: '가격 조회 중',
      estimatedRemainingMessage: '선택 포트폴리오의 최신 가격과 평가 금액을 확인합니다.',
      timeoutSeconds: 15 * 60,
      stagnantStage: false,
    });
    setApiError('');
    try {
      await ensureMarketDataCurrent();
      const preview = await previewPortfolio(selectedPortfolio, { usdKrwRate, useLivePrices: true });
      setPortfolioPreview(preview);
      if (!preview.canRunAnalysis) {
        throw new Error((preview.errors || []).join(', ') || '백엔드가 이 포트폴리오를 분석할 수 없습니다.');
      }
      setRunState((prev) => ({
        ...prev,
        running: true,
        stage: 'HedgeMate 분석 작업 시작',
        error: '',
        currentStep: '분석 작업 요청 중',
        estimatedRemainingMessage: '이전 결과를 숨기고 새 분석 작업을 시작합니다.',
      }));
      const hedgeBudgetKrw = selectedPortfolio.totalValue ? Math.round(selectedPortfolio.totalValue * 0.1) : '';
      const job = await runPortfolioAnalysis(selectedPortfolio, {
        usdKrwRate,
        hedgeBudgetKrw,
        maxComboSize: 2,
        useLivePrices: true,
        forceReanalysis: false,
        ignoreAnalysisCache: false,
      });
      const jobRun = {
        ...startedRun,
        status: 'running',
        runId: job.runId || '',
        portfolioInputFingerprintHash: job.portfolioInputFingerprintHash || '',
        portfolioKey: runKey,
      };
      setLastAnalysisRun(jobRun);
      persistAnalysisRunForPortfolio(selectedPortfolio, jobRun);
      setRunState((prev) => ({
        ...prev,
        jobId: job.jobId,
        stage: job.stage || 'queued',
        currentStep: job.currentStep || '대기 중',
        estimatedRemainingMessage: job.estimatedRemainingMessage || '',
      }));
      const finalStatus = await pollRunStatus(job.jobId, (status) => {
        if (status.runId || status.portfolioInputFingerprintHash || status.result?.portfolioInputFingerprintHash) {
          setLastAnalysisRun((prev) => ({
            ...prev,
            status: status.status || prev?.status || 'running',
            runId: status.runId || prev?.runId || '',
            portfolioInputFingerprintHash: status.portfolioInputFingerprintHash || status.result?.portfolioInputFingerprintHash || prev?.portfolioInputFingerprintHash || '',
            portfolioKey: runKey,
          }));
        }
        setRunState((prev) => ({
          ...prev,
          running: true,
          jobId: status.jobId || job.jobId,
          stage: status.stage || status.status || '분석 진행 중',
          currentStep: status.currentStep || status.stage || '분석 진행 중',
          estimatedRemainingMessage: status.estimatedRemainingMessage || '',
          elapsedSeconds: keepElapsedMonotonic(prev.elapsedSeconds, status.elapsedSeconds ?? prev.elapsedSeconds),
          timeoutSeconds: status.timeoutSeconds ?? prev.timeoutSeconds,
          stagnantStage: Boolean(status.stagnantStage),
          error: '',
        }));
      }, { timeoutMs: 15 * 60 * 1000, stagnantStageMs: 5 * 60 * 1000 });
      if (finalStatus.status !== 'completed') {
        const failedRun = {
          status: 'failed',
          runId: finalStatus.runId || jobRun.runId || '',
          portfolioInputFingerprintHash: finalStatus.portfolioInputFingerprintHash || finalStatus.result?.portfolioInputFingerprintHash || jobRun.portfolioInputFingerprintHash || '',
          portfolioKey: runKey,
        };
        setLastAnalysisRun(failedRun);
        persistAnalysisRunForPortfolio(selectedPortfolio, failedRun);
        throw new Error(finalStatus.error || '분석 작업이 완료되지 않았습니다.');
      }
      const completedAt = new Date().toISOString();
      const completedRun = {
        status: 'completed',
        runId: finalStatus.runId || finalStatus.result?.runId || jobRun.runId || '',
        portfolioInputFingerprintHash: finalStatus.portfolioInputFingerprintHash || finalStatus.result?.portfolioInputFingerprintHash || jobRun.portfolioInputFingerprintHash || '',
        portfolioKey: runKey,
        completedAt,
      };
      setLastAnalysisRun(completedRun);
      persistAnalysisRunForPortfolio(selectedPortfolio, completedRun);
      if (selectedPortfolio?.id) {
        await updatePortfolio(selectedPortfolio.id, {
          status: 'analyzed',
          latestAnalysisRunId: completedRun.runId,
          latestAnalysisAt: completedAt,
          latestAnalysisFingerprintHash: completedRun.portfolioInputFingerprintHash,
          latestAnalysisPortfolioKey: completedRun.portfolioKey,
        }).catch(() => null);
      }
      const cachedAnalysisReused = Boolean(finalStatus.result?.cached);
      setRunState((prev) => ({
        ...prev,
        running: false,
        stage: '',
        error: '',
        currentStep: cachedAnalysisReused ? 'cache hit' : '완료',
        estimatedRemainingMessage: '',
      }));
      const completedRunId = finalStatus.runId || finalStatus.result?.runId || '';
      const completedFingerprintHash = finalStatus.portfolioInputFingerprintHash || finalStatus.result?.portfolioInputFingerprintHash || '';
      let matchedDashboardLoaded = false;
      let lastMismatchDetail = null;
      for (let attempt = 1; attempt <= 4; attempt += 1) {
        setRunState((prev) => ({
          ...prev,
          running: false,
          stage: '',
          currentStep: 'result display check',
          estimatedRemainingMessage: '',
        }));
        const loaded = await loadBackendDashboard({ timeoutMs: 60 * 1000 });
        if (loaded?.dashboard) {
          const nextModel = toHedgeMateViewModel(loaded.dashboard, selectedPortfolio, {
            expectedRunId: completedRunId,
            portfolioInputFingerprintHash: completedFingerprintHash,
            runStatus: finalStatus.status,
          });
          if (nextModel.reportDisplayReady) {
            matchedDashboardLoaded = true;
            break;
          }
          lastMismatchDetail = nextModel.portfolioMatchDetail || null;
        }
        if (attempt < 4) await sleep(1500 * attempt);
      }
      if (!matchedDashboardLoaded) {
        const mismatchText = lastMismatchDetail?.message ? ` (${lastMismatchDetail.message})` : '';
        setRunState((prev) => ({
          ...prev,
          error: `ERROR: ${productStatusMessage('ERROR')}${mismatchText}`,
          stage: '',
        }));
      }
    } catch (error) {
      setLastAnalysisRun((prev) => prev?.portfolioKey === runKey ? { ...prev, status: 'failed' } : prev);
      setRunState((prev) => ({
        ...prev,
        running: false,
        stage: '',
        error: error.message || '분석 실행 중 오류가 발생했습니다.',
      }));
    }
  };

  if (portfolios.length === 0) {
    return (
      <div className="report-page">
        <div className="empty-report">
          <div className="empty-report-icon">
            <Briefcase size={48} />
          </div>
          <h2 className="mt-4">분석할 포트폴리오가 없습니다</h2>
          <p className="text-secondary text-sm mt-2" style={{ maxWidth: '400px', lineHeight: 1.6 }}>
            먼저 포트폴리오를 등록해야 분석 리포트를 확인할 수 있습니다.<br />
            보유 종목과 수량을 등록한 뒤 HedgeMate 분석을 시작하세요.
          </p>
          <Button variant="primary" className="mt-6" onClick={() => navigate('/register')}>
            포트폴리오 등록하기 <ArrowRight size={14} />
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="report-page">
      <div className="flow-breadcrumb mb-6">
        <span className="flow-crumb" onClick={() => navigate('/register')} style={{ cursor: 'pointer' }}>
          <span className="crumb-step">1</span> 포트폴리오 등록
        </span>
        <span className="flow-arrow">›</span>
        <span className="flow-crumb" onClick={() => navigate('/portfolios')} style={{ cursor: 'pointer' }}>
          <span className="crumb-step">2</span> 내 포트폴리오
        </span>
        <span className="flow-arrow">›</span>
        <span className="flow-crumb active">
          <span className="crumb-step">3</span> 취약점 리포트
        </span>
      </div>

      <div className="portfolio-selector mb-6">
        <div className="selector-header">
          <div className="flex items-center gap-2">
            <div className="selector-icon"><Briefcase size={16} /></div>
            <div>
              <div className="text-xs text-secondary font-semibold" style={{ letterSpacing: '0.05em' }}>분석 대상 포트폴리오</div>
              <div className="text-sm font-semibold mt-1">
                {selectedPortfolio ? selectedPortfolio.name : '포트폴리오를 선택하세요'}
              </div>
            </div>
          </div>
          {selectedPortfolio && (
            <div className="flex items-center gap-4">
              {selectedPortfolio.strategy && (
                <div className="flex flex-col items-end mr-4">
                  <span className="text-[0.65rem] text-secondary font-semibold uppercase tracking-wider">적용 전략</span>
                  <span className="text-xs text-accent-light font-semibold">{selectedPortfolio.strategyName}</span>
                </div>
              )}
              <div className="selector-meta">
                <span className="selector-tag">{selectedPortfolio.purpose}</span>
                <span className="selector-tag">{selectedPortfolio.assets.length}종목</span>
                <span className="selector-tag accent">등록 기준 ₩{Math.round(selectedPortfolio.totalValue || 0).toLocaleString()}</span>
              </div>
            </div>
          )}
        </div>

        <div className="selector-list">
          {portfolios.map((p) => (
            <button
              key={p.id}
              className={`selector-item ${selectedPortfolioId === p.id ? 'active' : ''}`}
              onClick={() => handlePortfolioChange(p.id)}
            >
              <div className="selector-item-info">
                <span className="font-semibold text-sm flex items-center gap-2">
                  {p.name}
                  {p.strategy && <span className="badge-purple" style={{ padding: '1px 4px', fontSize: '10px' }}>{p.strategyName}</span>}
                </span>
                <span className="text-xs text-secondary">{p.purpose} · {p.assets.length}종목</span>
              </div>
              <div className="selector-item-right">
                <span className="text-xs font-semibold">등록 기준 ₩{Math.round(p.totalValue || 0).toLocaleString()}</span>
                {p.status === 'new' && <span className="new-dot"></span>}
              </div>
            </button>
          ))}
        </div>
      </div>

      <div className="report-header flex justify-between items-start">
        <div>
          <span className="text-secondary text-xs font-semibold tracking-wider flex items-center gap-2">
            <Shield size={12} className="text-accent-light" />
            PORTFOLIO VULNERABILITY ACTIONS
          </span>
          <h1 className="mt-2 mb-1">포트폴리오 취약점 및 헷지 액션</h1>
          <p className="text-secondary text-xs">저장된 분석 업데이트: {lastUpdated}</p>
          {marketDataAsOfText && <p className="text-secondary text-xs mt-1">실시간 데이터 확인: {marketDataAsOfText}</p>}
          {reportModel?.activeRunId && <p className="text-secondary text-xs mt-1">분석 run: {reportModel.activeRunId}</p>}
        </div>
        <div className="flex gap-3" style={{ flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          <Button
            variant="primary"
            onClick={handleRunAnalysis}
            disabled={!selectedPortfolio || runState.running || (portfolioPreview && !portfolioPreview.canRunAnalysis)}
          >
            {runState.running ? <Loader2 size={14} className="spin-icon" /> : <Rocket size={14} />} {analysisCtaLabel}
          </Button>
        </div>
      </div>

      {showMarketDataAutoStatus && (
        <div className={`status-strip compact ${marketDataAutoStatus.level === 'warning' ? 'warning' : ''} mt-4`}>
          {marketDataAutoStatus.running ? <Loader2 size={14} className="spin-icon" /> : (
            marketDataAutoStatus.level === 'warning' ? <AlertCircle size={14} /> : <Shield size={14} />
          )}
          <span>{marketDataAutoStatus.message}</span>
        </div>
      )}

      {staleAnalysisBundle && !runState.running && (
        <div className="status-strip warning mt-4">
          <AlertCircle size={14} />
          <span>최신 시장데이터는 반영됐지만 현재 리포트는 이전 분석 결과입니다. 최신 데이터로 재분석하세요.</span>
        </div>
      )}

      {isLoading && !runState.running && (
        <div className="status-strip compact mt-4">
          <Loader2 size={14} className="spin-icon" />
          <span>최신 분석 결과를 불러오는 중입니다.</span>
        </div>
      )}

      {runState.stage && !runState.running && (
        <div className="status-strip mt-4">
          <Loader2 size={14} className={runState.running ? 'spin-icon' : ''} />
          <span>{runState.stage}</span>
        </div>
      )}
      {runState.error && (
        <div className="status-strip error mt-4">
          <AlertCircle size={14} />
          <span>{runState.error}</span>
        </div>
      )}

      {apiError && (
        <div className="backend-error-card mt-6">
          <AlertCircle size={24} />
          <div>
            <h3>{apiErrorIsTimeout ? 'HedgeMate 응답 시간 초과' : 'HedgeMate 백엔드 연결 실패'}</h3>
            <p>{apiError}</p>
            <p className="text-xs text-secondary mt-2">
              {apiErrorIsTimeout
                ? '서버가 꺼진 상태가 아니라 조회 응답이 제한 시간을 넘긴 상태일 수 있습니다. 최신 snapshot이 생성되면 다시 빠르게 표시됩니다.'
                : '백엔드가 꺼져 있으면 프론트는 대기 상태로 남습니다. `python HedgeMate/scripts/serve_dashboard.py --host 127.0.0.1 --port 8766`로 서버를 켠 뒤 다시 조회하세요.'}
            </p>
          </div>
        </div>
      )}

      {isLoading && !portfolioData && !runState.running && (
        <div className="backend-loading-card mt-6">
          <Loader2 size={32} className="spin-icon text-accent-light" />
          <p className="text-sm text-secondary">HedgeMate 최신 분석 결과를 불러오는 중입니다.</p>
        </div>
      )}

      {runState.running && (
        <section className="analysis-progress-card mt-6">
          <div className="progress-orb"><Loader2 size={28} className="spin-icon" /></div>
          <div className="flex-1">
            <span className="decision-badge">ANALYSIS_RUNNING</span>
            <h3>선택 포트폴리오 분석 진행 중</h3>
            <p>다른 포트폴리오 기준 결과는 숨김 처리했습니다. 분석 완료 후 선택 포트폴리오와 결과가 일치할 때만 CVaR/MDD/beta/stress/Sharpe 카드가 표시됩니다.</p>
            <div className="progress-grid mt-4">
              <div>
                <span>현재 단계</span>
                <strong>{runState.currentStep || runState.stage || '분석 진행 중'}</strong>
              </div>
              <div>
                <span>경과 시간</span>
                <strong>{formatElapsed(runState.elapsedSeconds)} / {formatElapsed(runState.timeoutSeconds || 15 * 60)}</strong>
              </div>
              <div>
                <span>선택 포트폴리오</span>
                <strong>{selectedTickers}</strong>
              </div>
            </div>
            {runState.stage && <p className="text-xs text-secondary mt-3">상태: {runState.stage}</p>}
            <p className="text-xs text-secondary mt-2">
              단계: 분석 시작 → 가격 확인 → 위험 계산 → 조정 후보 선별 → 결과 표시
            </p>
            {runState.estimatedRemainingMessage && <p className="text-xs text-secondary mt-2">{runState.estimatedRemainingMessage}</p>}
            {runState.stagnantStage && (
              <p className="decision-warning mt-3">같은 단계가 오래 지속되고 있습니다. 제한 시간을 넘기면 실패로 전환하고 이전 결과는 표시하지 않습니다.</p>
            )}
            {runState.elapsedSeconds >= 300 && (
              <p className="decision-warning mt-3">분석이 오래 걸리고 있습니다. 백테스트, gate 검증, 저장된 분석 결과 갱신 단계에서 시간이 걸릴 수 있습니다.</p>
            )}
          </div>
        </section>
      )}

      {!isLoading && !runState.running && selectedPortfolio && !showMatchedResults && (
        <section className="analysis-required-card mt-6" data-analysis-state={displayProductStatus}>
          {staleAnalysisBundle && (
            <div className="status-strip warning mt-4">
              <AlertCircle size={14} />
              <span><strong>{analysisRequiredTitle}</strong> {analysisRequiredMessage}</span>
            </div>
          )}
          <div>
            <span className="decision-badge">{displayProductStatus}</span>
            <h3>{previewBlocksAnalysis ? '단일 자산 비중이 50%를 넘어 분석을 실행할 수 없습니다' : '이 포트폴리오에 대한 최신 분석 결과가 없습니다'}</h3>
            <p>
              {previewBlocksAnalysis
                ? '다종목 포트폴리오는 한 종목 비중이 50%를 넘으면 정식 분석을 막습니다. 비중을 낮추거나 1종목 단일자산 분석으로 분리해 주세요.'
                : '이 포트폴리오에 대한 최신 분석 결과가 없습니다. 분석을 실행해야 리포트를 볼 수 있습니다.'}
            </p>
          </div>
          <div className="status-strip compact mt-4">
            <Shield size={14} />
            <span>{displayProductStatus}: {productUiMessage}</span>
          </div>
          <div className="selected-summary-grid mt-5">
            <div>
              <span>선택 포트폴리오</span>
              <strong>{selectedPortfolio.name}</strong>
            </div>
            <div>
              <span>선택 자산</span>
              <strong>{selectedTickers}</strong>
            </div>
            <div>
              <span>등록 기준 금액</span>
              <strong>₩{Math.round(selectedPortfolio.totalValue || 0).toLocaleString()}</strong>
            </div>
            <div>
              <span>상태</span>
              <strong>{previewBlocksAnalysis ? 'ERROR' : (runState.error ? 'ERROR' : displayProductStatus)}</strong>
            </div>
          </div>
          {previewBlocksAnalysis && previewBlockReasons.length > 0 && (
            <div className="status-strip warning mt-4">
              <AlertCircle size={14} />
              <div>
                {previewBlockReasons.slice(0, 5).map((reason) => (
                  <div key={reason}>{reason}</div>
                ))}
              </div>
            </div>
          )}
          {!previewBlocksAnalysis && hasSingleAssetPreviewWarning && (
            <div className="status-strip warning mt-4">
              <AlertCircle size={14} />
              <span>1종목 포트폴리오는 50% 초과 경고가 있어도 단일자산 분석으로 진행할 수 있습니다.</span>
            </div>
          )}
          {reportBlockReasons.length > 0 && (
            <div className="status-strip warning mt-4">
              <AlertCircle size={14} />
              <div>
                {reportBlockReasons.slice(0, 5).map((reason) => (
                  <div key={reason}>{reason}</div>
                ))}
              </div>
            </div>
          )}
          {portfolioPreview?.rows?.length > 0 && (
            <div className="data-table-wrapper mt-5">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>자산</th>
                    <th>평가 기준</th>
                    <th>최신 단가</th>
                    <th>평가액</th>
                    <th>가격 출처</th>
                    <th>주의</th>
                  </tr>
                </thead>
                <tbody>
                  {portfolioPreview.rows.map((row) => (
                    <tr key={`${row.resolvedTicker}-${row.rowIndex}`}>
                      <td>{row.displayLabel || row.resolvedTicker}</td>
                      <td>{row.valuationBasis === 'quantity' ? '최신가×수량' : '입력 금액'}</td>
                      <td>{row.currency === 'KRW' ? '₩' : '$'}{Number(row.latestPrice || 0).toLocaleString()}</td>
                      <td>₩{Math.round(row.marketValueKrw || 0).toLocaleString()}</td>
                      <td>{row.priceSource || row.dataMode || '-'}</td>
                      <td>{(row.warnings || []).slice(0, 1).join(' ') || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {previewError && (
            <div className="status-strip error mt-4">
              <AlertCircle size={14} />
              <span>{previewError}</span>
            </div>
          )}
        </section>
      )}

      {showMatchedResults && (
        <>
          <div className={`decision-banner ${reportModel.decisionBanner.tone} mt-6`}>
            <div>
              <span className="decision-badge">{reportModel.decisionBanner.badge}</span>
              <h3>{reportModel.decisionBanner.title}</h3>
              <p>{reportModel.decisionBanner.summary}</p>
              {reportModel.portfolioMatches && !reportModel.portfolioMatchDetail?.weightVerified && (
                <p className="decision-warning mt-2">{reportModel.portfolioMatchDetail.message}</p>
              )}
            </div>
            <div className="decision-counts">
              {reportModel.decisionBanner.counts.formalRecommendations > 0
                ? <span>추천안 {reportModel.decisionBanner.counts.formalRecommendations}</span>
                : <span>추천 기준 충족 없음</span>}
              <span>선택 후보 {reportModel.decisionBanner.counts.formal}</span>
              <span>추가 확인 {reportModel.decisionBanner.counts.review}</span>
              <span>제외 {reportModel.decisionBanner.counts.fail}</span>
              <span>A {reportModel.decisionBanner.counts.gradeA}</span>
              <span>B {reportModel.decisionBanner.counts.gradeB}</span>
              <span>C {reportModel.decisionBanner.counts.gradeC}</span>
              <span>D {reportModel.decisionBanner.counts.gradeD}</span>
            </div>
          </div>

          {reportModel.warnings.length > 0 && (
            <div className="status-strip warning mt-4">
              <AlertCircle size={14} />
              <div>
                {reportModel.warnings.slice(0, 4).map((warning) => (
                  <div key={warning}>{warning}</div>
                ))}
              </div>
            </div>
          )}

          <section className="vulnerability-first-panel mt-6">
            <div className="section-title-row">
              <div>
                <span className="eyebrow">Portfolio Vulnerability</span>
                <h3>주의해야 할 주요 위험 요인</h3>
              </div>
              <span className="text-xs text-secondary">현재 분석 결과 기준</span>
            </div>
            {(() => {
              const topThree = reportModel.topVulnerabilities.slice(0, 3);
              const maxRisk = Math.max(...topThree.map((item) => Math.abs(item.netVulnerability || 0)), 1);
              return (
                <div className="top-vulnerability-list">
                  {topThree.map((item) => {
                    const tone = riskToneForRank(item.rank);
                    const progressWidth = Math.max(8, Math.min(100, (Math.abs(item.netVulnerability || 0) / maxRisk) * 100));
                    const causeSegments = buildCauseSegments(item.sourceHoldings);
                    return (
                      <article className={`top-vulnerability-card ${tone.className} ${item.rank === 1 ? 'primary' : ''}`} key={`top-${item.riskSleeve}`}>
                        <div className="top-vulnerability-head">
                          <div className="risk-title-group">
                            <div className="risk-title-meta">
                              <span className="rank-chip">#{item.rank}</span>
                              <span className="risk-level-chip">{tone.label}</span>
                            </div>
                            <h4>{item.label}</h4>
                          </div>
                          <div className="risk-score-block">
                            <span>위험 지수</span>
                            <div className="risk-score-row">
                              <strong>{item.netVulnerability.toFixed(4)}</strong>
                              <div className="risk-progress-track" aria-hidden="true">
                                <div className="risk-progress-fill" style={{ width: `${progressWidth}%` }}></div>
                              </div>
                            </div>
                            <small>전체 취약성 중 {item.contributionPct.toFixed(1)}%</small>
                          </div>
                        </div>
                        <p className="risk-summary">
                          이 위험은 주로 {item.sourceHoldings.map((holding) => formatAssetWithTicker(holding.ticker, assetLabelMap)).join(', ') || '보유 자산'}에서 만들어집니다.
                        </p>
                        <div className="cause-stack-section">
                          <div className="cause-stack-label">위험 유발 자산</div>
                          {causeSegments.length > 0 ? (
                            <>
                              <div className="asset-stacked-bar" aria-label={`${item.label} 위험 유발 자산 비중`}>
                                {causeSegments.map((segment) => (
                                  <div
                                    key={`${item.riskSleeve}-${segment.ticker}`}
                                    className="asset-stack-segment"
                                    style={{ width: `${segment.displayPct}%`, backgroundColor: segment.color }}
                                    title={`${segment.ticker} ${segment.displayPct.toFixed(1)}%`}
                                  >
                                    {segment.displayPct >= 16 ? `${assetDisplayName(segment.ticker, assetLabelMap)} ${segment.displayPct.toFixed(0)}%` : segment.displayPct >= 8 ? assetDisplayName(segment.ticker, assetLabelMap) : ''}
                                  </div>
                                ))}
                              </div>
                              <div className="asset-stack-legend">
                                {causeSegments.map((segment) => (
                                  <span key={`${item.riskSleeve}-${segment.ticker}-legend`}>
                                    <i style={{ backgroundColor: segment.color }}></i>
                                    {formatAssetWithTicker(segment.ticker, assetLabelMap)} {segment.displayPct.toFixed(1)}%
                                  </span>
                                ))}
                              </div>
                            </>
                          ) : (
                            <div className="cause-stack-empty">원인 자산 정보가 없습니다.</div>
                          )}
                          {item.offsetHoldings.length > 0 && (
                            <div className="offset-note">
                              상쇄 자산: {item.offsetHoldings.slice(0, 2).map((holding) => formatAssetWithTicker(holding.ticker || holding.asset_ticker || holding, assetLabelMap)).join(', ')}
                            </div>
                          )}
                        </div>
                      </article>
                    );
                  })}
                </div>
              );
            })()}
          </section>

          <section className="chart-card mt-6" data-testid="vulnerability-prescriptions">
            <div className="flex justify-between items-start gap-4 mb-4">
              <div>
                <span className="eyebrow">Vulnerability Prescriptions</span>
                <h3 className="font-semibold">취약점별 헷징 처방</h3>
                <p className="text-xs text-secondary mt-1">
                  해당 위험을 직접 낮춘 근거가 있는 후보만 처방으로 표시합니다.
                </p>
              </div>
              <span className="decision-badge">{reportModel.productStatus}</span>
            </div>
            <div className="action-card-grid">
              {reportModel.prescriptionRows.map((row) => {
                const candidate = row.candidate;
                const adjustmentRows = candidate?.adjustmentRows || [];
                return (
                  <article className="action-card" key={row.id} data-testid="prescription-card">
                    <div className="flex justify-between items-start gap-3">
                      <div>
                        <span className={`grade-badge grade-${row.grade.toLowerCase()}`}>{row.gradeLabel}</span>
                        {row.userDisplayScore !== null && row.userDisplayScore !== undefined && (
                          <span className={`recommendation-score grade-${row.grade.toLowerCase()}`}>
                            추천 점수 {row.userDisplayScore}/100
                          </span>
                        )}
                        <h4>{row.vulnerability.label}</h4>
                      </div>
                      <span className="text-xs text-secondary">#{row.vulnerability.rank}</span>
                    </div>
                    <p className="text-xs text-secondary mt-3">
                      줄일 자산: {formatAssetList(row.sourceAssets, assetLabelMap)}
                    </p>
                    <ActionAssetRoute
                      source={candidate?.sourceTickers || candidate?.sourceAsset || row.sourceAssets}
                      hedge={candidate ? candidate.hedgeTickers || candidate.hedgeAsset : []}
                      assetLabelMap={assetLabelMap}
                    />
                    <AdjustmentRatioList rows={adjustmentRows} assetLabelMap={assetLabelMap} idPrefix={row.id} />
                    <p className="text-xs mt-3">{humanizeAssetText(row.reason, assetLabelMap)}</p>
                    {candidate?.reason && <p className="text-xs text-secondary mt-2">{humanizeAssetText(candidate.reason, assetLabelMap)}</p>}
                    <div className="action-mini-metrics">
                      <span>취약점 개선 {Number(candidate?.improvePct || 0).toFixed(1)}%</span>
                      <span>{row.directMatch ? '직접 처방 근거 있음' : 'benchmark 표시'}</span>
                      {candidate?.metricRows?.slice(0, 3).map((metric) => (
                        <span key={`${row.id}-${metric.key}`}>{metric.label} {metric.improvementText}</span>
                      ))}
                    </div>
                    {candidate && (
                      <details className="score-detail">
                        <summary>세부 지표</summary>
                        <div>
                          <span>linked final_score {formatInternalScore(candidate.linkedFinalScore)}</span>
                          <span>prescription_score {formatInternalScore(candidate.prescriptionScore)}</span>
                          <span>{candidate.scoreBand || row.scoreBand}</span>
                          <span>{candidate.scoreMethodVersion || row.scoreMethodVersion}</span>
                        </div>
                      </details>
                    )}
                  </article>
                );
              })}
            </div>
          </section>

          {portfolioData && reportModel.actionCards.length > 0 && (
            <>
              <div className="metric-cards flex gap-4 mt-6">
                <div className={`metric-card clickable ${expandedCard === 'base' ? 'expanded' : ''}`} onClick={() => setExpandedCard(expandedCard === 'base' ? null : 'base')}>
                  <div className="flex justify-between items-center mb-6">
                    <h3 className="font-semibold text-secondary">현재 포트폴리오</h3>
                    <span className="badge-dark">BASE</span>
                  </div>
                  {metricKeys.map((metricKey) => (
                    <div className="metric-row mt-4" key={metricKey}>
                      <span title={METRIC_DEFINITIONS[metricKey].helper}>{METRIC_DEFINITIONS[metricKey].label}</span>
                      <div className="text-right">
                        <div className="font-semibold text-lg">{formatMetricValue(portfolioData.base[metricKey], metricKey)}</div>
                        <div className="text-xs text-secondary">기준값</div>
                      </div>
                    </div>
                  ))}
                  {expandedCard === 'base' && selectedPortfolio && (
                    <div className="detail-panel mt-4">
                      <div className="text-xs text-secondary mb-2">구성 종목</div>
                      <div className="text-sm">
                        {selectedPortfolio.assets.map((asset) => `${formatAssetWithTicker(asset.ticker || asset.name, assetLabelMap)} (${asset.weight ?? '-'}%)`).join(', ')}
                      </div>
                      <div className="text-xs text-secondary mt-3 mb-2">등록 기준 금액</div>
                      <div className="text-sm">₩{Math.round(selectedPortfolio.totalValue || 0).toLocaleString()}</div>
                    </div>
                  )}
                  <div className="expand-indicator mt-2">
                    {expandedCard === 'base' ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </div>
                </div>

                {['recommended', 'optimized'].map((type, index) => {
                  const action = portfolioData.actions[index];
                  return (
                    <div
                      key={type}
                      className={`metric-card clickable ${index === 1 ? 'highlight' : ''} ${expandedCard === type ? 'expanded' : ''}`}
                      onClick={() => setExpandedCard(expandedCard === type ? null : type)}
                    >
                      <div className="flex justify-between items-center mb-6">
                        <h3 className="font-semibold text-primary">{cleanActionLabel(portfolioData.labels[type])}</h3>
                        <span className={index === 1 ? 'badge-blue' : 'badge-purple'}>{cleanActionLabel(action?.badge || 'NO ACTION')}</span>
                      </div>
                      {metricKeys.map((metricKey) => (
                        <div className="metric-row mt-4" key={metricKey}>
                          <span title={METRIC_DEFINITIONS[metricKey].helper}>{METRIC_DEFINITIONS[metricKey].label}</span>
                          <div className="text-right">
                            <div className={`font-semibold text-lg ${index === 1 ? 'text-blue' : 'text-accent-light'}`}>{formatMetricValue(portfolioData[type][metricKey], metricKey)}</div>
                            <div className={`text-xs ${index === 1 ? 'text-blue' : 'text-accent-light'}`}>{getImproveText(portfolioData, type, metricKey)}</div>
                          </div>
                        </div>
                      ))}
                      {expandedCard === type && (
                        <div className="detail-panel mt-4">
                          <div className="text-xs text-secondary mb-2">취약점 연결</div>
                          <div className="text-sm">{action?.riskSleeveLabel || '선택 액션 없음'}</div>
                          <div className="text-xs text-secondary mt-3 mb-2">원인 자산과 후보</div>
                          <div className="text-sm">{action ? sourceAssetsText(action, assetLabelMap) : '추가 분석 필요'}</div>
                          <AdjustmentRatioList rows={action?.adjustmentRows || []} assetLabelMap={assetLabelMap} idPrefix={`${type}-detail`} />
                          {action?.rejectedReasonKo && <div className="text-xs text-secondary mt-3">{humanizeAssetText(action.rejectedReasonKo, assetLabelMap)}</div>}
                        </div>
                      )}
                      <div className="expand-indicator mt-2">
                        {expandedCard === type ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="chart-card mt-6">
                <div className="metric-tabs flex gap-2 mb-4">
                  {metricKeys.map((metricKey) => (
                    <button
                      key={metricKey}
                      className={`metric-tab ${selectedMetric === metricKey ? 'active' : ''}`}
                      onClick={() => setSelectedMetric(metricKey)}
                      title={METRIC_DEFINITIONS[metricKey].helper}
                    >
                      {METRIC_DEFINITIONS[metricKey].label}
                    </button>
                  ))}
                </div>
                <p className="text-xs text-secondary mb-4 metric-helper">
                  {METRIC_DEFINITIONS[selectedMetric].label}: {METRIC_DEFINITIONS[selectedMetric].helper}
                </p>
                <div className="flex justify-between items-center mb-6">
                  <div>
                    <h3 className="font-semibold">{METRIC_DEFINITIONS[selectedMetric].label} 비교</h3>
                    <p className="text-xs text-secondary mt-1">{METRIC_DEFINITIONS[selectedMetric].helper}</p>
                  </div>
                  <div className="flex gap-4 text-xs text-secondary chart-legend">
                    <span className="flex items-center gap-1"><span className="dot dot-dark"></span> 현재</span>
                    <span className="flex items-center gap-1"><span className="dot dot-purple"></span> 조정안 1</span>
                    <span className="flex items-center gap-1"><span className="dot dot-blue"></span> 조정안 2</span>
                  </div>
                </div>

                {['base', 'recommended', 'optimized'].map((type) => (
                  <div className={`bar-row ${type !== 'base' ? 'mt-6' : ''}`} key={type}>
                    <div className={`flex justify-between text-xs mb-2 ${type === 'base' ? 'text-secondary' : type === 'recommended' ? 'text-accent-light' : 'text-blue'}`}>
                      <span>{cleanActionLabel(portfolioData.labels[type])}</span>
                      <span>{formatMetricValue(portfolioData[type][selectedMetric], selectedMetric)} ({getImproveText(portfolioData, type, selectedMetric)})</span>
                    </div>
                    <div className="bar-container"><div className={`bar ${type === 'base' ? 'bar-dark' : type === 'recommended' ? 'bar-purple' : 'bar-blue'}`} style={{ width: animateBars ? `${calcBarWidth(portfolioData, type, selectedMetric)}%` : '0%' }}></div></div>
                  </div>
                ))}
              </div>

            </>
          )}

          <details className="chart-card mt-6 candidate-details">
            <summary>전체 후보와 근거 보기</summary>
            <p className="text-xs text-secondary mt-3 mb-4">아래 표는 참고용 후보와 탈락 사유까지 함께 보여줍니다.</p>
            <div className="data-table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>상태</th>
                    <th>액션</th>
                    <th>취약점</th>
                    <th>원인 자산</th>
                    <th>후보</th>
                    <th>완화율</th>
                    <th>설명</th>
                  </tr>
                </thead>
                <tbody>
                  {reportModel.candidateRows.slice(0, 25).map((row) => (
                    <tr key={row.id}>
                      <td>{row.status === 'REVIEW_ACTION' ? '검토 필요 후보' : row.status}</td>
                      <td>{actionTypeLabel(row.actionType)}</td>
                      <td>{row.riskSleeveLabel}</td>
                      <td>{formatAssetList(row.sourceTickers || row.sourceAsset, assetLabelMap)}</td>
                      <td>{formatAssetList(row.hedgeTickers || row.hedgeAsset, assetLabelMap)}</td>
                      <td>{row.improvePct.toFixed(1)}%</td>
                      <td>{humanizeAssetText(row.reason, assetLabelMap)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        </>
      )}
    </div>
  );
};
