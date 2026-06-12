import React, { useEffect, useMemo, useState } from 'react';
import { AlertCircle, Database, ExternalLink, Newspaper, RefreshCw, TrendingDown, TrendingUp } from 'lucide-react';
import { Button } from '../components/Button';
import { getScenarioDashboard, getScenarioSensitivities } from '../services/hedgemateApi';
import { buildMarketStateAssetGuide } from '../services/marketStateAssetGuide';
import { ASSET_DATABASE } from '../utils/helpers';
import './MarketStateDashboard.css';

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

const formatKstDateTimeShort = (value) => {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const datePart = date.toLocaleDateString('ko-KR', {
    timeZone: 'Asia/Seoul',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).replace(/\.\s*/g, '.').replace(/\.$/, '');
  const timePart = date.toLocaleTimeString('ko-KR', {
    timeZone: 'Asia/Seoul',
    hour: '2-digit',
    minute: '2-digit',
  });
  return `${datePart} ${timePart}`;
};

const formatKstDateOnly = (value) => {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return formatDateLabel(value);
  return date.toLocaleDateString('ko-KR', {
    timeZone: 'Asia/Seoul',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).replace(/\.\s*/g, '.').replace(/\.$/, '');
};

const formatDateLabel = (value) => {
  const match = String(value || '').match(/(20\d{2})-?(\d{2})-?(\d{2})/);
  if (!match) return value || '-';
  return `${match[1]}.${match[2]}.${match[3]}`;
};

const stateTone = (state) => {
  const normalized = String(state || '').toUpperCase();
  if (['ACTIVE', 'STRONG', 'RISK_ON', 'PASS', 'OK'].includes(normalized)) return 'positive';
  if (['WATCH', 'STRESS', 'WARN', 'PROVISIONAL'].includes(normalized)) return 'warning';
  if (['OFF', 'NEUTRAL', 'INSUFFICIENT_HISTORY'].includes(normalized)) return 'neutral';
  return 'muted';
};

const STATE_LABELS = {
  ACTIVE: '활성',
  WATCH: '관찰',
  STRESS: '스트레스',
  OFF: '비활성',
  NEUTRAL: '중립',
  PROVISIONAL: '임시',
  PRESSURE: '부담',
  FX_PRESSURE: '환율 부담',
  RISK_OFF_SPILLOVER: '위험회피 전이',
  RISK_ON: '위험선호',
  DEFENSIVE_ROTATION: '방어주 상대강세',
  INSUFFICIENT_HISTORY: '자료 부족',
};

const stateLabel = (state) => STATE_LABELS[String(state || '').toUpperCase()] || state || '-';

const looksMojibake = (value) => {
  const text = String(value || '');
  return text.includes('�') || (text.includes('?') && /[가-힣]/.test(text)) || (text.match(/\?/g) || []).length >= 2 || /[媛湲諛愿吏]|쨌|\?쒓|\?μ|\?꾩|\?먰/.test(text);
};

const cleanText = (value, fallback = '') => {
  const text = String(value || '').trim();
  if (text && !looksMojibake(text)) return text;
  return fallback || text;
};

const scenarioLabel = (row) => {
  if (!row) return '시장국면';
  const nowcastCode = row.nowcast_code || (row.source === 'intraday_nowcast' ? row.code : '');
  const scenarioCode = row.scenario_code || (row.source === 'daily_final' ? row.code : '');
  if (NOWCAST_CODE_LABELS[nowcastCode]) return NOWCAST_CODE_LABELS[nowcastCode];
  if (row.nameKo) return cleanText(row.nameKo, '시장국면');
  const fallback = NOWCAST_CODE_LABELS[nowcastCode] || DAILY_SCENARIO_CODE_LABELS[scenarioCode] || nowcastCode || scenarioCode || '시장국면';
  return cleanText(row.nowcast_name_ko || row.scenario_name_ko || row.scenario_name, fallback);
};

const progressStyle = (score) => ({
  width: `${Math.max(0, Math.min(100, toNumber(score, 0)))}%`,
});

const DAILY_SCENARIO_CODE_LABELS = {
  soft_landing_goldilocks: '골디락스/연착륙',
  slowdown_recession_deflation_risk: '경기둔화/침체',
  higher_for_longer_long_rate_shock: '장기금리 부담',
  stagflation_reinflation_energy_shock: '스태그플레이션/에너지',
  usd_strength_krw_weakness: '달러강세/원화약세',
  acute_global_stress_liquidity_crunch: '글로벌 스트레스',
  china_trade_fragmentation_shock: '중국/무역 분절',
  semiconductor_ai_cycle_shock: '반도체 AI 사이클',
  korea_domestic_financial_stress: '한국 금융 스트레스',
  geopolitical_escalation_supply_shock: '지정학/공급충격',
};

const NOWCAST_CODE_LABELS = {
  kr_risk_on_intraday: '한국장 장중 위험선호',
  global_risk_spillover_intraday: '글로벌 위험회피 한국 전이',
  krw_weakness_intraday: '원화약세 장중 압력',
  kr_semiconductor_pressure_intraday: '한국 반도체 장중 부담',
  kr_defensive_rotation_intraday: '한국장 방어주 상대강세',
};

const ScenarioCard = ({ row, compact = false }) => {
  const state = row.final_display_state || row.display_state || row.structured_display_state || row.status || row.raw_state;
  const score = row.final_score ?? row.score ?? row.structured_score;
  const interpretation = row.market_interpretation_ko || row.interpretation_ko;
  const driverText = row.top_positive_drivers || row.topPositiveDrivers || '';
  const drivers = String(driverText || '')
    .split('|')
    .map((item) => cleanText(item).trim())
    .filter(Boolean)
    .slice(0, 3);
  return (
    <article className={`market-scenario-card ${compact ? 'compact' : ''}`}>
      <div className="market-card-head">
        <div>
          <h3>{scenarioLabel(row)}</h3>
          <p>{row.scenario_name || row.scenario_code || row.lens || row.nowcast_code || '-'}</p>
        </div>
        <span className={`state-chip ${stateTone(state)}`}>{stateLabel(state)}</span>
      </div>
      <div className="score-line">
        <span>점수</span>
        <strong>{formatNumber(score)}</strong>
      </div>
      <div className="score-meter">
        <div className="score-meter-fill" style={progressStyle(score)} />
      </div>
      {interpretation && <p className="market-interpretation">{cleanText(interpretation)}</p>}
      {drivers.length > 0 && (
        <div className="nowcast-driver-list" aria-label="단기 신호 근거">
          {drivers.map((driver) => <span key={driver}>{driver}</span>)}
        </div>
      )}
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

const nowcastStatus = (row) => row?.status || row?.raw_state || row?.display_state || row?.structured_display_state || '';

const isDisplayableNowcast = (row) => {
  const status = String(nowcastStatus(row)).toUpperCase();
  return Boolean(status) && !['OFF', 'NEUTRAL', 'OK', 'PASS', 'INSUFFICIENT_HISTORY'].includes(status);
};

const MarketSummaryCard = ({ dashboard, activeScenarios, stateCounts, nowcastLeaders }) => {
  const dailyPrimary = activeScenarios[0] || {};
  const hasDailyPrimary = Boolean(dailyPrimary.scenario_code || dailyPrimary.scenario_name_ko || dailyPrimary.scenario_name);
  const backendPrimary = dashboard.primaryMarketState || {};
  const primary = hasDailyPrimary ? {
    source: 'daily_final',
    code: dailyPrimary.scenario_code,
    nameKo: scenarioLabel(dailyPrimary),
    score: dailyPrimary.final_score ?? dailyPrimary.score ?? dailyPrimary.activation_weight,
    confidence: dailyPrimary.final_confidence ?? dailyPrimary.confidence,
    state: dailyPrimary.final_display_state || dailyPrimary.display_state || dailyPrimary.status || (hasDailyPrimary ? 'ACTIVE' : '-'),
    dataAsOfDate: dashboard.dataAsOfDate,
    officialDailyDataAsOfDate: dashboard.dataAsOfDate,
    interpretationKo: dailyPrimary.market_interpretation_ko,
  } : {
    source: backendPrimary.source || 'daily_final',
    code: backendPrimary.code,
    nameKo: backendPrimary.nameKo,
    score: backendPrimary.score,
    confidence: backendPrimary.confidence,
    state: backendPrimary.state || '-',
    asOfKst: backendPrimary.asOfKst,
    dataAsOfDate: backendPrimary.dataAsOfDate || dashboard.dataAsOfDate,
    officialDailyDataAsOfDate: backendPrimary.officialDailyDataAsOfDate,
    interpretationKo: backendPrimary.interpretationKo,
  };
  const intradayReferenceSignal = (nowcastLeaders || []).find(isDisplayableNowcast);
  const primaryState = primary.state || 'ACTIVE';
  const primaryScore = primary.score;
  const activeCount = stateCounts.find((item) => String(item.state).toUpperCase() === 'ACTIVE')?.count ?? activeScenarios.length;
  const watchCount = stateCounts.find((item) => String(item.state).toUpperCase() === 'WATCH')?.count ?? 0;
  const offCount = stateCounts.find((item) => String(item.state).toUpperCase() === 'OFF')?.count ?? 0;
  const intradayStatus = dashboard.intradayNowcastStatus || {};
  const freshness = dashboard.marketStateFreshness || {};
  const newsAdjustment = dashboard.intradayNewsScoreAdjustment || {};
  const intradayIsPrimary = primary.source === 'intraday_nowcast' && primary.asOfKst;
  const intradayReferenceSource = primary.asOfKst
    || freshness.intradayNowcastAsOfKst
    || intradayReferenceSignal?.asOfKst
    || intradayReferenceSignal?.latestTimestampKst
    || intradayStatus.latestTimestampKst;
  const intradayReferenceText = formatKstDateTime(intradayReferenceSource);
  const intradayShortReferenceText = formatKstDateTimeShort(intradayReferenceSource);
  const primaryReferenceText = freshness.displayDate
    ? formatDateLabel(freshness.displayDate)
    : (intradayShortReferenceText || formatDateLabel(primary.dataAsOfDate || dashboard.asOfDate));
  const referenceText = intradayReferenceText
    ? `최신 장중 기준 ${intradayShortReferenceText || intradayReferenceText}`
    : `최신 기준 ${primaryReferenceText}`;
  const summaryCopy = cleanText(primary.interpretationKo || primary.market_interpretation_ko)
    || '현재 시장국면과 자산 민감도 데이터를 기준으로 시장 상태를 요약합니다.';
  const fallbackNote = !intradayIsPrimary && intradayStatus && intradayStatus.fresh === false
    ? '장중 nowcast가 최신 기준이 아니어서 정식 일간 국면을 표시합니다.'
    : '';
  const intradaySignalStatus = nowcastStatus(intradayReferenceSignal);
  const intradaySignalScore = intradayReferenceSignal?.score ?? intradayReferenceSignal?.final_score ?? intradayReferenceSignal?.structured_score;

  return (
    <section className="market-simple-summary mt-6">
      <div className="market-simple-copy">
        <span className="summary-kicker">현재 시장국면 진단 · {referenceText}</span>
        <div className="summary-title-row">
          <h2>{scenarioLabel(primary)}</h2>
          <span className={`state-chip ${stateTone(primaryState)}`}>{stateLabel(primaryState)}</span>
          <span className="state-chip neutral">시장국면</span>
        </div>
        <p>{summaryCopy}</p>
        {fallbackNote && <p className="summary-basis-note warning">{fallbackNote}</p>}
        <div className="summary-basis-row">
          <span>현재 기준: {intradayReferenceText || primaryReferenceText}</span>
          {intradayReferenceSignal && <span>장중 참고: {scenarioLabel(intradayReferenceSignal)}</span>}
        </div>
        {newsAdjustment.skipReason === 'news_date_mismatch' && (
          <p className="summary-basis-note warning">뉴스 날짜가 현재 표시 기준과 달라 점수에는 반영하지 않았습니다.</p>
        )}
        <div className="summary-chip-row">
          <strong>시장국면 TOP 3:</strong>
          {activeScenarios.slice(0, 3).map((row) => (
            <span className={`summary-scenario-chip ${stateTone(row.final_display_state || row.display_state)}`} key={row.scenario_code}>
              <span>{scenarioLabel(row)}</span>
              <small>
                {stateLabel(row.final_display_state || row.display_state || 'ACTIVE')}
                {' · 점수 '}
                {formatNumber(row.final_score ?? row.score ?? row.activation_weight, 1)}
              </small>
            </span>
          ))}
        </div>
        {intradayReferenceSignal && (
          <div className="summary-nowcast-reference" aria-label="장중 참고 신호">
            <div>
              <span>장중 참고 신호</span>
              <strong>
                {scenarioLabel(intradayReferenceSignal)}
                {' · '}
                {stateLabel(intradaySignalStatus)}
                {' · '}
                {formatNumber(intradaySignalScore, 1)}
              </strong>
            </div>
            <p>정식 시장국면을 대체하지 않는 장중 참고 신호입니다.</p>
            <small>기준: {intradayShortReferenceText || intradayReferenceText || '-'}</small>
          </div>
        )}
      </div>
      <div className="market-simple-score">
        <strong>{formatNumber(primaryScore, 1)}</strong>
        <span>MARKET STATE SCORE</span>
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
const NewsRiskOverlaySection = ({ items, status, isRefreshing, refreshStatus }) => {
  const rows = Array.isArray(items) ? items.slice(0, 5) : [];
  if (!rows.length) return null;
  const statusText = '뉴스 참고 자료';
  const referenceText = status?.refreshWindowKst
    ? `기준일 ${formatKstDateOnly(status.refreshWindowKst)}`
    : '제목 · 날짜 · 출처 링크';

  return (
    <section className="market-panel news-overlay-panel mt-6">
      <div className="market-section-head">
        <div>
          <span>시장국면 판단 보조 근거</span>
          <h2>시장 뉴스 참고자료</h2>
        </div>
        <span className={`section-chip ${isRefreshing ? 'refreshing' : ''}`}>
          {isRefreshing ? '갱신 중' : `${rows.length}건`}
        </span>
      </div>

      <div className="news-overlay-note">
        <Newspaper size={16} />
        <span>{refreshStatus || statusText} · {referenceText}</span>
      </div>

      <div className="news-overlay-list">
        {rows.map((item, index) => {
          const url = String(item.url || '');
          const title = item.displayTitleKo || item.title || '제목 없음';
          const source = item.sourceKo || item.source || '-';
          const publishedDate = formatKstDateOnly(item.date || item.publishedAt || item.timestamp || item.timeHorizon);
          const hasSourceLink = /^https?:\/\//i.test(url);
          return (
            <article className="news-overlay-item" key={`${title || 'news'}-${index}`}>
              <div className="news-overlay-rank" aria-hidden="true">•</div>
              <div className="news-overlay-body">
                <div className="news-overlay-title-row">
                  <h3>{title}</h3>
                </div>
                <div className="news-overlay-meta">
                  {hasSourceLink ? (
                    <a className="news-source-chip" href={url} target="_blank" rel="noreferrer" aria-label={`${source} 뉴스 원문 열기`}>
                      <span>출처: {source}</span>
                      <ExternalLink size={12} />
                    </a>
                  ) : (
                    <span className="news-source-chip muted">출처: {source}</span>
                  )}
                  <span>{publishedDate || '-'}</span>
                </div>
              </div>
            </article>
          );
        })}
      </div>
      <p className="asset-guide-footnote">* 이 섹션은 /market-state 설명용 intraday 레이어입니다. 개선 리포트의 정식 판단, backtest gate, product bundle 근거로 사용하지 않습니다.</p>
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
            ? nowcastLeaders.slice(0, 5).map((row, index) => (
              <ScenarioCard key={`${row.nowcast_code || index}-nowcast`} row={row} compact />
            ))
            : <div className="market-empty">단기 nowcast 신호가 없습니다.</div>}
        </div>
      </article>
    </section>
  );
};

export const MarketStateDashboard = () => {
  const [selectedRun, setSelectedRun] = useState('');
  const [dashboard, setDashboard] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [refreshStatus, setRefreshStatus] = useState('');
  const [error, setError] = useState('');
  const [scenarioSensitivityPayload, setScenarioSensitivityPayload] = useState(null);
  const [assetGuideError, setAssetGuideError] = useState('');
  const [activeTab, setActiveTab] = useState('summary');

  const loadDashboard = async (runId = '', options = {}) => {
    const { showLoading = true, ...requestOptions } = options;
    if (showLoading) setIsLoading(true);
    setError('');
    setAssetGuideError('');
    try {
      const data = await getScenarioDashboard(runId, requestOptions);
      setDashboard(data);
      setSelectedRun(data.runId || runId || '');
      if (data?.snapshotUnavailable || String(data?.status || '').toUpperCase() === 'REFRESHING') {
        setRefreshStatus('시장국면 snapshot을 준비 중입니다. 사용 가능한 최신 시장국면 데이터를 먼저 표시합니다.');
      } else {
        setRefreshStatus('');
      }
      try {
        const sensitivities = await getScenarioSensitivities({
          signal: requestOptions.signal,
          timeoutMs: requestOptions.timeoutMs,
        });
        setScenarioSensitivityPayload(sensitivities);
      } catch (sensitivityError) {
        if (sensitivityError.name === 'AbortError') return;
        setScenarioSensitivityPayload({ rows: [] });
        setAssetGuideError(sensitivityError.message || '자산 민감도 데이터를 불러오지 못했습니다.');
      }
      return data;
    } catch (err) {
      if (err.name === 'AbortError') return;
      setError(err.message || '시장국면 진단 결과를 불러오지 못했습니다.');
      return null;
    } finally {
      if (showLoading) setIsLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();
    const bootstrap = async () => {
      setIsLoading(true);
      setError('');
      try {
        await loadDashboard('', { signal: controller.signal });
      } catch (err) {
        if (!cancelled) {
          setError(err.message || '시장국면 실행 목록을 불러오지 못했습니다.');
          setIsLoading(false);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
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
  const newsTop5 = dashboard?.intradayNewsTop5 || [];
  const newsStatus = dashboard?.intradayNewsOverlayStatus || {};
  const assetGuide = useMemo(
    () => buildMarketStateAssetGuide(dashboard || {}, scenarioSensitivityPayload || { rows: [] }),
    [dashboard, scenarioSensitivityPayload]
  );
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
          <Button variant="secondary" onClick={() => loadDashboard(selectedRun)} disabled={isLoading}>
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
              <MarketSummaryCard dashboard={dashboard} activeScenarios={activeScenarios} stateCounts={stateCounts} nowcastLeaders={nowcastLeaders} />

              <NewsRiskOverlaySection
                items={newsTop5}
                status={newsStatus}
                isRefreshing={false}
                refreshStatus=""
              />

              <section className="market-panel asset-guide-panel mt-6">
                <div className="market-section-head">
                  <div>
                    <span>이 장세의 추천 자산</span>
                    <h2>현재 시장국면 기반 자산 배분 가이드</h2>
                  </div>
                  <span className="section-chip">
                    {assetGuide.totalAssetCount || 0}개 자산 · {assetGuide.activeScenarios.length}개 국면 매칭 · {assetGuide.matchedRowCount}개 행
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
