import React, { useEffect, useMemo, useState } from 'react';
import { Shield, Rocket, ChevronDown, ChevronUp, RefreshCw, Briefcase, AlertCircle, ArrowRight, Loader2 } from 'lucide-react';
import { Button } from '../components/Button';
import { useLocation, useNavigate } from 'react-router-dom';
import { usePortfolios } from '../context/PortfolioContext';
import { getProductDashboard, pollRunStatus, previewPortfolio, refreshMarketData, runPortfolioAnalysis, toBackendPortfolioRows } from '../services/hedgemateApi';
import { METRIC_DEFINITIONS, formatMetricDelta, formatMetricValue, toHedgeMateViewModel } from '../services/hedgemateViewModel';
import './ImprovementReport.css';

const metricKeys = ['cvar', 'mdd', 'beta', 'stress', 'sharpe'];

const formatDateTime = (value) => {
  if (!value) return '백엔드 산출물 기준 없음';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('ko-KR');
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

const actionStatusClass = (status) => {
  if (status === 'FORMAL_ACTION') return 'status-ready';
  if (status === 'REVIEW_ACTION') return 'status-review';
  if (status === 'FAIL_ACTION') return 'status-fail';
  return 'status-muted';
};

const actionTypeLabel = (type) => {
  if (type === 'TRIM_AND_HEDGE') return '비중 축소 + 헷지';
  if (type === 'ADD_HEDGE') return '헷지 추가 검토';
  if (type === 'REPLACE_SLEEVE') return '대체 편입 검토';
  if (type === 'NO_ACTION') return '유효 액션 없음';
  return type || '검토 액션';
};

const sourceAssetsText = (action) => {
  const source = action?.sourceTickers?.join(', ') || '원인 자산 확인 필요';
  const hedge = action?.hedgeTickers?.join(', ') || action?.candidateLabel || '헷지 후보 확인 필요';
  return `${source} → ${hedge}`;
};

const formatElapsed = (seconds = 0) => {
  const safe = Math.max(0, Number(seconds) || 0);
  const mins = Math.floor(safe / 60);
  const secs = Math.floor(safe % 60);
  return mins > 0 ? `${mins}분 ${secs}초` : `${secs}초`;
};

const selectedTickerText = (portfolio) => {
  const rows = toBackendPortfolioRows(portfolio || {});
  return rows.map((row) => row.ticker || row.asset).filter(Boolean).join(', ') || '선택 자산 없음';
};

const portfolioRunKey = (portfolio) => {
  const rows = toBackendPortfolioRows(portfolio || {});
  const stableNumber = (value) => {
    const number = Number(value);
    return Number.isFinite(number) ? number.toFixed(6) : '';
  };
  return rows
    .map((row) => [
      row.ticker || row.asset,
      stableNumber(row.quantity),
      stableNumber(row.amountKrw),
    ].join(':'))
    .filter(Boolean)
    .sort()
    .join('|');
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
  const [serviceStatus, setServiceStatus] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [apiError, setApiError] = useState('');
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

  const selectedPortfolio = portfolios.find((p) => p.id === selectedPortfolioId);
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
  const showMatchedResults = Boolean(reportModel?.reportDisplayReady) && !runState.running;
  const selectedTickers = selectedTickerText(selectedPortfolio);
  const reportBlockReasons = useMemo(() => {
    if (!selectedPortfolio) return ['선택 포트폴리오가 없습니다.'];
    if (!reportModel) return [];
    const detail = reportModel.portfolioMatchDetail || {};
    const reasons = [];
    if (!detail.runMatches) reasons.push('방금 실행한 runId와 active manifest/bundle runId가 일치하지 않습니다.');
    if (!detail.portfolioHashMatches) reasons.push('방금 실행한 포트폴리오 fingerprint hash와 active bundle hash가 일치하지 않습니다.');
    if (!detail.tickersMatch) reasons.push('선택 포트폴리오와 active bundle의 ticker 구성이 다릅니다.');
    if (!detail.runCompleted) reasons.push('분석 job이 completed 상태가 아닙니다.');
    if (reportModel.freshnessStatus === 'STALE') reasons.push('데이터 freshnessStatus가 STALE입니다.');
    if (!detail.artifactIntegrityOk) reasons.push('active bundle 필수 artifact가 누락되었습니다.');
    if (!['ACTION_READY', 'REVIEW_ONLY', 'STALE'].includes(reportModel.productStatus)) reasons.push(`백엔드 productStatus가 ${reportModel.productStatus || 'unknown'}입니다.`);
    return reasons;
  }, [reportModel, selectedPortfolio]);

  const loadBackendDashboard = async (requestOptions = {}) => {
    setIsLoading(true);
    setApiError('');
    try {
      const hedgeBudgetKrw = selectedPortfolio?.totalValue ? Math.round(selectedPortfolio.totalValue * 0.1) : '';
      const dashboard = await getProductDashboard(selectedPortfolio ? {
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
      setServiceStatus({
        generatedAtUtc: dashboard?.dataFreshness?.generatedAtUtc || dashboard?.manifest?.generated_at_utc,
        freshnessStatus: dashboard?.dataFreshness?.freshnessStatus || dashboard?.freshnessStatus,
        productStatus: dashboard?.productStatus,
      });
      setDashboardPayload(dashboard);
      return { dashboard };
    } catch (error) {
      if (error.name === 'AbortError') return null;
      setApiError(error.message || 'HedgeMate 백엔드 연결에 실패했습니다.');
      setDashboardPayload(null);
      return null;
    } finally {
      if (!requestOptions.signal?.aborted) setIsLoading(false);
    }
  };

  useEffect(() => {
    if (!selectedPortfolioId && portfolios.length > 0) {
      const params = new URLSearchParams(location.search);
      const requestedId = params.get('portfolio');
      const requested = requestedId && portfolios.some((portfolio) => portfolio.id === requestedId);
      setSelectedPortfolioId(requested ? requestedId : portfolios[0].id);
    }
  }, [portfolios, selectedPortfolioId, location.search]);

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
        ? { ...prev, elapsedSeconds: Math.floor((Date.now() - prev.startedAt) / 1000) }
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
    setSelectedPortfolioId(id);
    setExpandedCard(null);
  };

  const ensureMarketDataCurrent = async () => {
    setRunState((prev) => ({
      ...prev,
      running: true,
      stage: '\uC2DC\uC7A5\uB370\uC774\uD130 \uCD5C\uC2E0 \uC5EC\uBD80 \uD655\uC778 \uC911',
      currentStep: 'market data freshness check',
      estimatedRemainingMessage: '\uC624\uB298 \uAE30\uC900 \uC0B0\uCD9C\uBB3C\uC774 \uC788\uC73C\uBA74 \uC989\uC2DC \uAC74\uB108\uB701\uB2C8\uB2E4.',
      error: '',
    }));
    const refreshJob = await refreshMarketData({
      mode: 'full_rebuild',
      maxComboSize: 2,
      useLivePrices: true,
      autoRefresh: true,
    });
    if (refreshJob.status === 'skipped_latest' || refreshJob.status === 'completed') {
      return refreshJob;
    }
    if (!refreshJob.jobId) {
      throw new Error('\uC2DC\uC7A5\uB370\uC774\uD130 \uAC31\uC2E0 \uC791\uC5C5 ID\uB97C \uBC1B\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4.');
    }
    const finalStatus = await pollRunStatus(refreshJob.jobId, (status) => {
      setRunState((prev) => ({
        ...prev,
        running: true,
        jobId: status.jobId || refreshJob.jobId,
        stage: status.stage || status.status || '\uC2DC\uC7A5\uB370\uC774\uD130 \uAC31\uC2E0 \uC911',
        currentStep: status.currentStep || status.stage || '\uC2DC\uC7A5\uB370\uC774\uD130 \uAC31\uC2E0 \uC911',
        estimatedRemainingMessage: status.estimatedRemainingMessage || '',
        elapsedSeconds: status.elapsedSeconds ?? prev.elapsedSeconds,
        timeoutSeconds: status.timeoutSeconds ?? prev.timeoutSeconds,
        stagnantStage: Boolean(status.stagnantStage),
        error: '',
      }));
    }, { intervalMs: 3000, timeoutMs: 30 * 60 * 1000 });
    if (finalStatus.status !== 'completed') {
      throw new Error(finalStatus.error || '\uC2DC\uC7A5\uB370\uC774\uD130 \uAC31\uC2E0\uC774 \uC644\uB8CC\uB418\uC9C0 \uC54A\uC558\uC2B5\uB2C8\uB2E4.');
    }
    return finalStatus;
  };

  const handleRunAnalysis = async () => {
    if (!selectedPortfolio) return;
    const startedAt = Date.now();
    const runKey = portfolioRunKey(selectedPortfolio);
    setDashboardPayload(null);
    setLastAnalysisRun({ status: 'running', runId: '', portfolioInputFingerprintHash: '', portfolioKey: runKey });
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
      const job = await runPortfolioAnalysis(selectedPortfolio, { usdKrwRate, hedgeBudgetKrw, maxComboSize: 2, useLivePrices: true });
      setLastAnalysisRun((prev) => ({
        ...prev,
        status: 'running',
        runId: job.runId || prev?.runId || '',
        portfolioInputFingerprintHash: job.portfolioInputFingerprintHash || prev?.portfolioInputFingerprintHash || '',
        portfolioKey: runKey,
      }));
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
          elapsedSeconds: status.elapsedSeconds ?? prev.elapsedSeconds,
          timeoutSeconds: status.timeoutSeconds ?? prev.timeoutSeconds,
          stagnantStage: Boolean(status.stagnantStage),
          error: '',
        }));
      }, { timeoutMs: 15 * 60 * 1000, stagnantStageMs: 5 * 60 * 1000 });
      if (finalStatus.status !== 'completed') {
        setLastAnalysisRun((prev) => ({
          ...prev,
          status: 'failed',
          runId: finalStatus.runId || prev?.runId || '',
          portfolioInputFingerprintHash: finalStatus.portfolioInputFingerprintHash || finalStatus.result?.portfolioInputFingerprintHash || prev?.portfolioInputFingerprintHash || '',
          portfolioKey: runKey,
        }));
        throw new Error(finalStatus.error || '분석 작업이 완료되지 않았습니다.');
      }
      setLastAnalysisRun((prev) => ({
        ...prev,
        status: 'completed',
        runId: finalStatus.runId || finalStatus.result?.runId || prev?.runId || '',
        portfolioInputFingerprintHash: finalStatus.portfolioInputFingerprintHash || finalStatus.result?.portfolioInputFingerprintHash || prev?.portfolioInputFingerprintHash || '',
        portfolioKey: runKey,
      }));
      if (selectedPortfolio?.id) {
        updatePortfolio(selectedPortfolio.id, {
          status: 'analyzed',
          latestAnalysisRunId: finalStatus.runId || finalStatus.result?.runId || '',
          latestAnalysisAt: new Date().toISOString(),
        });
      }
      const cachedAnalysisReused = Boolean(finalStatus.result?.cached);
      setRunState((prev) => ({
        ...prev,
        running: false,
        stage: cachedAnalysisReused ? '저장된 분석 캐시 재사용 완료' : '분석 완료. 최신 산출물을 불러오는 중',
        error: '',
        currentStep: cachedAnalysisReused ? 'cache hit' : '완료',
      }));
      const loaded = await loadBackendDashboard();
      if (loaded?.dashboard) {
        const nextModel = toHedgeMateViewModel(loaded.dashboard, selectedPortfolio, {
          expectedRunId: finalStatus.runId || finalStatus.result?.runId || '',
          portfolioInputFingerprintHash: finalStatus.portfolioInputFingerprintHash || finalStatus.result?.portfolioInputFingerprintHash || '',
          runStatus: finalStatus.status,
        });
        if (!nextModel.officialReportReady) {
          setRunState((prev) => ({
            ...prev,
            error: '분석은 끝났지만 active dashboard의 runId/hash/ticker 또는 freshness 조건이 일치하지 않습니다. 이전 결과 카드를 표시하지 않습니다.',
            stage: '',
          }));
        }
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

  const _handleRefreshMarketData = async () => {
    const startedAt = Date.now();
    setDashboardPayload(null);
    setRunState({
      running: true,
      stage: '시장데이터 갱신 작업 요청 중',
      error: '',
      startedAt,
      elapsedSeconds: 0,
      jobId: '',
      currentStep: '시장데이터 갱신 중',
      estimatedRemainingMessage: '가격과 최신 산출물을 다시 만드는 동안 이전 결과를 숨깁니다.',
      timeoutSeconds: 30 * 60,
      stagnantStage: false,
    });
    setApiError('');
    try {
      const hedgeBudgetKrw = selectedPortfolio?.totalValue ? Math.round(selectedPortfolio.totalValue * 0.1) : '';
      const refreshJob = await refreshMarketData({
        portfolioRows: selectedPortfolio ? toBackendPortfolioRows(selectedPortfolio, { usdKrwRate }) : undefined,
        hedgeBudgetKrw,
        maxComboSize: 2,
        useLivePrices: true,
      });
      if (refreshJob.status === 'skipped_latest' || refreshJob.status === 'completed') {
        setRunState((prev) => ({
          ...prev,
          running: false,
          stage: refreshJob.result?.reason || '시장데이터가 이미 최신 상태입니다.',
          error: '',
        }));
        await loadBackendDashboard();
        return;
      }
      const finalStatus = await pollRunStatus(refreshJob.jobId, (status) => {
        setRunState((prev) => ({
          ...prev,
          running: true,
          jobId: status.jobId || refreshJob.jobId,
          stage: status.stage || status.status || '시장데이터 갱신 중',
          currentStep: status.currentStep || status.stage || '시장데이터 갱신 중',
          estimatedRemainingMessage: status.estimatedRemainingMessage || '',
          elapsedSeconds: status.elapsedSeconds ?? prev.elapsedSeconds,
          timeoutSeconds: status.timeoutSeconds ?? prev.timeoutSeconds,
          stagnantStage: Boolean(status.stagnantStage),
          error: '',
        }));
      }, { intervalMs: 3000, timeoutMs: 30 * 60 * 1000 });
      if (finalStatus.status !== 'completed') {
        throw new Error(finalStatus.error || '시장데이터 갱신 작업이 완료되지 않았습니다.');
      }
      setRunState((prev) => ({
        ...prev,
        running: false,
        stage: '시장데이터 갱신 완료. 최신 산출물을 불러오는 중',
        error: '',
      }));
      await loadBackendDashboard();
    } catch (error) {
      setRunState((prev) => ({
        ...prev,
        running: false,
        stage: '',
        error: error.message || '시장데이터 갱신 중 오류가 발생했습니다.',
      }));
    }
  };

  const handleRefreshMarketDataMode = async ({
    mode = 'market_data_only',
    label = '시장데이터 빠른 갱신',
    forceFullRefresh = false,
  } = {}) => {
    const startedAt = Date.now();
    const isHeavyJob = mode !== 'market_data_only';
    const timeoutMs = isHeavyJob ? 30 * 60 * 1000 : 8 * 60 * 1000;
    setDashboardPayload(null);
    setRunState({
      running: true,
      stage: `${label} 요청 중`,
      error: '',
      startedAt,
      elapsedSeconds: 0,
      jobId: '',
      currentStep: mode === 'market_data_only' ? 'cache loading' : label,
      estimatedRemainingMessage: mode === 'market_data_only'
        ? '기존 raw snapshot을 확인하고 누락된 거래일만 갱신합니다.'
        : '포트폴리오 분석과 정식추천 검증 작업을 실행합니다.',
      timeoutSeconds: Math.floor(timeoutMs / 1000),
      stagnantStage: false,
    });
    setApiError('');
    try {
      const hedgeBudgetKrw = selectedPortfolio?.totalValue ? Math.round(selectedPortfolio.totalValue * 0.1) : '';
      const refreshJob = await refreshMarketData({
        mode,
        forceFullRefresh,
        portfolioRows: selectedPortfolio ? toBackendPortfolioRows(selectedPortfolio, { usdKrwRate }) : undefined,
        hedgeBudgetKrw,
        maxComboSize: 2,
        useLivePrices: true,
      });
      if (refreshJob.status === 'skipped_latest' || refreshJob.status === 'completed') {
        setRunState((prev) => ({
          ...prev,
          running: false,
          stage: refreshJob.result?.reason || `${label} 완료`,
          error: '',
        }));
        await loadBackendDashboard();
        return;
      }
      const finalStatus = await pollRunStatus(refreshJob.jobId, (status) => {
        setRunState((prev) => ({
          ...prev,
          running: true,
          jobId: status.jobId || refreshJob.jobId,
          stage: status.stage || status.status || `${label} 진행 중`,
          currentStep: status.currentStep || status.stage || `${label} 진행 중`,
          estimatedRemainingMessage: status.estimatedRemainingMessage || '',
          elapsedSeconds: status.elapsedSeconds ?? prev.elapsedSeconds,
          timeoutSeconds: status.timeoutSeconds ?? prev.timeoutSeconds,
          stagnantStage: Boolean(status.stagnantStage),
          error: '',
        }));
      }, { intervalMs: 3000, timeoutMs });
      if (finalStatus.status !== 'completed') {
        throw new Error(finalStatus.error || `${label} 작업이 완료되지 않았습니다.`);
      }
      setRunState((prev) => ({
        ...prev,
        running: false,
        stage: `${label} 완료. 최신 상태를 다시 확인하는 중`,
        error: '',
      }));
      await loadBackendDashboard();
    } catch (error) {
      setRunState((prev) => ({
        ...prev,
        running: false,
        stage: '',
        error: error.message || `${label} 중 오류가 발생했습니다.`,
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
          {reportModel?.activeRunId && <p className="text-secondary text-xs mt-1">분석 run: {reportModel.activeRunId} · freshness: {reportModel.freshnessStatus || 'unknown'}</p>}
        </div>
        <div className="flex gap-3" style={{ flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          <Button variant="secondary" onClick={loadBackendDashboard} disabled={isLoading || runState.running}>
            {isLoading ? <Loader2 size={14} className="spin-icon" /> : <RefreshCw size={14} />} 저장된 결과 확인
          </Button>
          <Button variant="secondary" onClick={() => handleRefreshMarketDataMode()} disabled={isLoading || runState.running}>
            <RefreshCw size={14} /> {'\uC2DC\uC7A5\uB370\uC774\uD130 \uBE60\uB978 \uAC31\uC2E0'}
          </Button>
          <Button
            variant="secondary"
            onClick={() => handleRefreshMarketDataMode({ mode: 'portfolio_reanalysis', label: '\uC815\uC2DD\uCD94\uCC9C \uAC80\uC99D' })}
            disabled={!selectedPortfolio || isLoading || runState.running}
          >
            <Shield size={14} /> {'\uC815\uC2DD\uCD94\uCC9C \uAC80\uC99D'}
          </Button>
          <Button
            variant="secondary"
            onClick={() => handleRefreshMarketDataMode({ mode: 'full_rebuild', label: '\uC804\uCCB4 \uC7AC\uBE4C\uB4DC', forceFullRefresh: true })}
            disabled={isLoading || runState.running}
          >
            <RefreshCw size={14} /> {'\uC804\uCCB4 \uC7AC\uBE4C\uB4DC'}
          </Button>
          <Button variant="primary" onClick={handleRunAnalysis} disabled={!selectedPortfolio || runState.running}>
            {runState.running ? <Loader2 size={14} className="spin-icon" /> : <Rocket size={14} />} {'\uD3EC\uD2B8\uD3F4\uB9AC\uC624 \uC7AC\uBD84\uC11D'}
          </Button>
        </div>
      </div>

      {runState.stage && (
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
            <h3>HedgeMate 백엔드 연결 실패</h3>
            <p>{apiError}</p>
            <p className="text-xs text-secondary mt-2">백엔드가 꺼져 있으면 프론트는 대기 상태로 남습니다. `python HedgeMate/scripts/serve_dashboard.py --host 127.0.0.1 --port 8766`로 서버를 켠 뒤 다시 조회하세요.</p>
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
              단계: 분석 시작 → 가격 조회 → HedgeMate pipeline 실행 → backtest/gate 검증 → active bundle 갱신 → 완료/실패
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
        <section className="analysis-required-card mt-6">
          <div>
            <span className="decision-badge">분석 대기</span>
            <h3>이 포트폴리오에 대한 최신 분석 결과가 없습니다</h3>
            <p>
              이 포트폴리오에 대한 최신 분석 결과가 없습니다. 분석을 실행해야 리포트를 볼 수 있습니다.
            </p>
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
              <strong>{runState.error ? '분석 실패' : reportModel?.productStatus || (previewError ? 'preview 실패' : portfolioPreview?.canRunAnalysis ? '분석 가능' : 'preview 확인 중')}</strong>
            </div>
          </div>
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
          <div className="flex gap-3 mt-5">
            <Button variant="primary" onClick={handleRunAnalysis} disabled={runState.running || (portfolioPreview && !portfolioPreview.canRunAnalysis)}>
              <Rocket size={14} /> 이 포트폴리오로 분석 생성
            </Button>
            <Button variant="secondary" onClick={loadBackendDashboard} disabled={isLoading}>
              <RefreshCw size={14} /> 저장된 결과 다시 확인
            </Button>
          </div>
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
                ? <span>정식 추천 {reportModel.decisionBanner.counts.formalRecommendations}</span>
                : <span>추천 gate 통과 없음</span>}
              <span>검증 액션 {reportModel.decisionBanner.counts.formal}</span>
              <span>REVIEW {reportModel.decisionBanner.counts.review}</span>
              <span>FAIL {reportModel.decisionBanner.counts.fail}</span>
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
                <span className="eyebrow">Portfolio Vulnerability Top 3</span>
                <h3>내 포트폴리오가 먼저 약한 곳</h3>
              </div>
              <span className="text-xs text-secondary">백엔드 portfolioVulnerabilitySummary 기준</span>
            </div>
            <div className="top-vulnerability-grid">
              {reportModel.topVulnerabilities.slice(0, 3).map((item) => (
                <article className="top-vulnerability-card" key={`top-${item.riskSleeve}`}>
                  <div className="flex justify-between items-start gap-3">
                    <div>
                      <span className="rank-chip">#{item.rank}</span>
                      <h4>{item.label}</h4>
                    </div>
                    <div className="vuln-score">
                      <strong>{item.netVulnerability.toFixed(4)}</strong>
                      <span>{item.contributionPct.toFixed(1)}%</span>
                    </div>
                  </div>
                  <p className="text-xs text-secondary mt-3">
                    이 취약성은 주로 {item.sourceHoldings.map((holding) => holding.ticker).join(', ') || '보유자산'} 비중에서 발생합니다.
                  </p>
                  <div className="cause-asset-list">
                    {item.sourceHoldings.slice(0, 4).map((holding) => (
                      <span key={`${item.riskSleeve}-${holding.ticker}`}>{holding.ticker}</span>
                    ))}
                    {item.offsetHoldings.length > 0 && (
                      <span className="offset-pill">offset {item.offsetHoldings.slice(0, 2).map((holding) => holding.ticker || holding.asset_ticker || holding).join(', ')}</span>
                    )}
                  </div>
                </article>
              ))}
            </div>
            <div className="source-attribution-strip">
              <div>
                <span className="eyebrow">Source Holdings</span>
                <h4>취약성을 만든 보유자산</h4>
              </div>
              <div className="source-asset-pills">
                {reportModel.attributionRows.slice(0, 6).map((row) => (
                  <span key={`source-pill-${row.id}`}>
                    {row.asset} · {row.riskSleeveLabel} {row.contributionPct.toFixed(1)}%
                  </span>
                ))}
              </div>
            </div>
          </section>

          <section className="chart-card mt-6" data-testid="vulnerability-prescriptions">
            <div className="flex justify-between items-start gap-4 mb-4">
              <div>
                <span className="eyebrow">Vulnerability Prescriptions</span>
                <h3 className="font-semibold">취약점별 헷징 처방</h3>
                <p className="text-xs text-secondary mt-1">
                  금, 미국채, 현금성 자산도 해당 취약점을 직접 낮춘 근거가 있을 때만 처방으로 표시하고, 아니면 benchmark로 낮춰 표시합니다.
                </p>
              </div>
              <span className="decision-badge">{reportModel.productStatus}</span>
            </div>
            <div className="action-card-grid">
              {reportModel.prescriptionRows.map((row) => {
                const candidate = row.candidate;
                return (
                  <article className="action-card" key={row.id} data-testid="prescription-card">
                    <div className="flex justify-between items-start gap-3">
                      <div>
                        <span className={`grade-badge grade-${row.grade.toLowerCase()}`}>{row.gradeLabel}</span>
                        <h4>{row.vulnerability.label}</h4>
                      </div>
                      <span className="text-xs text-secondary">#{row.vulnerability.rank}</span>
                    </div>
                    <p className="text-xs text-secondary mt-3">
                      줄일 자산: {row.sourceAssets.join(', ') || '보유자산 확인 필요'}
                    </p>
                    <div className="action-route mt-3">
                      {candidate?.sourceAsset || row.sourceAssets.join(', ') || '-'} → {candidate?.hedgeAsset || '직접 후보 없음'}
                    </div>
                    <p className="text-xs mt-3">{row.reason}</p>
                    {candidate?.reason && <p className="text-xs text-secondary mt-2">{candidate.reason}</p>}
                    <div className="action-mini-metrics">
                      <span>취약점 개선 {Number(candidate?.improvePct || 0).toFixed(1)}%</span>
                      <span>{row.directMatch ? '직접 처방 근거 있음' : 'benchmark 표시'}</span>
                      {candidate?.metricRows?.slice(0, 3).map((metric) => (
                        <span key={`${row.id}-${metric.key}`}>{metric.label} {metric.improvementText}</span>
                      ))}
                    </div>
                  </article>
                );
              })}
            </div>
          </section>

          <div className="metric-tabs flex gap-2 mt-6">
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
          <p className="text-xs text-secondary mt-2 metric-helper">
            {METRIC_DEFINITIONS[selectedMetric].label}: {METRIC_DEFINITIONS[selectedMetric].helper}
          </p>

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
                        {selectedPortfolio.assets.map((asset) => `${asset.ticker || asset.name} (${asset.weight ?? '-'}%)`).join(', ')}
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
                        <h3 className="font-semibold text-primary">{portfolioData.labels[type]}</h3>
                        <span className={index === 1 ? 'badge-blue' : 'badge-purple'}>{action?.badge || 'NO ACTION'}</span>
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
                          <div className="text-sm">{action ? sourceAssetsText(action) : '추가 분석 필요'}</div>
                          {action?.rejectedReasonKo && <div className="text-xs text-secondary mt-3">{action.rejectedReasonKo}</div>}
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
                <div className="flex justify-between items-center mb-6">
                  <div>
                    <h3 className="font-semibold">{METRIC_DEFINITIONS[selectedMetric].label} 비교</h3>
                    <p className="text-xs text-secondary mt-1">{METRIC_DEFINITIONS[selectedMetric].helper}</p>
                  </div>
                  <div className="flex gap-4 text-xs text-secondary chart-legend">
                    <span className="flex items-center gap-1"><span className="dot dot-dark"></span> 현재</span>
                    <span className="flex items-center gap-1"><span className="dot dot-purple"></span> 검토 액션 1</span>
                    <span className="flex items-center gap-1"><span className="dot dot-blue"></span> 검토 액션 2</span>
                  </div>
                </div>

                {['base', 'recommended', 'optimized'].map((type) => (
                  <div className={`bar-row ${type !== 'base' ? 'mt-6' : ''}`} key={type}>
                    <div className={`flex justify-between text-xs mb-2 ${type === 'base' ? 'text-secondary' : type === 'recommended' ? 'text-accent-light' : 'text-blue'}`}>
                      <span>{portfolioData.labels[type]}</span>
                      <span>{formatMetricValue(portfolioData[type][selectedMetric], selectedMetric)} ({getImproveText(portfolioData, type, selectedMetric)})</span>
                    </div>
                    <div className="bar-container"><div className={`bar ${type === 'base' ? 'bar-dark' : type === 'recommended' ? 'bar-purple' : 'bar-blue'}`} style={{ width: animateBars ? `${calcBarWidth(portfolioData, type, selectedMetric)}%` : '0%' }}></div></div>
                  </div>
                ))}
              </div>

              <div className="info-cards flex gap-4 mt-6">
                <div className="info-card flex gap-4 items-center">
                  <div className="icon-box purple-bg"><Shield size={20} className="text-accent-light" /></div>
                  <div>
                    <h4 className="font-semibold text-sm">취약점 중심 액션</h4>
                    <p className="text-xs text-secondary mt-1">{reportModel.actionCards[0]?.plainKoreanReason || reportModel.actionCards[0]?.actionReasonKo || '백엔드 hedgeActionPlan 기준으로 포트폴리오 취약성을 줄이는 액션만 표시합니다.'}</p>
                  </div>
                </div>
                <div className="info-card flex gap-4 items-center">
                  <div className="icon-box blue-bg"><Rocket size={20} className="text-blue" /></div>
                  <div>
                    <h4 className="font-semibold text-sm">왜 검토 단계인가</h4>
                    <p className="text-xs text-secondary mt-1">{reportModel.actionCards[0]?.statusReasonKo || reportModel.decisionBanner.summary}</p>
                  </div>
                </div>
              </div>
            </>
          )}

          <div className="vulnerability-grid mt-6">
            <section className="chart-card">
              <h3 className="font-semibold mb-2">포트폴리오 취약점 요약</h3>
              <p className="text-xs text-secondary mb-4">risk sleeve별로 어떤 시장국면에 약한지 백엔드 attribution 기준으로 정리합니다.</p>
              <div className="vulnerability-list">
                {reportModel.topVulnerabilities.slice(0, 5).map((item) => (
                  <div className="vulnerability-item" key={item.riskSleeve}>
                    <div>
                      <div className="font-semibold text-sm">{item.label}</div>
                      <div className="text-xs text-secondary mt-1">
                        원인 자산: {item.sourceHoldings.map((holding) => holding.ticker).join(', ') || '없음'}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-semibold text-accent-light">{item.netVulnerability.toFixed(4)}</div>
                      <div className="text-xs text-secondary">{item.contributionPct.toFixed(1)}%</div>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <section className="chart-card">
              <h3 className="font-semibold mb-2">왜 검증 통과 액션이 아닌가</h3>
              <p className="text-xs text-secondary mb-4">REVIEW_ACTION은 검토 시뮬레이션 후보입니다. 최종 판단은 추가 검증 이후에만 가능합니다.</p>
              <div className="blocker-list">
                {reportModel.decisionBanner.blockers.length > 0 ? reportModel.decisionBanner.blockers.map((blocker) => (
                  <span className="blocker-pill" key={blocker}>{blocker}</span>
                )) : <span className="blocker-pill">추가 검증 필요</span>}
              </div>
              {reportModel.decisionBanner.upgradeRequirements.length > 0 && (
                <ul className="upgrade-list">
                  {reportModel.decisionBanner.upgradeRequirements.slice(0, 4).map((item) => <li key={item}>{item}</li>)}
                </ul>
              )}
              {reportModel.decisionBanner.actionTypeCoverage.length > 0 && (
                <div className="mt-4">
                  <h4 className="text-xs font-semibold mb-2">액션 유형 커버리지</h4>
                  <div className="blocker-list">
                    {reportModel.decisionBanner.actionTypeCoverage.map((item) => (
                      <span className="blocker-pill" key={item.actionType}>
                        {item.label} {item.selectedCount}/{item.candidateCount}
                      </span>
                    ))}
                  </div>
                  <ul className="upgrade-list">
                    {reportModel.decisionBanner.actionTypeCoverage
                      .filter((item) => item.presentInCandidates && !item.presentInSelected && item.absenceReasonKo)
                      .slice(0, 3)
                      .map((item) => <li key={`${item.actionType}-reason`}>{item.label}: {item.absenceReasonKo}</li>)}
                  </ul>
                </div>
              )}
            </section>
          </div>

          <section className="chart-card mt-6">
            <div className="flex justify-between items-center mb-4">
              <div>
                <h3 className="font-semibold">선택된 검토 액션</h3>
                <p className="text-xs text-secondary mt-1">메인 액션 카드는 hedgeActionPlan의 selected action만 사용합니다.</p>
              </div>
            </div>
            {reportModel.actionCards.length === 0 && reportModel.candidateRows.length > 0 && (
              <div className="candidate-gate-summary mb-4">
                <strong>평가 후보 {reportModel.decisionBanner.counts.evaluatedCandidates}개 · 최종 선택 액션 0개</strong>
                <span>
                  후보는 계산됐지만 backtest/formal gate를 통과하지 못해 메인 액션 카드로 승격되지 않았습니다.
                  아래 후보 테이블에서 각 후보와 실패 사유를 확인할 수 있습니다.
                </span>
              </div>
            )}
            {reportModel.actionCards.length === 0 && reportModel.candidateRows.length > 0 && (
              <div className="review-candidate-grid mb-4">
                {reportModel.candidateRows.slice(0, 3).map((candidate, index) => (
                  <article className="review-candidate-card" key={`review-${candidate.id}`}>
                    <div className="flex justify-between items-start gap-3">
                      <div>
                        <span className={`action-status ${actionStatusClass(candidate.status)}`}>
                          {index === 0 ? 'BEST 검토 후보' : '검토 후보'}
                        </span>
                        <span className={`grade-badge grade-${(candidate.recommendationGrade || 'none').toLowerCase()}`}>
                          {candidate.recommendationGradeLabel}
                        </span>
                        <h4>{actionTypeLabel(candidate.actionType)} · {candidate.hedgeAsset || '-'}</h4>
                      </div>
                      <span className="text-xs text-secondary">#{index + 1}</span>
                    </div>
                    <div className="action-route mt-3">{candidate.sourceAsset || '-'} → {candidate.hedgeAsset || '-'}</div>
                    <p className="text-xs text-secondary mt-3">{candidate.riskSleeveLabel}</p>
                    <p className="text-xs mt-3">{candidate.reason || 'gate 미통과로 공식 추천이 아닙니다.'}</p>
                    <div className="action-mini-metrics">
                      <span>취약성 개선 후보값 {candidate.improvePct.toFixed(1)}%</span>
                      <span>공식 추천 아님 · gate 미통과</span>
                    </div>
                  </article>
                ))}
              </div>
            )}
            <div className="action-card-grid">
              {reportModel.actionCards.slice(0, 6).map((action) => (
                <article className="action-card" key={action.id}>
                  <div className="flex justify-between items-start gap-3">
                    <div>
                      <span className={`action-status ${actionStatusClass(action.displayStatus || action.actionStatus)}`}>{action.badge}</span>
                      <span className={`grade-badge grade-${(action.recommendationGrade || 'none').toLowerCase()}`}>
                        {action.recommendationGradeLabel}
                      </span>
                      <h4>{action.title}</h4>
                    </div>
                    <span className="text-xs text-secondary">#{action.rank}</span>
                  </div>
                  <p className="text-xs text-secondary mt-3">{action.riskSleeveLabel}</p>
                  <div className="action-route mt-3">{sourceAssetsText(action)}</div>
                  <p className="text-xs mt-3">{action.expectedEffect || action.actionReasonKo}</p>
                  {action.recommendationGradeReason && (
                    <p className="text-xs text-secondary mt-2">{action.recommendationGradeReason}</p>
                  )}
                  <div className="action-mini-metrics">
                    <span>CVaR {formatMetricDelta(action.baseMetrics.cvar, action.proposedMetrics.cvar, 'cvar')}</span>
                    <span>MDD {formatMetricDelta(action.baseMetrics.mdd, action.proposedMetrics.mdd, 'mdd')}</span>
                    <span>Sharpe {formatMetricDelta(action.baseMetrics.sharpe, action.proposedMetrics.sharpe, 'sharpe')}</span>
                    {Number.isFinite(action.prescriptionScore) && <span>처방 점수 {action.prescriptionScore.toFixed(1)}</span>}
                    {action.basisRiskLevel && <span>basis risk {action.basisRiskLevel}</span>}
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section className="chart-card mt-6">
            <h3 className="font-semibold mb-2">취약점 기여 자산</h3>
            <p className="text-xs text-secondary mb-4">보유자산이 어떤 risk sleeve 취약성을 만들었는지 contribution 기준으로 봅니다.</p>
            <div className="data-table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>자산</th>
                    <th>취약점</th>
                    <th>현재 비중</th>
                    <th>기여도</th>
                    <th>근거 품질</th>
                    <th>설명</th>
                  </tr>
                </thead>
                <tbody>
                  {reportModel.attributionRows.slice(0, 10).map((row) => (
                    <tr key={row.id}>
                      <td>{row.asset}</td>
                      <td>{row.riskSleeveLabel}</td>
                      <td>{row.currentWeight.toFixed(1)}%</td>
                      <td>{row.contributionPct.toFixed(1)}%</td>
                      <td>{row.evidenceQuality || '-'}</td>
                      <td>{row.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <details className="chart-card mt-6 candidate-details">
            <summary>전체 후보와 근거 보기</summary>
            <p className="text-xs text-secondary mt-3 mb-4">hedgeActionCandidates는 메인 액션이 아니라 전체 후보와 근거 테이블로만 표시합니다.</p>
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
                      <td>{row.sourceAsset}</td>
                      <td>{row.hedgeAsset}</td>
                      <td>{row.improvePct.toFixed(1)}%</td>
                      <td>{row.reason}</td>
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
