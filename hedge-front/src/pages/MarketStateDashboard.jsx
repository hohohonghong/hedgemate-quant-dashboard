import React, { useEffect, useMemo, useState } from 'react';
import { AlertCircle, Database, RefreshCw, TrendingDown, TrendingUp } from 'lucide-react';
import { Button } from '../components/Button';
import { getScenarioDashboard, getScenarioRuns, getScenarioSensitivities, pollRunStatus, refreshMarketData } from '../services/hedgemateApi';
import { buildMarketStateAssetGuide } from '../services/marketStateAssetGuide';
import { ASSET_DATABASE } from '../utils/helpers';
import './MarketStateDashboard.css';

const REFRESH_CHECKING_MESSAGE = '\uC7A5\uC911 3\uC2DC\uAC04 nowcast \uAE30\uC900\uC810\uC744 \uD655\uC778\uD558\uB294 \uC911\uC785\uB2C8\uB2E4.';
const REFRESH_RUNNING_MESSAGE = '\uCD5C\uC2E0 \uC7A5\uC911 \uB370\uC774\uD130\uB85C nowcast\uB97C \uAC31\uC2E0\uD558\uB294 \uC911\uC785\uB2C8\uB2E4.';
const REFRESH_CURRENT_MESSAGE = '\uCD5C\uC2E0 3\uC2DC\uAC04 nowcast \uAE30\uC900\uC810\uC785\uB2C8\uB2E4.';
const MARKET_STATE_TABS = [
  { id: 'summary', label: '요약' },
  { id: 'lens', label: '관점별 국면 분류' },
  { id: 'shortTerm', label: '단기 보조 신호' },
];

const toNumber = (value, fallback = null) => {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
};

const formatNumber = (value, digits = 2) => {
  const number = toNumber(value);
  if (number === null) return '-';
  return number.toFixed(digits);
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

const stateTone = (state) => {
  const normalized = String(state || '').toUpperCase();
  if (['ACTIVE', 'STRONG', 'RISK_ON', 'PASS', 'OK'].includes(normalized)) return 'positive';
  if (['WATCH', 'STRESS', 'WARN', 'PROVISIONAL'].includes(normalized)) return 'warning';
  if (['OFF', 'NEUTRAL', 'INSUFFICIENT_HISTORY'].includes(normalized)) return 'neutral';
  return 'muted';
};

const scenarioLabel = (row) => row?.scenario_name_ko || row?.scenario_name || row?.scenario_code || row?.nowcast_name_ko || row?.nowcast_code || '시장국면';

const progressStyle = (score) => ({
  width: `${Math.max(0, Math.min(100, toNumber(score, 0)))}%`,
});

const ScenarioCard = ({ row, compact = false }) => {
  const state = row.final_display_state || row.display_state || row.structured_display_state || row.status || row.raw_state;
  const score = row.final_score ?? row.score ?? row.structured_score;
  const confidence = row.final_confidence ?? row.confidence ?? row.structured_confidence;
  return (
    <article className={`market-scenario-card ${compact ? 'compact' : ''}`}>
      <div className="market-card-head">
        <div>
          <h3>{scenarioLabel(row)}</h3>
          <p>{row.scenario_name || row.scenario_code || row.lens || row.nowcast_code || '-'}</p>
        </div>
        <span className={`state-chip ${stateTone(state)}`}>{state || '-'}</span>
      </div>
      <div className="score-line">
        <span>Score {formatNumber(score)}</span>
        <strong>Confidence {formatNumber(confidence)}</strong>
      </div>
      <div className="score-meter">
        <div className="score-meter-fill" style={progressStyle(score)} />
      </div>
      {row.market_interpretation_ko && <p className="market-interpretation">{row.market_interpretation_ko}</p>}
    </article>
  );
};

const guideDescription = (type) => (
  type === 'interest'
    ? '현재 활성 국면에서 방어/상쇄 신호가 확인된 자산'
    : '현재 활성 국면에서 취약 신호가 확인된 자산'
);

const FRIENDLY_ASSET_NAMES = {
  FXY: '일본 엔화 ETF',
  FXF: '스위스 프랑 ETF',
  FXE: '유로화 ETF',
  IAU: '금 ETF',
  GLD: '금 ETF',
  TAIL: '테일위험 방어 ETF',
  EWY: '한국 ETF',
  UUP: '달러 ETF',
  TLT: '장기 미국국채 ETF',
  IEF: '중기 미국국채 ETF',
  SHY: '단기 미국국채 ETF',
  SPY: 'S&P 500 ETF',
  QQQ: 'Nasdaq 100 ETF',
  HYG: '하이일드 채권 ETF',
  '005930.KS': '삼성전자',
  '000660.KS': 'SK하이닉스',
  '051910.KS': 'LG화학',
  '035720.KS': '카카오',
  '032830.KS': '삼성생명',
  '000270.KS': '기아',
};

const displayAssetName = (asset) => {
  const ticker = String(asset.ticker || '').toUpperCase();
  const rawName = String(asset.assetName || '').trim();
  if (rawName && rawName.toUpperCase() !== ticker) return rawName;
  return ASSET_DATABASE[ticker]?.name || FRIENDLY_ASSET_NAMES[ticker] || rawName || ticker;
};

const shortReason = (asset, type) => {
  const scenario = asset.matchedScenarios?.[0] || '현재 장세';
  const notes = String(asset.notes || '').trim();
  if (notes && notes.length <= 54 && !/^[a-z0-9_ -]+$/i.test(notes)) return notes;
  return type === 'interest'
    ? `${scenario} 방어/상쇄 신호`
    : `${scenario} 취약 신호`;
};

const AssetGuideCard = ({ asset, type }) => (
  <article className={`market-asset-guide-card ${type}`} title={guideDescription(type)}>
    <h3>{asset.ticker}</h3>
    <p className="asset-guide-name">{displayAssetName(asset)}</p>
    <p className="asset-guide-desc">{shortReason(asset, type)}</p>
  </article>
);

const AssetGuideColumn = ({ title, helper, assets, type }) => (
  <div className="asset-guide-column">
    <div className="asset-guide-column-head">
      <h3>
        {type === 'interest' ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
        {title}
      </h3>
      <span>{helper}</span>
    </div>
    {assets.length ? (
      <div className="asset-guide-card-stack">
        {assets.slice(0, 6).map((asset) => (
          <AssetGuideCard key={asset.ticker} asset={asset} type={type} />
        ))}
      </div>
    ) : (
      <div className="market-empty compact">해당 방향의 자산 신호가 없습니다.</div>
    )}
  </div>
);

const MarketSummaryCard = ({ dashboard, activeScenarios, stateCounts }) => {
  const primary = activeScenarios[0] || {};
  const primaryState = primary.final_display_state || primary.display_state || primary.status || 'ACTIVE';
  const primaryScore = primary.final_score ?? primary.score ?? primary.activation_weight;
  const primaryConfidence = primary.final_confidence ?? primary.confidence;
  const activeCount = stateCounts.find((item) => String(item.state).toUpperCase() === 'ACTIVE')?.count ?? activeScenarios.length;
  const watchCount = stateCounts.find((item) => String(item.state).toUpperCase() === 'WATCH')?.count ?? 0;
  const offCount = stateCounts.find((item) => String(item.state).toUpperCase() === 'OFF')?.count ?? 0;
  const intradayStatus = dashboard.intradayNowcastStatus || {};
  const intradayReferenceText = formatKstDateTime(intradayStatus.latestTimestampKst);
  const nowcastWindowText = intradayStatus.bucketHours ? `${intradayStatus.bucketHours}시간 nowcast` : '장중 nowcast';
  const referenceText = intradayReferenceText
    ? `장중 기준 ${intradayReferenceText} · ${nowcastWindowText}`
    : dashboard.asOfDate || dashboard.dataAsOfDate || '-';
  const summaryCopy = primary.market_interpretation_ko
    || dashboard.dataFreshnessNote
    || '현재 활성 시장국면과 장중 nowcast 데이터를 기준으로 장세를 요약합니다.';

  return (
    <section className="market-simple-summary mt-6">
      <div className="market-simple-copy">
        <span className="summary-kicker">현재 장세 진단 · {referenceText}</span>
        <div className="summary-title-row">
          <h2>{scenarioLabel(primary)}</h2>
          <span className={`state-chip ${stateTone(primaryState)}`}>{primaryState}</span>
        </div>
        <p>{summaryCopy}</p>
        <div className="summary-chip-row">
          <strong>동시 활성:</strong>
          {activeScenarios.slice(0, 3).map((row) => (
            <span className={`summary-scenario-chip ${stateTone(row.final_display_state || row.display_state)}`} key={row.scenario_code}>
              <span>{scenarioLabel(row)}</span>
              <small>
                {row.final_display_state || row.display_state || 'ACTIVE'}
                {' · 점수 '}
                {formatNumber(row.final_score ?? row.score ?? row.activation_weight, 1)}
                {' · 신뢰도 '}
                {formatNumber(row.final_confidence ?? row.confidence, 1)}
              </small>
            </span>
          ))}
        </div>
      </div>
      <div className="market-simple-score">
        <strong>{formatNumber(primaryScore, 1)}</strong>
        <span>SCORE</span>
        <p>신뢰도 {formatNumber(primaryConfidence, 1)}</p>
        <div className="score-meter">
          <div className="score-meter-fill" style={progressStyle(primaryScore)} />
        </div>
        <div className="summary-count-row">
          <span className="state-chip positive">ACTIVE {activeCount}</span>
          <span className="state-chip neutral">OFF {offCount}</span>
          <span className="state-chip warning">WATCH {watchCount}</span>
        </div>
      </div>
    </section>
  );
};

const MarketStateTabs = ({ activeTab, onTabChange }) => (
  <div className="market-state-tabs mt-6" role="tablist" aria-label="현재 시장 국면 보기">
    {MARKET_STATE_TABS.map((tab) => (
      <button
        type="button"
        role="tab"
        id={`market-state-tab-${tab.id}`}
        aria-controls={`market-state-panel-${tab.id}`}
        aria-selected={activeTab === tab.id}
        className={activeTab === tab.id ? 'active' : ''}
        key={tab.id}
        onClick={() => onTabChange(tab.id)}
      >
        {tab.label}
      </button>
    ))}
  </div>
);

const LensSummaryPanel = ({ lensSummary, stateCounts }) => (
  <section className="market-tab-panel mt-4" id="market-state-panel-lens" role="tabpanel" aria-labelledby="market-state-tab-lens">
    <article className="market-panel">
      <div className="market-section-head">
        <div>
          <span>Lens Summary</span>
          <h2>관점별 국면 분류</h2>
        </div>
      </div>
      <div className="state-chip-row">
        {stateCounts.map((item) => (
          <span className={`state-chip ${stateTone(item.state)}`} key={item.state}>{item.state} {item.count}</span>
        ))}
      </div>
      <div className="market-scenario-stack mt-4">
        {lensSummary.length
          ? lensSummary.map((row) => (
            <article className="market-scenario-card compact" key={row.lens}>
              <div className="market-card-head">
                <div>
                  <h3>{row.lens}</h3>
                  <p>{row.topScenario || '대표 시나리오 없음'}</p>
                </div>
                <span className="section-chip">{row.count}개</span>
              </div>
              <div className="score-line">
                <span>Top score</span>
                <strong>{formatNumber(row.topScore)}</strong>
              </div>
              <div className="score-meter">
                <div className="score-meter-fill" style={progressStyle(row.topScore)} />
              </div>
            </article>
          ))
          : <div className="market-empty">관점별 요약 데이터가 없습니다.</div>}
      </div>
    </article>
  </section>
);

const ShortTermSignalsPanel = ({ nowcastLeaders }) => {
  return (
    <section className="market-tab-panel mt-4" id="market-state-panel-shortTerm" role="tabpanel" aria-labelledby="market-state-tab-shortTerm">
      <article className="market-panel">
        <div className="market-section-head">
          <div>
            <span>Nowcast & Event Overlay</span>
            <h2>단기 보조 신호</h2>
          </div>
        </div>
        <div className="market-scenario-stack">
          {nowcastLeaders.length
            ? nowcastLeaders.slice(0, 4).map((row, index) => (
              <ScenarioCard key={`${row.nowcast_code || index}-nowcast`} row={row} compact />
            ))
            : <div className="market-empty">단기 nowcast 신호가 없습니다.</div>}
        </div>
      </article>
    </section>
  );
};

export const MarketStateDashboard = () => {
  const [runs, setRuns] = useState([]);
  const [selectedRun, setSelectedRun] = useState('');
  const [dashboard, setDashboard] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [refreshStatus, setRefreshStatus] = useState('');
  const [error, setError] = useState('');
  const [scenarioSensitivityPayload, setScenarioSensitivityPayload] = useState(null);
  const [assetGuideError, setAssetGuideError] = useState('');
  const [activeTab, setActiveTab] = useState('summary');

  const loadDashboard = async (runId = '', options = {}) => {
    setIsLoading(true);
    setError('');
    setAssetGuideError('');
    try {
      const data = await getScenarioDashboard(runId, options);
      setDashboard(data);
      setRuns((previousRuns) => data.runs || previousRuns);
      setSelectedRun(data.runId || runId || '');
      try {
        const sensitivities = await getScenarioSensitivities({
          signal: options.signal,
          timeoutMs: options.timeoutMs,
        });
        setScenarioSensitivityPayload(sensitivities);
      } catch (sensitivityError) {
        if (sensitivityError.name === 'AbortError') return;
        setScenarioSensitivityPayload({ rows: [] });
        setAssetGuideError(sensitivityError.message || '자산 민감도 데이터를 불러오지 못했습니다.');
      }
    } catch (err) {
      if (err.name === 'AbortError') return;
      setError(err.message || '시장국면 진단 결과를 불러오지 못했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();
    const bootstrap = async () => {
      setIsLoading(true);
      setIsRefreshing(true);
      setRefreshStatus(REFRESH_CHECKING_MESSAGE);
      setError('');
      try {
        const refreshJob = await refreshMarketData({
          mode: 'intraday_nowcast',
          useLivePrices: true,
          autoRefresh: true,
        }, { signal: controller.signal, timeoutMs: 30 * 1000 });
        if (cancelled) return;
        if (refreshJob.status === 'skipped_latest' || refreshJob.status === 'completed') {
          setRefreshStatus(refreshJob.result?.reason || REFRESH_CURRENT_MESSAGE);
        } else if (refreshJob.jobId) {
          setRefreshStatus(REFRESH_RUNNING_MESSAGE);
          const finalStatus = await pollRunStatus(refreshJob.jobId, (status) => {
            if (!cancelled) {
              setRefreshStatus(status.currentStep || status.stage || REFRESH_RUNNING_MESSAGE);
            }
          }, { signal: controller.signal, intervalMs: 3000, timeoutMs: 30 * 60 * 1000 });
          if (finalStatus.status !== 'completed') {
            throw new Error(finalStatus.error || '\uC2DC\uC7A5\uB370\uC774\uD130 \uAC31\uC2E0\uC774 \uC644\uB8CC\uB418\uC9C0 \uC54A\uC558\uC2B5\uB2C8\uB2E4.');
          }
          setRefreshStatus(REFRESH_CURRENT_MESSAGE);
        }
        const runPayload = await getScenarioRuns({ signal: controller.signal });
        if (cancelled) return;
        setRuns(runPayload.runs || []);
        const latestRun = runPayload.latestRunId || runPayload.runs?.[0] || '';
        await loadDashboard(latestRun, { signal: controller.signal });
      } catch (err) {
        if (!cancelled) {
          setError(err.message || '시장국면 실행 목록을 불러오지 못했습니다.');
          setIsLoading(false);
        }
      } finally {
        if (!cancelled) {
          setIsRefreshing(false);
        }
      }
    };
    bootstrap();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, []);

  const activeScenarios = dashboard?.topActiveScenarios || [];
  const lensSummary = dashboard?.lensSummary || [];
  const stateCounts = dashboard?.stateCounts || [];
  const nowcastLeaders = dashboard?.nowcastLeaders || [];
  const assetGuide = useMemo(
    () => buildMarketStateAssetGuide(dashboard || {}, scenarioSensitivityPayload || { rows: [] }),
    [dashboard, scenarioSensitivityPayload]
  );

  const handleRunChange = async (event) => {
    const runId = event.target.value;
    setSelectedRun(runId);
    await loadDashboard(runId);
  };

  return (
    <div className="market-state-page">
      <div className="report-header flex justify-between items-start">
        <div>
          <span className="text-xs text-secondary font-semibold tracking-wider">MARKET STATE DASHBOARD</span>
          <h1 className="text-3xl font-bold mt-2">현재시장국면</h1>
          <p className="text-secondary mt-2">
            포트폴리오 처방에 들어가는 시장국면 입력값을 한 화면에서 확인합니다. 점수와 이벤트 보조신호는 실행 추천이 아니라 시장 상태 진단용입니다.
          </p>
        </div>
        <div className="market-controls">
          <select value={selectedRun} onChange={handleRunChange} disabled={isLoading || isRefreshing || runs.length === 0}>
            {runs.map((run) => <option key={run} value={run}>{run}</option>)}
          </select>
          <Button variant="secondary" onClick={() => loadDashboard(selectedRun)} disabled={isLoading || isRefreshing}>
            <RefreshCw size={14} className={isLoading ? 'spin-icon' : ''} /> 새로고침
          </Button>
        </div>
      </div>

      {refreshStatus && (
        <div className="market-status mt-6">
          <Database size={16} />
          <span>{refreshStatus}</span>
        </div>
      )}

      {error && (
        <div className="market-status error mt-6">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {isLoading && !dashboard ? (
        <div className="market-loading mt-6">
          <RefreshCw size={24} className="spin-icon" />
          <strong>시장국면 진단 결과를 불러오는 중입니다.</strong>
        </div>
      ) : dashboard && (
        <>
          <MarketStateTabs activeTab={activeTab} onTabChange={setActiveTab} />

          {activeTab === 'summary' && (
            <div className="market-tab-panel" id="market-state-panel-summary" role="tabpanel" aria-labelledby="market-state-tab-summary">
              <MarketSummaryCard dashboard={dashboard} activeScenarios={activeScenarios} stateCounts={stateCounts} />

              <section className="market-panel asset-guide-panel mt-6">
                <div className="market-section-head">
                  <div>
                    <span>이 장세의 추천 자산</span>
                    <h2>현재 시장국면 기반 자산 배분 가이드</h2>
                  </div>
                  <span className="section-chip">
                    {assetGuide.activeScenarios.length}개 국면 · {assetGuide.matchedRowCount}개 민감도 행
                  </span>
                </div>
                {assetGuideError && (
                  <div className="market-status error compact mb-4">
                    <AlertCircle size={16} />
                    <span>{assetGuideError}</span>
                  </div>
                )}
                {assetGuide.emptyMessage ? (
                  <div className="market-empty">{assetGuide.emptyMessage}</div>
                ) : (
                  <div className="asset-guide-grid">
                    <AssetGuideColumn
                      title="매수 관심 자산"
                      helper="방어/상쇄 신호"
                      assets={assetGuide.interestAssets}
                      type="interest"
                    />
                    <AssetGuideColumn
                      title="비중 축소 고려"
                      helper="취약 신호"
                      assets={assetGuide.reduceAssets}
                      type="reduce"
                    />
                  </div>
                )}
                <p className="asset-guide-footnote">* 시장국면 엔진 점수와 자산별 scenario sensitivity를 조합한 참고용 가이드입니다. 투자 추천이 아닙니다.</p>
              </section>
            </div>
          )}

          {activeTab === 'lens' && (
            <LensSummaryPanel lensSummary={lensSummary} stateCounts={stateCounts} />
          )}

          {activeTab === 'shortTerm' && (
            <ShortTermSignalsPanel nowcastLeaders={nowcastLeaders} />
          )}
        </>
      )}
    </div>
  );
};
