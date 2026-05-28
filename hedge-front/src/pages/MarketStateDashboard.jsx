import React, { useEffect, useMemo, useState } from 'react';
import { Activity, AlertCircle, BarChart3, CalendarDays, Database, FileText, RefreshCw, ShieldCheck, Signal } from 'lucide-react';
import { Button } from '../components/Button';
import { getScenarioDashboard, getScenarioRuns, pollRunStatus, refreshMarketData } from '../services/hedgemateApi';
import './MarketStateDashboard.css';

const REFRESH_CHECKING_MESSAGE = '\uC7A5\uC911 3\uC2DC\uAC04 nowcast \uAE30\uC900\uC810\uC744 \uD655\uC778\uD558\uB294 \uC911\uC785\uB2C8\uB2E4.';
const REFRESH_RUNNING_MESSAGE = '\uCD5C\uC2E0 \uC7A5\uC911 \uB370\uC774\uD130\uB85C nowcast\uB97C \uAC31\uC2E0\uD558\uB294 \uC911\uC785\uB2C8\uB2E4.';
const REFRESH_CURRENT_MESSAGE = '\uCD5C\uC2E0 3\uC2DC\uAC04 nowcast \uAE30\uC900\uC810\uC785\uB2C8\uB2E4.';

const toNumber = (value, fallback = null) => {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
};

const formatNumber = (value, digits = 2) => {
  const number = toNumber(value);
  if (number === null) return '-';
  return number.toFixed(digits);
};

const formatCount = (value) => {
  const number = toNumber(value);
  if (number === null) return '-';
  return Math.round(number).toLocaleString('ko-KR');
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

const MetricCard = ({ icon, label, value, helper }) => (
  <article className="market-metric-card">
    <div className="market-metric-icon">{icon}</div>
    <span>{label}</span>
    <strong>{value}</strong>
    <p>{helper}</p>
  </article>
);

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

export const MarketStateDashboard = () => {
  const [runs, setRuns] = useState([]);
  const [selectedRun, setSelectedRun] = useState('');
  const [dashboard, setDashboard] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [refreshStatus, setRefreshStatus] = useState('');
  const [error, setError] = useState('');

  const loadDashboard = async (runId = '', options = {}) => {
    setIsLoading(true);
    setError('');
    try {
      const data = await getScenarioDashboard(runId, options);
      setDashboard(data);
      setRuns((previousRuns) => data.runs || previousRuns);
      setSelectedRun(data.runId || runId || '');
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
  const topRows = dashboard?.topMarketRows || [];
  const lensSummary = dashboard?.lensSummary || [];
  const stateCounts = dashboard?.stateCounts || [];
  const vectorLeaders = dashboard?.scenarioVectorLeaders || [];
  const nowcastLeaders = dashboard?.nowcastLeaders || [];
  const validationMeta = dashboard?.validation?.metadata || {};
  const eventMeta = dashboard?.eventOverlay?.metadata || {};

  const overviewCards = useMemo(() => ([
    {
      label: '시장국면 실행',
      value: dashboard?.runId || '-',
      helper: dashboard?.generatedAt || '생성 시각 없음',
      icon: <Activity size={18} />,
    },
    {
      label: '국면 기준일',
      value: dashboard?.asOfDate || '-',
      helper: dashboard?.dataFreshnessNote || `데이터 기준 ${dashboard?.dataAsOfDate || '-'}`,
      icon: <CalendarDays size={18} />,
    },
    {
      label: '활성 국면',
      value: `${activeScenarios.length}개`,
      helper: 'STRESS / ACTIVE 중심으로 표시',
      icon: <Signal size={18} />,
    },
    {
      label: '최종 행 수',
      value: formatCount(dashboard?.meta?.finalRowCount),
      helper: dashboard?.meta?.pipelinePhase || 'final market state',
      icon: <Database size={18} />,
    },
    {
      label: '검증 케이스',
      value: `${formatCount(validationMeta.ok_case_count ?? dashboard?.meta?.validationOkCases)}/${formatCount(validationMeta.case_count ?? dashboard?.meta?.validationCases)}`,
      helper: 'OK / TOTAL',
      icon: <ShieldCheck size={18} />,
    },
    {
      label: '이벤트 보조신호',
      value: formatCount(eventMeta.article_count ?? dashboard?.meta?.eventArticleCount ?? dashboard?.meta?.overlayRowCount),
      helper: '뉴스/이벤트는 보조 신호로만 사용',
      icon: <BarChart3 size={18} />,
    },
  ]), [dashboard, activeScenarios.length, validationMeta, eventMeta]);

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
          <div className="market-status mt-6">
            <Activity size={16} />
            <span>
              실행 {dashboard.runId} · 화면 기준 {dashboard.asOfDate || '-'} · 데이터 기준 {dashboard.dataAsOfDate || '-'}
            </span>
          </div>

          <section className="market-overview-grid mt-6">
            {overviewCards.map((card) => (
              <MetricCard key={card.label} {...card} />
            ))}
          </section>

          <section className="market-section-grid mt-6">
            <article className="market-panel">
              <div className="market-section-head">
                <div>
                  <span>Final Market State</span>
                  <h2>상위 활성 시장국면</h2>
                </div>
                <span className="section-chip">{dashboard.asOfDate || '-'}</span>
              </div>
              <div className="market-scenario-stack">
                {activeScenarios.length
                  ? activeScenarios.map((row) => <ScenarioCard key={row.scenario_code} row={row} />)
                  : <div className="market-empty">활성 시장국면 데이터가 없습니다.</div>}
              </div>
            </article>

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

          <section className="market-section-grid lower mt-6">
            <article className="market-panel">
              <div className="market-section-head">
                <div>
                  <span>Scenario Vector</span>
                  <h2>현재 시나리오 벡터</h2>
                </div>
              </div>
              <div className="market-scenario-stack">
                {vectorLeaders.slice(0, 5).map((row, index) => (
                  <ScenarioCard key={`${row.scenario_code || index}-vector`} row={row} compact />
                ))}
              </div>
            </article>

            <article className="market-panel">
              <div className="market-section-head">
                <div>
                  <span>Nowcast & Event Overlay</span>
                  <h2>단기 보조 신호</h2>
                </div>
              </div>
              <div className="market-scenario-stack">
                {nowcastLeaders.slice(0, 4).map((row, index) => (
                  <ScenarioCard key={`${row.nowcast_code || index}-nowcast`} row={row} compact />
                ))}
              </div>
              <div className="market-bullet-box mt-4">
                {(dashboard.eventOverlay?.reviewBullets?.length ? dashboard.eventOverlay.reviewBullets : ['이벤트 보조신호 요약이 없습니다.'])
                  .slice(0, 5)
                  .map((item) => <p key={item}>{item}</p>)}
              </div>
            </article>
          </section>

          <section className="market-panel mt-6">
            <div className="market-section-head">
              <div>
                <span>All Market Rows</span>
                <h2>국면별 점수 테이블</h2>
              </div>
            </div>
            <div className="market-table-wrap">
              <table className="market-table">
                <thead>
                  <tr>
                    <th>시장국면</th>
                    <th>관점</th>
                    <th>상태</th>
                    <th>점수</th>
                    <th>신뢰도</th>
                    <th>주요 드라이버</th>
                  </tr>
                </thead>
                <tbody>
                  {topRows.slice(0, 12).map((row) => (
                    <tr key={row.scenario_code}>
                      <td>
                        <strong>{scenarioLabel(row)}</strong>
                        <span>{row.scenario_code}</span>
                      </td>
                      <td>{row.lens || '-'}</td>
                      <td><span className={`state-chip ${stateTone(row.final_display_state)}`}>{row.final_display_state || '-'}</span></td>
                      <td>{formatNumber(row.final_score)}</td>
                      <td>{formatNumber(row.final_confidence)}</td>
                      <td>{row.top_positive_drivers || row.market_interpretation_ko || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="market-section-grid lower mt-6">
            <article className="market-panel">
              <div className="market-section-head">
                <div>
                  <span>Validation</span>
                  <h2>과거 검증 요약</h2>
                </div>
              </div>
              <div className="state-chip-row">
                <span className="state-chip positive">OK {formatCount(validationMeta.ok_case_count ?? dashboard.meta?.validationOkCases)}</span>
                <span className="state-chip neutral">TOTAL {formatCount(validationMeta.case_count ?? dashboard.meta?.validationCases)}</span>
              </div>
              <div className="market-bullet-box mt-4">
                {(dashboard.validation?.reviewBullets?.length ? dashboard.validation.reviewBullets : dashboard.summaryBullets || [])
                  .slice(0, 6)
                  .map((item) => <p key={item}>{item}</p>)}
              </div>
            </article>

            <article className="market-panel">
              <div className="market-section-head">
                <div>
                  <span>Artifacts</span>
                  <h2>산출물</h2>
                </div>
              </div>
              <div className="artifact-list">
                {Object.entries(dashboard.artifacts || {}).slice(0, 8).map(([key, value]) => (
                  <div className="artifact-item" key={key}>
                    <FileText size={15} />
                    <div>
                      <strong>{key}</strong>
                      <span>{value || '-'}</span>
                    </div>
                  </div>
                ))}
              </div>
            </article>
          </section>
        </>
      )}
    </div>
  );
};
