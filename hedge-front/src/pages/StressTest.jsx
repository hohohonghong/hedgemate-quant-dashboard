import React, { useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  ArrowRight,
  Briefcase,
  CheckCircle2,
  Loader2,
  Shield,
  TrendingDown,
  TrendingUp,
} from 'lucide-react';
import { Button } from '../components/Button';
import { useNavigate } from 'react-router-dom';
import { usePortfolios } from '../context/PortfolioContext';
import { getScenarioDashboard, getScenarioSensitivities } from '../services/hedgemateApi';
import { isKoreanTicker, normalizeTickerSymbol } from '../utils/helpers';
import './StressTest.css';

const IMPACT_CAP_PCT = 35;
const STRESS_HORIZON_TRADING_DAYS = 5;
const STRESS_HORIZON_LABEL = `${STRESS_HORIZON_TRADING_DAYS}거래일`;
const IMPACT_SCALE = 8;
const SENSITIVITY_SCORE_SCALE = 100;

const clamp = (value, min, max) => {
  const number = Number(value);
  if (!Number.isFinite(number)) return min;
  return Math.min(max, Math.max(min, number));
};

const toNumber = (value, fallback = 0) => {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
};

const formatPct = (value, digits = 2) => {
  const number = toNumber(value);
  return `${number > 0 ? '+' : ''}${number.toFixed(digits)}%`;
};

const formatKrw = (value) => {
  const number = Math.round(Math.abs(toNumber(value)));
  return `${value < 0 ? '-' : ''}₩${number.toLocaleString()}`;
};

const scenarioScore = (row = {}) => toNumber(
  row.final_score ?? row.score ?? row.structured_score ?? row.scenario_score,
);

const scenarioConfidence = (row = {}) => toNumber(
  row.final_confidence ?? row.confidence ?? row.structured_confidence ?? row.finalConfidence,
);

const normalizeScenario = (row = {}, source = '') => {
  const code = String(row.scenario_code || row.scenarioCode || '').trim();
  if (!code) return null;
  return {
    code,
    name: row.scenario_name_ko || row.scenarioNameKo || row.scenario_name || row.scenarioName || code,
    englishName: row.scenario_name || row.scenarioName || '',
    lens: row.lens || row.related_lenses || '-',
    score: scenarioScore(row),
    confidence: scenarioConfidence(row),
    state: row.final_display_state || row.structured_display_state || row.display_state || row.final_state || '-',
    interpretation: row.market_interpretation_ko || row.notes || '',
    source,
  };
};

const collectScenarios = (dashboard) => {
  const candidates = [
    ...(dashboard?.topActiveScenarios || []).map((row) => [row, 'topActiveScenarios']),
    ...(dashboard?.topMarketRows || []).map((row) => [row, 'topMarketRows']),
    ...(dashboard?.scenarioVectorLeaders || []).map((row) => [row, 'scenarioVectorLeaders']),
  ];
  const byCode = new Map();

  candidates.forEach(([row, source]) => {
    const scenario = normalizeScenario(row, source);
    if (!scenario) return;
    const existing = byCode.get(scenario.code);
    if (!existing || scenario.score > existing.score) {
      byCode.set(scenario.code, scenario);
    }
  });

  return [...byCode.values()].sort((a, b) => b.score - a.score);
};

const sensitivityKey = (scenarioCode, ticker) => `${scenarioCode}::${normalizeTickerSymbol(ticker)}`;

const buildSensitivityMap = (rows = []) => {
  const map = new Map();
  rows.forEach((row) => {
    const scenarioCode = String(row.scenario_code || '').trim();
    const ticker = normalizeTickerSymbol(row.ticker || row.asset_ticker || row.asset || '');
    const beta = Number(row.scenario_beta);
    if (!scenarioCode || !ticker || !Number.isFinite(beta)) return;

    const key = sensitivityKey(scenarioCode, ticker);
    const existing = map.get(key);
    if (!existing || toNumber(row.confidence) > toNumber(existing.confidence)) {
      map.set(key, { ...row, ticker, scenario_beta: beta });
    }
  });
  return map;
};

const assetExplicitAmountKrw = (asset) => {
  const explicit = toNumber(asset.amountKrw ?? asset.marketValueKrw ?? asset.valueKrw, NaN);
  return Number.isFinite(explicit) && explicit > 0 ? explicit : null;
};

const assetCostValueKrw = (asset, usdKrwRate) => {
  const qty = toNumber(asset.qty ?? asset.quantity, 0);
  const cost = toNumber(asset.cost ?? asset.price ?? asset.unitPrice, 0);
  if (!qty || !cost) return null;
  const isUsd = asset.currency === 'USD' || (!asset.currency && !isKoreanTicker(asset.ticker));
  return qty * cost * (isUsd ? usdKrwRate : 1);
};

const portfolioAssetsWithWeights = (portfolio, usdKrwRate) => {
  const totalValue = toNumber(portfolio?.totalValue ?? portfolio?.totalValueKrw, 0);
  const prepared = (portfolio?.assets || [])
    .map((asset) => {
      const ticker = normalizeTickerSymbol(asset.ticker || asset.symbol || asset.name);
      const explicitValue = assetExplicitAmountKrw(asset);
      const costValue = assetCostValueKrw(asset, usdKrwRate);
      const weightPct = toNumber(asset.weightPct ?? asset.weight, NaN);
      const derivedValue = totalValue > 0 && Number.isFinite(weightPct) && weightPct > 0
        ? (totalValue * weightPct) / 100
        : null;
      const valueKrw = explicitValue ?? costValue ?? derivedValue ?? 0;
      return {
        ticker,
        name: asset.name || ticker,
        valueKrw,
        storedWeightPct: Number.isFinite(weightPct) ? weightPct : null,
      };
    })
    .filter((asset) => asset.ticker);

  const valueSum = prepared.reduce((sum, asset) => sum + asset.valueKrw, 0);
  const weightSum = prepared.reduce((sum, asset) => sum + (asset.storedWeightPct || 0), 0);

  return prepared
    .map((asset) => {
      const weightPct = valueSum > 0
        ? (asset.valueKrw / valueSum) * 100
        : weightSum > 0 && asset.storedWeightPct !== null
          ? (asset.storedWeightPct / weightSum) * 100
          : 0;
      return {
        ...asset,
        weightPct,
        weight: weightPct / 100,
      };
    })
    .filter((asset) => asset.weight > 0);
};

const isFavorableScenario = (scenarioCode = '') => {
  const lower = scenarioCode.toLowerCase();
  return lower.includes('soft_landing') || lower.includes('goldilocks');
};

const calculateScenarioResult = (scenario, assets, sensitivityMap, totalValue) => {
  if (!scenario) return null;
  const favorable = isFavorableScenario(scenario.code);
  const intensity = clamp(scenario.score / 100, 0, 1);

  const rows = assets.map((asset) => {
    const sensitivity = sensitivityMap.get(sensitivityKey(scenario.code, asset.ticker));
    if (!sensitivity) {
      return { ...asset, matched: false };
    }
    const beta = toNumber(sensitivity.scenario_beta);
    const confidence = toNumber(sensitivity.confidence, scenario.confidence || 50);
    const confidenceWeight = clamp(confidence / 100, 0.25, 1);
    const rawImpact = (favorable ? beta : -beta) * intensity * confidenceWeight * IMPACT_SCALE;
    const assetImpactPct = clamp(rawImpact, -IMPACT_CAP_PCT, IMPACT_CAP_PCT);
    const assetSensitivityScore = clamp(Math.abs(beta) * intensity * confidenceWeight * SENSITIVITY_SCORE_SCALE, 0, 100);
    return {
      ...asset,
      matched: true,
      scenarioBeta: beta,
      assetImpactPct,
      assetImpactAmount: totalValue * asset.weight * assetImpactPct / 100,
      assetSensitivityScore,
      confidence,
      sourceQuality: sensitivity.source_quality || '-',
      sensitivityLevel: sensitivity.sensitivity_level || '-',
      recommendedRole: sensitivity.recommended_role || '-',
      notes: sensitivity.notes || '',
    };
  });

  const matchedRows = rows.filter((row) => row.matched);
  const matchedWeight = matchedRows.reduce((sum, row) => sum + row.weight, 0);
  const portfolioImpactPct = matchedRows.reduce((sum, row) => sum + row.weight * row.assetImpactPct, 0);
  const portfolioImpactAmount = totalValue * portfolioImpactPct / 100;
  const portfolioSensitivityScore = clamp(
    matchedRows.reduce((sum, row) => sum + row.weight * row.assetSensitivityScore, 0),
    0,
    100,
  );
  const weightedConfidence = matchedWeight > 0
    ? matchedRows.reduce((sum, row) => sum + row.confidence * row.weight, 0) / matchedWeight
    : 0;

  const vulnerableAssets = matchedRows
    .filter((row) => row.assetImpactPct < 0)
    .sort((a, b) => a.assetImpactPct - b.assetImpactPct)
    .slice(0, 5);
  const defensiveAssets = matchedRows
    .filter((row) => row.assetImpactPct > 0)
    .sort((a, b) => b.assetImpactPct - a.assetImpactPct)
    .slice(0, 5);

  return {
    scenario,
    favorable,
    intensity,
    rows,
    matchedRows,
    vulnerableAssets,
    defensiveAssets,
    coveragePct: assets.length > 0 ? (matchedRows.length / assets.length) * 100 : 0,
    coverageWeightPct: matchedWeight * 100,
    confidencePct: weightedConfidence,
    portfolioSensitivityScore,
    portfolioImpactPct,
    portfolioImpactAmount,
  };
};

const EmptyMessage = ({ title, body }) => (
  <div className="stress-empty-card">
    <AlertTriangle size={22} />
    <div>
      <h3>{title}</h3>
      {body && <p>{body}</p>}
    </div>
  </div>
);

const AssetImpactList = ({ title, rows, emptyText, tone }) => (
  <section className="stress-list-card">
    <div className="stress-section-title">
      {tone === 'defense' ? <Shield size={16} /> : <TrendingDown size={16} />}
      <h3>{title}</h3>
    </div>
    {rows.length > 0 ? (
      <div className="stress-asset-list">
        {rows.map((row) => (
          <article className="stress-asset-row" key={`${title}-${row.ticker}`}>
            <div>
              <strong>{row.ticker}</strong>
              <span>{row.name}</span>
            </div>
            <div className="stress-asset-metrics">
              <span className={row.assetImpactPct >= 0 ? 'impact-positive' : 'impact-negative'}>
                {formatPct(row.assetImpactPct, 2)}
              </span>
              <small>{row.weightPct.toFixed(1)}% · beta {row.scenarioBeta.toFixed(3)}</small>
            </div>
          </article>
        ))}
      </div>
    ) : (
      <p className="stress-muted">{emptyText}</p>
    )}
  </section>
);

export const StressTest = () => {
  const navigate = useNavigate();
  const { portfolios, usdKrwRate } = usePortfolios();

  const [selectedPortfolioId, setSelectedPortfolioId] = useState(null);
  const [selectedScenarioCode, setSelectedScenarioCode] = useState('');
  const [scenarioDashboard, setScenarioDashboard] = useState(null);
  const [sensitivityRows, setSensitivityRows] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [dashboardError, setDashboardError] = useState('');
  const [sensitivityError, setSensitivityError] = useState('');

  const selectedPortfolio = portfolios.find((portfolio) => portfolio.id === selectedPortfolioId);

  useEffect(() => {
    if (!selectedPortfolioId && portfolios.length > 0) {
      setSelectedPortfolioId(portfolios[0].id);
    }
  }, [portfolios, selectedPortfolioId]);

  useEffect(() => {
    const controller = new AbortController();
    setIsLoading(true);
    setDashboardError('');
    setSensitivityError('');

    Promise.allSettled([
      getScenarioDashboard('', { signal: controller.signal, timeoutMs: 60 * 1000 }),
      getScenarioSensitivities({ signal: controller.signal, timeoutMs: 60 * 1000 }),
    ]).then(([dashboardResult, sensitivityResult]) => {
      if (controller.signal.aborted) return;
      if (dashboardResult.status === 'fulfilled') {
        setScenarioDashboard(dashboardResult.value);
      } else {
        setScenarioDashboard(null);
        setDashboardError(dashboardResult.reason?.message || '시장국면 데이터를 불러오지 못했습니다.');
      }

      if (sensitivityResult.status === 'fulfilled') {
        setSensitivityRows(sensitivityResult.value?.rows || []);
      } else {
        setSensitivityRows([]);
        setSensitivityError(sensitivityResult.reason?.message || '시장국면별 자산 민감도 데이터가 없어 계산할 수 없습니다.');
      }
    }).finally(() => {
      if (!controller.signal.aborted) setIsLoading(false);
    });

    return () => controller.abort();
  }, []);

  const scenarios = useMemo(() => collectScenarios(scenarioDashboard), [scenarioDashboard]);
  const sensitivityMap = useMemo(() => buildSensitivityMap(sensitivityRows), [sensitivityRows]);
  const portfolioAssets = useMemo(
    () => portfolioAssetsWithWeights(selectedPortfolio, usdKrwRate),
    [selectedPortfolio, usdKrwRate],
  );
  const totalValue = toNumber(selectedPortfolio?.totalValue ?? selectedPortfolio?.totalValueKrw);

  useEffect(() => {
    if (scenarios.length === 0) {
      setSelectedScenarioCode('');
      return;
    }
    if (!selectedScenarioCode || !scenarios.some((scenario) => scenario.code === selectedScenarioCode)) {
      setSelectedScenarioCode(scenarios[0].code);
    }
  }, [scenarios, selectedScenarioCode]);

  const scenarioResults = useMemo(
    () => scenarios.map((scenario) => calculateScenarioResult(scenario, portfolioAssets, sensitivityMap, totalValue)).filter(Boolean),
    [scenarios, portfolioAssets, sensitivityMap, totalValue],
  );
  const selectedResult = scenarioResults.find((result) => result.scenario.code === selectedScenarioCode) || scenarioResults[0] || null;
  const hasAnyMatch = scenarioResults.some((result) => result.matchedRows.length > 0);

  if (portfolios.length === 0) {
    return (
      <div className="stress-test-page">
        <div className="stress-empty-state">
          <div className="empty-icon"><Briefcase size={32} /></div>
          <h2>포트폴리오가 없습니다</h2>
          <p>분석을 시작하려면 먼저 자산을 등록해주세요.</p>
          <Button variant="primary" onClick={() => navigate('/register')} style={{ marginTop: '1.5rem' }}>
            포트폴리오 등록 <ArrowRight size={14} />
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="stress-test-page">
      <div className="stress-header">
        <span className="stress-eyebrow">Market Regime Simulation</span>
        <h1>현재시장국면별 리스크 시뮬레이션</h1>
        <p>미리 정해진 시장국면별 {STRESS_HORIZON_LABEL} 기준 리스크 시뮬레이션을 진행합니다.</p>
      </div>

      <section className="portfolio-select-card">
        <div className="portfolio-select-copy">
          <div className="icon-wrapper"><Briefcase size={18} /></div>
          <div>
            <h3>분석 대상 포트폴리오 선택</h3>
            <p>선택한 포트폴리오 보유 자산과 공식 민감도 데이터를 {STRESS_HORIZON_LABEL} 기준으로 계산합니다.</p>
          </div>
        </div>
        <div className="select-wrapper">
          <select
            value={selectedPortfolioId || ''}
            onChange={(event) => setSelectedPortfolioId(event.target.value)}
            className="portfolio-dropdown"
          >
            {portfolios.map((portfolio) => (
              <option key={portfolio.id} value={portfolio.id}>
                {portfolio.name} ({portfolio.assets.length}종목)
              </option>
            ))}
          </select>
        </div>
      </section>

      <section className="analysis-target-banner">
        <div className="target-info">
          <div className="target-icon-box"><CheckCircle2 size={20} /></div>
          <div className="target-text">
            <h4>현재 분석 대상</h4>
            <p>{selectedPortfolio?.name} · {portfolioAssets.length}개 자산 · {formatKrw(totalValue)} · {STRESS_HORIZON_LABEL} 기준</p>
          </div>
        </div>
        <div className="target-assets">
          {portfolioAssets.slice(0, 4).map((asset) => (
            <div key={asset.ticker} className="asset-pill">
              {asset.ticker} {asset.weightPct.toFixed(1)}%
            </div>
          ))}
          {portfolioAssets.length > 4 && <div className="asset-pill">+{portfolioAssets.length - 4}</div>}
        </div>
      </section>

      {isLoading && (
        <div className="stress-loading-card">
          <Loader2 size={24} className="spin-icon" />
          <span>시장국면과 자산 민감도 데이터를 불러오는 중입니다.</span>
        </div>
      )}

      {!isLoading && dashboardError && (
        <EmptyMessage title="시장국면 데이터를 불러오지 못했습니다." body={dashboardError} />
      )}

      {!isLoading && !dashboardError && scenarios.length === 0 && (
        <EmptyMessage title="시장국면 데이터를 불러오지 못했습니다." body="topActiveScenarios, topMarketRows, scenarioVectorLeaders에 표시할 국면이 없습니다." />
      )}

      {!isLoading && !dashboardError && sensitivityRows.length === 0 && (
        <EmptyMessage title="시장국면별 자산 민감도 데이터가 없어 계산할 수 없습니다." body={sensitivityError || 'scenario-sensitivities 응답에 rows가 없습니다.'} />
      )}

      {!isLoading && !dashboardError && scenarios.length > 0 && sensitivityRows.length > 0 && !hasAnyMatch && (
        <EmptyMessage title="선택 포트폴리오에 매칭되는 민감도 데이터가 부족합니다." body="보유 자산 ticker와 scenario_code가 민감도 데이터에 함께 존재하는지 확인하세요." />
      )}

      {!isLoading && selectedResult && hasAnyMatch && (
        <>
          <section className="scenario-tabs-card">
            <div className="stress-section-title">
              <TrendingUp size={16} />
              <h3>정식 시장국면</h3>
            </div>
            <div className="scenario-tab-grid">
              {scenarioResults.map((result) => {
                const scenario = result.scenario;
                return (
                  <button
                    type="button"
                    key={scenario.code}
                    className={`market-scenario-tab ${scenario.code === selectedResult.scenario.code ? 'active' : ''}`}
                    onClick={() => setSelectedScenarioCode(scenario.code)}
                  >
                    <span className="scenario-tab-state">{scenario.state}</span>
                    <strong>{scenario.name}</strong>
                    <span>{scenario.lens}</span>
                    <small>국면점수 {scenario.score.toFixed(1)} · 커버리지 {result.coveragePct.toFixed(0)}%</small>
                  </button>
                );
              })}
            </div>
          </section>

          <section className="selected-scenario-card">
            <div className="selected-scenario-heading">
              <div>
                <span className="stress-eyebrow">{selectedResult.favorable ? 'Favorable Regime' : 'Adverse Regime'}</span>
                <h2>{selectedResult.scenario.name}</h2>
                <p>{selectedResult.scenario.interpretation || selectedResult.scenario.englishName}</p>
              </div>
              <div className={`scenario-impact-pill ${selectedResult.portfolioImpactPct >= 0 ? 'positive' : 'negative'}`}>
                {formatPct(selectedResult.portfolioImpactPct, 2)}
              </div>
            </div>

            <div className="stress-result-grid">
              <div className="stress-metric-card">
                <span>{STRESS_HORIZON_LABEL} 충격률</span>
                <strong className={selectedResult.portfolioImpactPct >= 0 ? 'impact-positive' : 'impact-negative'}>
                  {formatPct(selectedResult.portfolioImpactPct, 2)}
                </strong>
                <small>현재 국면 강도 기반 스트레스 추정치</small>
              </div>
              <div className="stress-metric-card">
                <span>{STRESS_HORIZON_LABEL} 예상 손익</span>
                <strong className={selectedResult.portfolioImpactAmount >= 0 ? 'impact-positive' : 'impact-negative'}>
                  {formatKrw(selectedResult.portfolioImpactAmount)}
                </strong>
                <small>포트폴리오 총액 기준</small>
              </div>
              <div className="stress-metric-card">
                <span>국면 민감도 점수</span>
                <strong>{selectedResult.portfolioSensitivityScore.toFixed(2)}</strong>
                <small>보유비중 기준 · 시장국면 점수 {selectedResult.scenario.score.toFixed(1)}</small>
              </div>
              <div className="stress-metric-card">
                <span>데이터 커버리지</span>
                <strong>{selectedResult.coveragePct.toFixed(0)}%</strong>
                <small>비중 기준 {selectedResult.coverageWeightPct.toFixed(1)}%</small>
              </div>
              <div className="stress-metric-card">
                <span>신뢰도</span>
                <strong>{selectedResult.confidencePct.toFixed(1)}%</strong>
              </div>
            </div>
          </section>

          <div className="stress-two-column">
            <AssetImpactList
              title="취약 자산 TOP 5"
              rows={selectedResult.vulnerableAssets}
              tone="risk"
              emptyText="이 국면에서 음의 예상 충격을 보이는 보유 자산이 없습니다."
            />
            <AssetImpactList
              title="방어/상쇄 자산 TOP 5"
              rows={selectedResult.defensiveAssets}
              tone="defense"
              emptyText="이 국면에서 방어 또는 상쇄 역할을 보이는 보유 자산이 없습니다."
            />
          </div>

          <section className="scenario-comparison-card">
            <div className="stress-section-title">
              <TrendingDown size={16} />
              <h3>국면별 비교 테이블</h3>
            </div>
            <div className="stress-table-wrapper">
              <table className="scenario-comparison-table">
                <thead>
                  <tr>
                    <th>국면명</th>
                    <th>{STRESS_HORIZON_LABEL} 충격률</th>
                    <th>{STRESS_HORIZON_LABEL} 손익</th>
                    <th>취약 자산</th>
                    <th>방어 자산</th>
                    <th>커버리지</th>
                    <th>신뢰도</th>
                  </tr>
                </thead>
                <tbody>
                  {scenarioResults.map((result) => (
                    <tr
                      key={`compare-${result.scenario.code}`}
                      className={result.scenario.code === selectedResult.scenario.code ? 'selected' : ''}
                      onClick={() => setSelectedScenarioCode(result.scenario.code)}
                    >
                      <td>
                        <strong>{result.scenario.name}</strong>
                        <span>{result.scenario.code}</span>
                      </td>
                      <td className={result.portfolioImpactPct >= 0 ? 'impact-positive' : 'impact-negative'}>
                        {formatPct(result.portfolioImpactPct, 2)}
                      </td>
                      <td className={result.portfolioImpactAmount >= 0 ? 'impact-positive' : 'impact-negative'}>
                        {formatKrw(result.portfolioImpactAmount)}
                      </td>
                      <td>{result.vulnerableAssets.map((row) => row.ticker).join(', ') || '-'}</td>
                      <td>{result.defensiveAssets.map((row) => row.ticker).join(', ') || '-'}</td>
                      <td>{result.coveragePct.toFixed(0)}%</td>
                      <td>{result.confidencePct.toFixed(1)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </div>
  );
};
