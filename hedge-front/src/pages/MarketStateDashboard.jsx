import React, { useEffect, useMemo, useState } from 'react';
import { AlertCircle, Database, ExternalLink, Newspaper, RefreshCw, TrendingDown, TrendingUp } from 'lucide-react';
import { Button } from '../components/Button';
import { getScenarioDashboard, getScenarioRuns, getScenarioSensitivities, pollRunStatus, refreshIntradayNews, refreshMarketData } from '../services/hedgemateApi';
import { buildMarketStateAssetGuide } from '../services/marketStateAssetGuide';
import { ASSET_DATABASE } from '../utils/helpers';
import './MarketStateDashboard.css';

const DAILY_REFRESH_CHECKING_MESSAGE = '정식 일간 시장국면 기준점을 확인하는 중입니다.';
const DAILY_REFRESH_RUNNING_MESSAGE = '최신 일간 데이터로 시장국면을 갱신하는 중입니다.';
const REFRESH_CHECKING_MESSAGE = '\uC7A5\uC911 3\uC2DC\uAC04 nowcast \uAE30\uC900\uC810\uC744 \uD655\uC778\uD558\uB294 \uC911\uC785\uB2C8\uB2E4.';
const REFRESH_RUNNING_MESSAGE = '\uCD5C\uC2E0 \uC7A5\uC911 \uB370\uC774\uD130\uB85C nowcast\uB97C \uAC31\uC2E0\uD558\uB294 \uC911\uC785\uB2C8\uB2E4.';
const NEWS_REFRESH_CHECKING_MESSAGE = '뉴스 오버레이 기준점을 확인하는 중입니다.';
const NEWS_REFRESH_RUNNING_MESSAGE = '시장국면 보조 뉴스 Top5를 갱신하는 중입니다.';
const MARKET_STATE_TABS = [
  { id: 'summary', label: '요약' },
  { id: 'lens', label: '관점별 국면 분류' },
  { id: 'shortTerm', label: '단기 보조 신호' },
];

const isAlreadyCurrentRefresh = (job) => {
  if (!job) return false;
  const reason = String(job.result?.reason || job.reason || '').toLowerCase();
  return job.status === 'skipped_latest'
    || reason.includes('already current')
    || reason.includes('skipped_latest');
};

const toNumber = (value, fallback = null) => {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
};

const formatNumber = (value, digits = 2) => {
  const number = toNumber(value);
  if (number === null) return '-';
  return number.toFixed(digits);
};

const formatPercentLike = (value) => {
  const number = toNumber(value);
  if (number === null) return '-';
  return Math.round(number <= 1 ? number * 100 : number).toString();
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

const formatRunBasisLabel = (runId) => {
  const match = String(runId || '').match(/(20\d{6})/);
  if (!match) return '최신 산출물';
  const raw = match[1];
  return `${raw.slice(0, 4)}.${raw.slice(4, 6)}.${raw.slice(6, 8)}`;
};

const formatDateLabel = (value) => {
  const match = String(value || '').match(/(20\d{2})-?(\d{2})-?(\d{2})/);
  if (!match) return value || '-';
  return `${match[1]}.${match[2]}.${match[3]}`;
};

const marketBasisFromDashboard = (dashboard, selectedRun) => {
  const freshness = dashboard?.marketStateFreshness || {};
  const dailyPrimary = dashboard?.topActiveScenarios?.[0] || {};
  return {
    label: '정식 일간 기준',
    value: formatDateLabel(freshness.dailyFinalDataAsOfDate || dailyPrimary.dataAsOfDate || dashboard?.dataAsOfDate) || formatRunBasisLabel(selectedRun),
    title: selectedRun || 'latest',
  };
};

const stateTone = (state) => {
  const normalized = String(state || '').toUpperCase();
  if (['ACTIVE', 'STRONG', 'RISK_ON', 'PASS', 'OK'].includes(normalized)) return 'positive';
  if (['WATCH', 'STRESS', 'WARN', 'PROVISIONAL'].includes(normalized)) return 'warning';
  if (['OFF', 'NEUTRAL', 'INSUFFICIENT_HISTORY'].includes(normalized)) return 'neutral';
  return 'muted';
};

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
  if (row.nameKo) return cleanText(row.nameKo, '시장국면');
  const nowcastCode = row.nowcast_code || (row.source === 'intraday_nowcast' ? row.code : '');
  const scenarioCode = row.scenario_code || (row.source === 'daily_final' ? row.code : '');
  const fallback = NOWCAST_CODE_LABELS[nowcastCode] || DAILY_SCENARIO_CODE_LABELS[scenarioCode] || nowcastCode || scenarioCode || '시장국면';
  return cleanText(row.nowcast_name_ko || row.scenario_name_ko || row.scenario_name, fallback);
};

const progressStyle = (score) => ({
  width: `${Math.max(0, Math.min(100, toNumber(score, 0)))}%`,
});

const SCENARIO_CODE_LABELS = {
  soft_landing_goldilocks: '골디락스/연착륙',
  slowdown_recession_deflation_risk: '경기둔화/침체',
  higher_for_longer_long_rate_shock: '장기금리 부담',
  stagflation_reinflation_energy_shock: '재인플레/에너지',
  usd_strength_krw_weakness: '달러강세/원화약세',
  acute_global_stress_liquidity_crunch: '글로벌 스트레스',
  china_trade_fragmentation_shock: '중국/무역 분절',
  semiconductor_ai_cycle_shock: '반도체/AI 사이클',
  korea_domestic_financial_stress: '한국 금융 스트레스',
  geopolitical_escalation_supply_shock: '지정학/공급충격',
};

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
  kr_defensive_rotation_intraday: '한국장 방어주 상대 강세',
};

const scenarioCodeLabel = (code) => DAILY_SCENARIO_CODE_LABELS[code] || SCENARIO_CODE_LABELS[code] || NOWCAST_CODE_LABELS[code] || code;

const severityTone = (value) => {
  const number = toNumber(value, 0);
  if (number >= 72) return 'warning';
  if (number >= 55) return 'neutral';
  return 'muted';
};

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

const nowcastStatus = (row) => row?.status || row?.raw_state || row?.display_state || row?.structured_display_state || '';

const isDisplayableNowcast = (row) => {
  const status = String(nowcastStatus(row)).toUpperCase();
  return Boolean(status) && !['OFF', 'NEUTRAL', 'OK', 'PASS', 'INSUFFICIENT_HISTORY'].includes(status);
};

const MarketSummaryCard = ({ dashboard, activeScenarios, stateCounts, nowcastLeaders }) => {
  const dailyPrimary = activeScenarios[0] || {};
  const hasDailyPrimary = Boolean(dailyPrimary.scenario_code || dailyPrimary.scenario_name_ko || dailyPrimary.scenario_name);
  const primary = {
    source: 'daily_final',
    code: dailyPrimary.scenario_code,
    nameKo: scenarioLabel(dailyPrimary),
    score: dailyPrimary.final_score ?? dailyPrimary.score ?? dailyPrimary.activation_weight,
    confidence: dailyPrimary.final_confidence ?? dailyPrimary.confidence,
    state: dailyPrimary.final_display_state || dailyPrimary.display_state || dailyPrimary.status || (hasDailyPrimary ? 'ACTIVE' : '-'),
    dataAsOfDate: dashboard.dataAsOfDate,
    interpretationKo: dailyPrimary.market_interpretation_ko,
  };
  const intradayReferenceSignal = (nowcastLeaders || []).find(isDisplayableNowcast);
  const primaryState = primary.state || 'ACTIVE';
  const primaryScore = primary.score;
  const primaryConfidence = primary.confidence;
  const activeCount = stateCounts.find((item) => String(item.state).toUpperCase() === 'ACTIVE')?.count ?? activeScenarios.length;
  const watchCount = stateCounts.find((item) => String(item.state).toUpperCase() === 'WATCH')?.count ?? 0;
  const offCount = stateCounts.find((item) => String(item.state).toUpperCase() === 'OFF')?.count ?? 0;
  const intradayStatus = dashboard.intradayNowcastStatus || {};
  const freshness = dashboard.marketStateFreshness || {};
  const newsAdjustment = dashboard.intradayNewsScoreAdjustment || {};
  const intradayReferenceSource = freshness.intradayNowcastAsOfKst
    || intradayReferenceSignal?.asOfKst
    || intradayReferenceSignal?.latestTimestampKst
    || intradayStatus.latestTimestampKst;
  const intradayReferenceText = formatKstDateTime(intradayReferenceSource);
  const intradayShortReferenceText = formatKstDateTimeShort(intradayReferenceSource);
  const currentDataReferenceText = formatDateLabel(freshness.dailyFinalDataAsOfDate || primary.dataAsOfDate || dashboard.dataAsOfDate || dashboard.asOfDate);
  const dailyReferenceText = formatDateLabel(freshness.dailyFinalDataAsOfDate || primary.dataAsOfDate || dashboard.dataAsOfDate);
  const newsReferenceText = Array.isArray(newsAdjustment.newsDates) && newsAdjustment.newsDates.length
    ? newsAdjustment.newsDates.join(', ')
    : '뉴스 기준일 없음';
  const referenceText = `정식 일간 기준 ${dailyReferenceText}`;
  const summaryCopy = cleanText(primary.interpretationKo || primary.market_interpretation_ko)
    || '현재 정식 일간 시장국면과 자산 민감도 데이터를 기준으로 시장 상태를 요약합니다.';
  const fallbackNote = intradayStatus && intradayStatus.fresh === false
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
          <span className={`state-chip ${stateTone(primaryState)}`}>{primaryState}</span>
          <span className="state-chip neutral">정식 일간</span>
        </div>
        <p>{summaryCopy}</p>
        {fallbackNote && <p className="summary-basis-note warning">{fallbackNote}</p>}
        <div className="summary-basis-row">
          <span>장중 nowcast: {intradayReferenceText || '최신 신호 없음'}</span>
          <span>현재 데이터 기준: {currentDataReferenceText}</span>
          <span>뉴스 기준: {newsReferenceText}</span>
        </div>
        {newsAdjustment.skipReason === 'news_date_mismatch' && (
          <p className="summary-basis-note warning">뉴스 날짜가 현재 표시 기준과 달라 점수에는 반영하지 않았습니다.</p>
        )}
        <div className="summary-chip-row">
          <strong>정식 일간 국면 TOP 3{dailyReferenceText ? ` · 일간 데이터 ${dailyReferenceText}` : ''}:</strong>
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
        {intradayReferenceSignal && (
          <div className="summary-nowcast-reference" aria-label="장중 참고 신호">
            <div>
              <span>장중 참고 신호</span>
              <strong>
                {scenarioLabel(intradayReferenceSignal)}
                {' · '}
                {intradaySignalStatus || '-'}
                {' · '}
                {formatNumber(intradaySignalScore, 1)}
              </strong>
            </div>
            <p>단기 보조 신호이며 정식 시장국면은 아닙니다.</p>
            <small>기준: {intradayShortReferenceText || intradayReferenceText || '-'}</small>
          </div>
        )}
      </div>
      <div className="market-simple-score">
        <strong>{formatNumber(primaryScore, 1)}</strong>
        <span>DAILY FINAL SCORE</span>
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
const NewsRiskOverlaySection = ({ items, status, isRefreshing, refreshStatus }) => {
  const rows = Array.isArray(items) ? items.slice(0, 5) : [];
  const fallbackText = status?.fallbackUsed
    ? 'Gemini key 또는 외부 응답이 없어 검증된 fallback 근거를 표시 중입니다.'
    : 'Gemini Flash-Lite 구조화 결과를 JSON schema 검증 후 표시합니다.';
  const referenceText = status?.refreshWindowKst
    ? `기준 창 ${formatKstDateTime(status.refreshWindowKst)}`
    : '09:00 / 15:00 / 21:00 KST 창 기준';

  return (
    <section className="market-panel news-overlay-panel mt-6">
      <div className="market-section-head">
        <div>
          <span>시장국면 판단 보조 근거</span>
          <h2>Top5 뉴스 리스크 오버레이</h2>
        </div>
        <span className={`section-chip ${isRefreshing ? 'refreshing' : ''}`}>
          {isRefreshing ? '갱신 중' : `${rows.length}/5`}
        </span>
      </div>

      <div className="news-overlay-note">
        <Newspaper size={16} />
        <span>{refreshStatus || fallbackText} · {referenceText}</span>
      </div>

      {rows.length ? (
        <div className="news-overlay-list">
          {rows.map((item, index) => {
            const scenarioLinks = Array.isArray(item.scenarioLinks) ? item.scenarioLinks : [];
            const url = String(item.url || '');
            const title = item.displayTitleKo || item.title || '제목 없음';
            const summary = item.displaySummaryKo || item.evidenceSpan || '근거 문장이 없습니다.';
            const source = item.sourceKo || item.source || '-';
            const riskLabel = item.riskLabelKo || item.eventType || '시장 리스크';
            const hasSourceLink = Boolean(url && !url.startsWith('fallback://'));
            return (
              <article className="news-overlay-item" key={`${title || 'news'}-${index}`}>
                <div className="news-overlay-rank">{index + 1}</div>
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
                    <span>{riskLabel}</span>
                    <span>{formatKstDateTime(item.date) || item.timeHorizon || '-'}</span>
                    <span className={`state-chip ${severityTone(item.severity)}`}>위험도 {formatNumber(item.severity, 0)}</span>
                    <span>신뢰도 {formatPercentLike(item.confidence)}</span>
                  </div>
                  <p>{summary}</p>
                  <div className="news-scenario-links" aria-label="연결된 시장국면">
                    {scenarioLinks.length
                      ? scenarioLinks.slice(0, 3).map((code) => <span key={code}>{scenarioCodeLabel(code)}</span>)
                      : <span>시장국면 미분류</span>}
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      ) : (
        <div className="market-empty compact">
          Top5 뉴스 오버레이가 아직 없습니다. 시장국면 본문은 기존 daily/nowcast 레이어로 계속 표시됩니다.
        </div>
      )}
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
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [refreshStatus, setRefreshStatus] = useState('');
  const [error, setError] = useState('');
  const [scenarioSensitivityPayload, setScenarioSensitivityPayload] = useState(null);
  const [assetGuideError, setAssetGuideError] = useState('');
  const [activeTab, setActiveTab] = useState('summary');
  const [isNewsRefreshing, setIsNewsRefreshing] = useState(false);
  const [newsRefreshStatus, setNewsRefreshStatus] = useState('');

  const loadDashboard = async (runId = '', options = {}) => {
    const { showLoading = true, ...requestOptions } = options;
    if (showLoading) setIsLoading(true);
    setError('');
    setAssetGuideError('');
    try {
      const data = await getScenarioDashboard(runId, requestOptions);
      setDashboard(data);
      setSelectedRun(data.runId || runId || '');
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
    } catch (err) {
      if (err.name === 'AbortError') return;
      setError(err.message || '시장국면 진단 결과를 불러오지 못했습니다.');
    } finally {
      if (showLoading) setIsLoading(false);
    }
  };

  const refreshNewsOverlay = async (runId = '', options = {}) => {
    setIsNewsRefreshing(true);
    setNewsRefreshStatus(NEWS_REFRESH_CHECKING_MESSAGE);
    try {
      const newsJob = await refreshIntradayNews({
        triggerReason: 'market_state_view',
        autoRefresh: true,
      }, { signal: options.signal, timeoutMs: 30 * 1000 });
      if (options.signal?.aborted) return;
      if (isAlreadyCurrentRefresh(newsJob)) {
        setNewsRefreshStatus('');
      } else if (newsJob.status === 'completed') {
        setNewsRefreshStatus('');
      } else if (newsJob.jobId) {
        setNewsRefreshStatus(NEWS_REFRESH_RUNNING_MESSAGE);
        const finalStatus = await pollRunStatus(newsJob.jobId, (status) => {
          if (!options.signal?.aborted) {
            setNewsRefreshStatus(status.currentStep || status.stage || NEWS_REFRESH_RUNNING_MESSAGE);
          }
        }, { signal: options.signal, intervalMs: 3000, timeoutMs: 8 * 60 * 1000 });
        if (finalStatus.status !== 'completed') {
          throw new Error(finalStatus.error || '뉴스 오버레이 갱신이 완료되지 않았습니다.');
        }
        setNewsRefreshStatus('');
      }
      if (!options.signal?.aborted) {
        await loadDashboard(runId || selectedRun, { signal: options.signal, showLoading: false });
      }
    } catch (err) {
      if (err.name !== 'AbortError' && !options.signal?.aborted) {
        setNewsRefreshStatus(`뉴스 오버레이는 기존 또는 fallback 상태로 표시됩니다. ${err.message || ''}`.trim());
      }
    } finally {
      if (!options.signal?.aborted) setIsNewsRefreshing(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();
    const bootstrap = async () => {
      setIsLoading(true);
      setIsRefreshing(true);
      setRefreshStatus(DAILY_REFRESH_CHECKING_MESSAGE);
      setError('');
      try {
        const dailyRefreshJob = await refreshMarketData({
          mode: 'market_data_only',
          useLivePrices: true,
          autoRefresh: true,
        }, { signal: controller.signal, timeoutMs: 30 * 1000 });
        if (cancelled) return;
        if (isAlreadyCurrentRefresh(dailyRefreshJob)) {
          setRefreshStatus('');
        } else if (dailyRefreshJob.status === 'completed') {
          setRefreshStatus('');
        } else if (dailyRefreshJob.jobId) {
          setRefreshStatus(DAILY_REFRESH_RUNNING_MESSAGE);
          const finalDailyStatus = await pollRunStatus(dailyRefreshJob.jobId, (status) => {
            if (!cancelled) {
              setRefreshStatus(status.currentStep || status.stage || DAILY_REFRESH_RUNNING_MESSAGE);
            }
          }, { signal: controller.signal, intervalMs: 3000, timeoutMs: 15 * 60 * 1000 });
          if (finalDailyStatus.status !== 'completed' && finalDailyStatus.status !== 'skipped_latest') {
            throw new Error(finalDailyStatus.error || '일간 시장국면 갱신이 완료되지 않았습니다.');
          }
        }
        setRefreshStatus(REFRESH_CHECKING_MESSAGE);
        const refreshJob = await refreshMarketData({
          mode: 'intraday_nowcast',
          useLivePrices: true,
          autoRefresh: true,
        }, { signal: controller.signal, timeoutMs: 30 * 1000 });
        if (cancelled) return;
        if (isAlreadyCurrentRefresh(refreshJob)) {
          setRefreshStatus('');
        } else if (refreshJob.status === 'completed') {
          setRefreshStatus('');
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
          setRefreshStatus('');
        }
        const runPayload = await getScenarioRuns({ signal: controller.signal });
        if (cancelled) return;
        const latestRun = runPayload.latestRunId || runPayload.runs?.[0] || '';
        await loadDashboard(latestRun, { signal: controller.signal });
        refreshNewsOverlay(latestRun, { signal: controller.signal });
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
  const newsTop5 = dashboard?.intradayNewsTop5 || [];
  const newsStatus = dashboard?.intradayNewsOverlayStatus || {};
  const assetGuide = useMemo(
    () => buildMarketStateAssetGuide(dashboard || {}, scenarioSensitivityPayload || { rows: [] }),
    [dashboard, scenarioSensitivityPayload]
  );
  const marketBasis = marketBasisFromDashboard(dashboard, selectedRun);

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
          <div className="market-basis-chip" title={marketBasis.title}>
            <span>{marketBasis.label}</span>
            <strong>{marketBasis.value}</strong>
          </div>
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

      {newsRefreshStatus && (
        <div className="market-status mt-3">
          <Newspaper size={16} />
          <span>{newsRefreshStatus}</span>
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
                isRefreshing={isNewsRefreshing}
                refreshStatus={newsRefreshStatus}
              />

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
