import React, { useState, useCallback } from 'react';
import { AlertTriangle, CheckCircle2, Info, Loader2, Search, ShieldCheck } from 'lucide-react';
import { searchTickers, getTickerQuote } from '../services/yahooFinance';
import { getScenarioSensitivities, lookupAssetPrice } from '../services/hedgemateApi';
import { debounce, ASSET_DATABASE, generateSimulatedMetrics, normalizeTickerSymbol, searchAssetDatabase } from '../utils/helpers';
import './AssetSensitivity.css';

const STOCK_DB = ASSET_DATABASE;

const toNumber = (value, fallback = null) => {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
};

const pickNumber = (row, keys) => {
  for (const key of keys) {
    const number = toNumber(row?.[key]);
    if (Number.isFinite(number)) return number;
  }
  return null;
};

const scenarioName = (row) => row.scenario_name_ko || row.scenario_label_ko || row.scenario_code || row.scenario || '시장국면';

const betaMeaning = (beta) => {
  if (!Number.isFinite(beta)) return '데이터 없음';
  const abs = Math.abs(beta);
  if (beta < -0.35) return '반대로 움직여 완충 가능성';
  if (abs >= 1.2) return '크게 흔들림';
  if (abs >= 0.7) return '보통 이상으로 흔들림';
  if (abs >= 0.3) return '일부 영향';
  return '영향 낮음';
};

const evidenceLabel = (row) => {
  const source = row.source_quality || row.evidence_quality || 'unknown';
  if (source === 'market') return '시장 데이터';
  if (source === 'direct_beta') return '직접 beta';
  if (source === 'structural') return '구조적 매핑';
  if (source === 'seed') return '초기값';
  return source;
};

const summarizeOfficialRows = (rows) => {
  const enriched = rows
    .map((row) => ({
      ...row,
      beta: pickNumber(row, ['asset_scenario_beta', 'signed_sensitivity', 'scenario_beta', 'beta']),
    }))
    .filter((row) => Number.isFinite(row.beta));

  if (!enriched.length) return null;

  const ranked = [...enriched].sort((a, b) => Math.abs(b.beta) - Math.abs(a.beta));
  const top = ranked[0];
  const avgAbs = enriched.reduce((sum, row) => sum + Math.abs(row.beta), 0) / enriched.length;
  const gateEligible = enriched.filter((row) => String(row.gate_eligible || '').toUpperCase() !== 'N').length;
  const marketEvidence = enriched.filter((row) => ['market', 'direct_beta'].includes(String(row.source_quality || row.evidence_quality || '').toLowerCase())).length;
  const stressRows = enriched.filter((row) => Math.abs(row.beta) >= 0.7).length;
  const hedgeRows = enriched.filter((row) => row.beta < -0.25).length;

  return {
    rows: ranked,
    top,
    avgAbs,
    gateEligible,
    marketEvidence,
    stressRows,
    hedgeRows,
    scenarioCount: enriched.length,
    score: Math.max(0, Math.min(100, Math.round(100 - Math.min(75, avgAbs * 25)))),
  };
};

const baseAssetInfo = (ticker) => {
  const base = generateSimulatedMetrics(ticker);
  return {
    name: base.name,
    price: base.price ?? 0,
    sector: base.sector ?? 'Technology',
    logo: base.logo ?? ticker.substring(0, 3).toUpperCase(),
    logoColor: base.logoColor ?? '#3b82f6',
    currency: base.currency || 'USD',
    code: ticker,
  };
};

const displayValue = (value, digits = 2) => Number.isFinite(value) ? value.toFixed(digits) : '-';

export const AssetSensitivity = () => {
  const [selectedStockName, setSelectedStockName] = useState(null);
  const [stockData, setStockData] = useState(null);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [isSearching, setIsSearching] = useState(false);

  const stock = stockData;

  const debouncedSearch = useCallback(
    debounce(async (value) => {
      if (value.length < 1) {
        setSuggestions([]);
        return;
      }
      setIsSearching(true);
      const localMatches = searchAssetDatabase(value, 12);
      const remoteMatches = await searchTickers(value);
      const combined = [...localMatches];
      remoteMatches.forEach((remoteMatch) => {
        if (!combined.find((candidate) => candidate.ticker === remoteMatch.ticker)) {
          combined.push({ ...remoteMatch, source: 'yahoo' });
        }
      });
      setSuggestions(combined.slice(0, 8));
      setIsSearching(false);
    }, 300),
    []
  );

  const handleSearchChange = (event) => {
    const value = event.target.value;
    setSearchTerm(value);
    debouncedSearch(value);
  };

  const selectStock = async (item) => {
    setSearchOpen(false);
    setSearchTerm('');
    setSuggestions([]);

    const ticker = normalizeTickerSymbol(item.ticker);
    setSelectedStockName(ticker);

    const generated = baseAssetInfo(ticker);
    const db = STOCK_DB[ticker] || STOCK_DB[item.ticker] || {};
    let pricePayload = null;
    let quote = null;
    let officialRows = [];
    let officialSummary = null;

    try {
      pricePayload = await lookupAssetPrice({ ticker }, { useLivePrices: true });
    } catch (error) {
      console.warn('HedgeMate price lookup failed, falling back to Yahoo/static data:', error);
      quote = await getTickerQuote(ticker);
    }

    try {
      const payload = await getScenarioSensitivities({ ticker });
      officialRows = (payload.rows || []).filter((row) => normalizeTickerSymbol(row.ticker || row.asset_ticker || '') === ticker);
      officialSummary = summarizeOfficialRows(officialRows);
    } catch (error) {
      console.warn('Scenario sensitivity lookup failed:', error);
    }

    setStockData({
      ...generated,
      name: pricePayload?.displayName || quote?.name || item.name || db.name || generated.name,
      price: pricePayload?.latestPrice ?? quote?.price ?? 0,
      currency: pricePayload?.currency || quote?.currency || db.currency || generated.currency,
      logo: db.logo || item.logo || generated.logo,
      logoColor: db.logoColor || item.logoColor || generated.logoColor,
      sector: db.sector || generated.sector,
      code: ticker,
      priceAsOf: pricePayload?.priceAsOf || quote?.quoteSourceName || '',
      priceSource: pricePayload ? `HedgeMate ${pricePayload.dataMode === 'live' ? '실시간 조회' : '캐시'}` : (quote ? 'Yahoo 조회' : '가격 fallback'),
      priceWarnings: pricePayload?.warnings || [],
      officialRows,
      officialSummary,
      hasOfficialSensitivity: Boolean(officialSummary),
    });
  };

  const topRisk = stock?.officialSummary?.top;
  const hasOfficial = Boolean(stock?.hasOfficialSensitivity);

  return (
    <div className="sensitivity-page">
      <div className="report-header mb-6">
        <h1 className="mb-2">종목 리스크 읽기</h1>
        <p className="text-secondary text-sm">
          이 화면은 종목이 어떤 시장국면에서 흔들리는지 보여줍니다. 어려운 지표명보다 “어떤 위험에 약한가”, “근거가 충분한가”를 먼저 보여주고, 공식 산출물이 없으면 추정값을 공식처럼 표시하지 않습니다.
        </p>
      </div>

      {!stock ? (
        <div className="empty-state-container card-box sensitivity-empty">
          <div className="empty-search-icon">
            <Search size={28} />
          </div>
          <h2>종목 검색</h2>
          <p className="text-secondary text-sm">
            종목명이나 티커를 검색하면 최신 가격과 시나리오 리스크 연결을 확인할 수 있습니다.
          </p>

          <div className="sensitivity-search-wrap">
            <div className="search-input-container sensitivity-search-input">
              <input
                type="text"
                placeholder="예: 삼성전자, SK하이닉스, AAPL, 005930.KS"
                value={searchTerm}
                onChange={handleSearchChange}
                autoFocus
                className="stock-search-input"
              />
              <Search size={16} className="text-secondary search-input-icon" />
              {isSearching && <Loader2 size={16} className="spin-icon search-loader" />}
            </div>

            {suggestions.length > 0 && (
              <div className="stock-options-list mini-list sensitivity-suggestions">
                {suggestions.map((item) => (
                  <button
                    key={item.ticker}
                    type="button"
                    className="stock-option"
                    onClick={() => selectStock(item)}
                  >
                    <div className="mini-logo" style={{ backgroundColor: item.logoColor || '#3b82f6' }}>{item.logo || item.ticker.substring(0, 2)}</div>
                    <div className="flex-1">
                      <div className="text-sm font-medium">{item.name}</div>
                      <div className="text-xs text-secondary">{item.ticker}</div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="sensitivity-grid mt-6">
          <div className="flex-col gap-4 left-dash">
            <div className="card-box asset-info-card" style={{ minHeight: '240px', position: 'relative' }}>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-4">
                  <div className="brand-logo" style={{ backgroundColor: stock.logoColor }}>{stock.logo}</div>
                  <div>
                    <h3 className="font-bold text-xl m-0 truncate max-w-[120px]">{stock.name || selectedStockName}</h3>
                    <div className="text-xs text-secondary tracking-widest mt-1">{stock.code}</div>
                  </div>
                </div>
                <button className="icon-btn-search" onClick={() => setSearchOpen(!searchOpen)}>
                  <Search size={18} className="text-secondary" />
                </button>
              </div>

              {searchOpen && (
                <div className="card-search-container">
                  <div className="search-input-container">
                    <input
                      type="text"
                      placeholder="종목명 또는 티커 검색"
                      value={searchTerm}
                      onChange={handleSearchChange}
                      autoFocus
                      className="stock-search-input"
                    />
                    {isSearching && <Loader2 size={14} className="spin-icon search-loader" />}
                  </div>
                  <div className="stock-options-list mini-list">
                    {suggestions.map((item) => (
                      <button
                        key={item.ticker}
                        type="button"
                        className="stock-option"
                        onClick={() => selectStock(item)}
                      >
                        <div className="mini-logo" style={{ backgroundColor: item.logoColor || '#3b82f6' }}>{item.logo || item.ticker.substring(0, 2)}</div>
                        <div className="flex-1">
                          <div className="text-sm font-medium">{item.name}</div>
                          <div className="text-xs text-secondary">{item.ticker}</div>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div className="mt-6">
                <div className="text-xs text-secondary font-semibold tracking-wider mb-2">최신 가격</div>
                <div className="flex items-end gap-2">
                  <span className="text-3xl font-bold tracking-tight">
                    {stock.currency === 'KRW' ? '₩' : '$'}{Number(stock.price || 0).toLocaleString()}
                  </span>
                </div>
                <div className="text-xs text-secondary mt-2">
                  {stock.priceSource || '가격 출처 확인 필요'}{stock.priceAsOf ? ` · 기준: ${stock.priceAsOf}` : ''}
                </div>
                {stock.priceWarnings?.length > 0 && (
                  <div className="text-xs text-secondary mt-1">{stock.priceWarnings[0]}</div>
                )}
              </div>

              <div className="flex justify-between text-xs font-medium border-t pt-3 mt-4" style={{ borderColor: 'var(--border-color)' }}>
                <div className="text-secondary">분류</div>
                <div>{stock.sector}</div>
              </div>
              <div className="flex justify-between text-xs font-medium mt-1">
                <div className="text-secondary">리스크 근거</div>
                <div>{hasOfficial ? '공식 산출물 있음' : '공식 산출물 없음'}</div>
              </div>
            </div>

            <div className="card-box flex-1">
              <div className="flex justify-between items-center mb-6">
                <span className="font-bold">한줄 판단</span>
                <span className={hasOfficial ? 'badge-green' : 'badge-purple'}>
                  {hasOfficial ? '공식 데이터' : '가격만 확인'}
                </span>
              </div>

              {hasOfficial ? (
                <>
                  <div className="risk-summary-number" style={{ color: Math.abs(topRisk.beta) >= 0.7 ? '#f59e0b' : '#34d399' }}>
                    {Math.abs(topRisk.beta).toFixed(2)}
                  </div>
                  <div className="text-center text-sm font-bold mt-2 mb-6">
                    가장 크게 흔들리는 국면: {scenarioName(topRisk)}
                  </div>
                  <div className="diagnosis-item flex gap-3 mb-4">
                    <ShieldCheck size={16} className="shrink-0 mt-1" style={{ color: '#059669' }} />
                    <div>
                      <div className="text-xs font-bold mb-1">읽는 법</div>
                      <div className="text-xs text-secondary">
                        숫자의 절댓값이 클수록 해당 시장국면에서 이 종목이 크게 움직인다는 뜻입니다. 음수면 반대로 움직여 완충 역할을 할 가능성이 있습니다.
                      </div>
                    </div>
                  </div>
                  <div className="diagnosis-item flex gap-3">
                    <AlertTriangle size={16} className="text-warning shrink-0 mt-1" />
                    <div>
                      <div className="text-xs font-bold mb-1">주의점</div>
                      <div className="text-xs text-secondary">
                        이 화면은 종목 단독 리스크 설명입니다. 실행 가능한 헷지 액션은 포트폴리오 리포트에서 다시 gate 검증을 통과해야 합니다.
                      </div>
                    </div>
                  </div>
                </>
              ) : (
                <div className="empty-official-box">
                  <Info size={18} />
                  <div>
                    <strong>이 종목의 공식 리스크 산출물이 없습니다.</strong>
                    <p>가격은 조회했지만 움직임 점수나 같이 움직임 값을 임의로 만들어 공식처럼 보여주지 않습니다.</p>
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="flex-col gap-4 right-dash">
            <div className="metric-row-grid">
              <div className="card-box p-4 metric-card-hover" title="이 종목이 가장 크게 흔들린 시장국면입니다.">
                <div className="flex justify-between items-start mb-2">
                  <span className="text-xs text-secondary font-semibold tracking-wider">가장 취약한 국면</span>
                  <Info size={12} className="text-secondary" />
                </div>
                <div className="metric-friendly-value">{hasOfficial ? scenarioName(topRisk) : '-'}</div>
                <div className="text-xs text-secondary mt-2">{hasOfficial ? betaMeaning(topRisk.beta) : '공식 데이터 없음'}</div>
              </div>
              <div className="card-box p-4 metric-card-hover" title="시장국면별 움직임의 평균 크기입니다.">
                <div className="flex justify-between items-start mb-2">
                  <span className="text-xs text-secondary font-semibold tracking-wider">전체 흔들림 크기</span>
                  <ShieldCheck size={12} className="text-secondary" />
                </div>
                <div className="text-2xl font-bold mt-2">{hasOfficial ? displayValue(stock.officialSummary.avgAbs, 2) : '-'}</div>
                <div className="text-xs text-secondary mt-1">낮을수록 여러 국면에서 덜 민감합니다.</div>
              </div>
              <div className="card-box p-4 metric-card-hover" title="추천 판단에 쓸 수 있는 수준의 산출물이 몇 개인지 보여줍니다.">
                <div className="flex justify-between items-start mb-2">
                  <span className="text-xs text-secondary font-semibold tracking-wider">근거 품질</span>
                  <CheckCircle2 size={12} className="text-secondary" />
                </div>
                <div className="text-2xl font-bold mt-2">{hasOfficial ? `${stock.officialSummary.marketEvidence}/${stock.officialSummary.scenarioCount}` : '-'}</div>
                <div className="text-xs text-secondary mt-1">시장 데이터 기반 / 전체 시나리오</div>
              </div>
              <div className="card-box p-4 metric-card-hover" title="추천 gate에서 쓸 수 있는 행 수입니다.">
                <div className="flex justify-between items-start mb-2">
                  <span className="text-xs text-secondary font-semibold tracking-wider">분석 범위</span>
                  <Info size={12} className="text-secondary" />
                </div>
                <div className="text-2xl font-bold mt-2">{hasOfficial ? `${stock.officialSummary.gateEligible}개` : '-'}</div>
                <div className="text-xs text-secondary mt-1">추천 판단에 사용 가능한 시나리오</div>
              </div>
            </div>

            <div className="card-box flex-1">
              <div className="flex justify-between items-center mb-6">
                <span className="font-bold">시장국면별 반응</span>
                <div className="text-xs text-secondary">
                  {hasOfficial ? `${stock.officialSummary.scenarioCount}개 공식 행` : '공식 데이터 없음'}
                </div>
              </div>

              {hasOfficial ? (
                <>
                  <div className="official-sensitivity-table">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>시장국면</th>
                          <th>움직임</th>
                          <th>뜻</th>
                          <th>근거</th>
                          <th>추천 판단</th>
                        </tr>
                      </thead>
                      <tbody>
                        {stock.officialSummary.rows.slice(0, 12).map((row, index) => (
                          <tr key={`${row.scenario_code || row.scenario}-${index}`}>
                            <td>{scenarioName(row)}</td>
                            <td>{Number(row.beta).toFixed(3)}</td>
                            <td>{betaMeaning(row.beta)}</td>
                            <td>{evidenceLabel(row)}</td>
                            <td>{String(row.gate_eligible || '').toUpperCase() === 'N' ? '참고용' : '사용 가능'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div className="heatmap-note mt-6 text-xs text-secondary">
                    <span className="text-accent-light font-bold">읽는 법:</span> 움직임 값은 시장국면별 반응 크기입니다. 1에 가까우면 그 국면과 비슷하게 크게 움직이고, 0에 가까우면 영향이 작고, 음수면 반대로 움직인다는 뜻입니다.
                  </div>
                </>
              ) : (
                <div className="empty-official-box">
                  <AlertTriangle size={18} />
                  <div>
                    <strong>공식 리스크 행이 없습니다.</strong>
                    <p>이 경우 HedgeMate는 있어 보이는 임의 점수를 만들지 않습니다. 포트폴리오 리포트에서는 데이터 부족 또는 참고용 후보로 처리됩니다.</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
