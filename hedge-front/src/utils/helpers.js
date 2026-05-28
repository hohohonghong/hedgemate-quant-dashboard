/**
 * Utility Helpers
 */

/**
 * Simple debounce implementation
 */
export const debounce = (func, wait) => {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
};

/**
 * Shared metadata/risk defaults for common tickers.
 * Do not treat the embedded price fields as live quotes; screens must prefer
 * HedgeMate price lookup or Yahoo quote data for any displayed price.
 */
export const TICKER_ALIASES = {
  SAMSUNG: '005930.KS',
  '삼성전자': '005930.KS',
  '삼성': '005930.KS',
  '005930': '005930.KS',
  SKHYNIX: '000660.KS',
  HYNIX: '000660.KS',
  'SK하이닉스': '000660.KS',
  '하이닉스': '000660.KS',
  '000660': '000660.KS',
  KIA: '000270.KS',
  '기아': '000270.KS',
  '000270': '000270.KS',
  HYUNDAI: '005380.KS',
  '현대차': '005380.KS',
  '현대자동차': '005380.KS',
  '005380': '005380.KS',
  NAVER: '035420.KS',
  '네이버': '035420.KS',
  '035420': '035420.KS',
  KAKAO: '035720.KS',
  '카카오': '035720.KS',
  '035720': '035720.KS',
  SAMSUNGBIO: '207940.KS',
  '삼성바이오로직스': '207940.KS',
  '207940': '207940.KS',
  HMM: '011200.KS',
  '에이치엠엠': '011200.KS',
  '011200': '011200.KS',
};

export const normalizeTickerSymbol = (ticker) => {
  const raw = String(ticker || '').trim();
  if (!raw) return '';
  const upper = raw.toUpperCase();
  return TICKER_ALIASES[upper] || TICKER_ALIASES[raw] || upper;
};

export const isKoreanTicker = (ticker) => {
  const normalized = normalizeTickerSymbol(ticker);
  return normalized.endsWith('.KS') || /^[0-9]{6}$/.test(normalized);
};

export const ASSET_DATABASE = {
  'AAPL':  { name: 'Apple Inc.',       price: 178.72, sector: 'Technology',          riskVol: 14.2, sp500Beta: 1.05, downsideBeta: 0.88, score: 96, logo: 'AAPL', logoColor: '#555', currency: 'USD' },
  'NVDA':  { name: 'NVIDIA Corp.',      price: 875.28, sector: 'Technology',          riskVol: 28.7, sp500Beta: 1.68, downsideBeta: 1.12, score: 88, logo: 'NVDA', logoColor: '#76b900', currency: 'USD' },
  'MSFT':  { name: 'Microsoft Corp.',   price: 415.50, sector: 'Technology',          riskVol: 12.8, sp500Beta: 0.95, downsideBeta: 0.72, score: 97, logo: 'MSFT', logoColor: '#00a4ef', currency: 'USD' },
  'TSLA':  { name: 'Tesla Inc.',        price: 171.05, sector: 'Consumer Cyclical',  riskVol: 42.3, sp500Beta: 1.92, downsideBeta: 1.35, score: 72, logo: 'TSLA', logoColor: '#e81d23', currency: 'USD' },
  'BTC':   { name: 'Bitcoin',           price: 67420,  sector: 'Digital Asset',      riskVol: 58.1, sp500Beta: 2.15, downsideBeta: 1.85, score: 65, logo: 'BTC',  logoColor: '#f7931a', currency: 'USD' },
  'GOOGL': { name: 'Alphabet Inc.',     price: 141.80, sector: 'Communication',     riskVol: 16.5, sp500Beta: 1.12, downsideBeta: 0.92, score: 94, logo: 'GOOG', logoColor: '#4285f4', currency: 'USD' },
  '005930.KS': { name: '삼성전자',      price: 293000, sector: 'Technology',          riskVol: 15.2, sp500Beta: 0.95, downsideBeta: 0.72, score: 91, logo: 'SEC',  logoColor: '#1d4ed8', currency: 'KRW', aliases: ['삼성', 'SAMSUNG'] },
  '000660.KS': { name: 'SK하이닉스',    price: 244000, sector: 'Technology',          riskVol: 24.8, sp500Beta: 1.36, downsideBeta: 1.02, score: 86, logo: 'HYN',  logoColor: '#ef4444', currency: 'KRW', aliases: ['하이닉스', 'HYNIX', 'SKHYNIX'] },
  '000270.KS': { name: '기아',          price: 111200, sector: 'Consumer Cyclical',  riskVol: 18.4, sp500Beta: 1.24, downsideBeta: 0.88, score: 82, logo: 'KIA',  logoColor: '#ef4444', currency: 'KRW', aliases: ['KIA'] },
  '005380.KS': { name: '현대차',        price: 247000, sector: 'Consumer Cyclical',  riskVol: 19.2, sp500Beta: 1.18, downsideBeta: 0.91, score: 80, logo: 'HYU',  logoColor: '#2563eb', currency: 'KRW', aliases: ['현대자동차', 'HYUNDAI'] },
  '035420.KS': { name: '네이버',        price: 188000, sector: 'Communication',      riskVol: 23.3, sp500Beta: 1.11, downsideBeta: 1.04, score: 78, logo: 'NAV',  logoColor: '#22c55e', currency: 'KRW', aliases: ['NAVER'] },
  '035720.KS': { name: '카카오',        price: 43200,  sector: 'Communication',      riskVol: 31.4, sp500Beta: 1.33, downsideBeta: 1.21, score: 69, logo: 'KAK',  logoColor: '#facc15', currency: 'KRW', aliases: ['KAKAO'] },
  '207940.KS': { name: '삼성바이오로직스', price: 813000, sector: 'Healthcare',      riskVol: 17.8, sp500Beta: 0.78, downsideBeta: 0.71, score: 84, logo: 'BIO',  logoColor: '#0ea5e9', currency: 'KRW', aliases: ['SAMSUNGBIO'] },
  '011200.KS': { name: 'HMM',           price: 18300,  sector: 'Industrials',        riskVol: 29.5, sp500Beta: 1.07, downsideBeta: 1.16, score: 64, logo: 'HMM',  logoColor: '#64748b', currency: 'KRW', aliases: ['에이치엠엠'] },
  'SAMSUNG': { name: '삼성전자',        price: 293000, sector: 'Technology',          riskVol: 15.2, sp500Beta: 0.95, downsideBeta: 0.72, score: 91, logo: 'SEC',  logoColor: '#1d4ed8', currency: 'KRW', aliasFor: '005930.KS' },
  'HYNIX': { name: 'SK하이닉스',         price: 244000, sector: 'Technology',          riskVol: 24.8, sp500Beta: 1.36, downsideBeta: 1.02, score: 86, logo: 'HYN',  logoColor: '#ef4444', currency: 'KRW', aliasFor: '000660.KS' },
  'KIA':   { name: '기아',              price: 111200, sector: 'Consumer Cyclical',  riskVol: 18.4, sp500Beta: 1.24, downsideBeta: 0.88, score: 82, logo: 'KIA',  logoColor: '#ef4444', currency: 'KRW', aliasFor: '000270.KS' },
};

export const searchAssetDatabase = (query, limit = 12) => {
  const raw = String(query || '').trim();
  const normalized = normalizeTickerSymbol(raw);
  const lower = raw.toLowerCase();
  const seen = new Set();
  const results = [];

  Object.entries(ASSET_DATABASE).forEach(([key, value]) => {
    const ticker = normalizeTickerSymbol(value.aliasFor || key);
    const data = ASSET_DATABASE[ticker] || value;
    const searchText = [
      key,
      ticker,
      data.name,
      data.sector,
      ...(data.aliases || []),
    ].filter(Boolean).join(' ').toLowerCase();
    const matchesEmpty = !raw;
    const matchesQuery = searchText.includes(lower) || ticker.includes(normalized) || key.includes(normalized);

    if ((matchesEmpty || matchesQuery) && !seen.has(ticker)) {
      seen.add(ticker);
      results.push({
        ticker,
        name: data.name,
        price: null,
        currency: data.currency,
        logo: data.logo,
        logoColor: data.logoColor,
        source: 'local',
        isLocal: true,
      });
    }
  });

  return results.slice(0, limit);
};

/**
 * Shared data generator for simulated metrics
 */
export const generateSimulatedMetrics = (ticker) => {
  const normalizedTicker = normalizeTickerSymbol(ticker);
  if (ASSET_DATABASE[normalizedTicker]) return ASSET_DATABASE[normalizedTicker];
  if (ASSET_DATABASE[ticker]) return ASSET_DATABASE[ticker];

  let hash = 0;
  for (let i = 0; i < ticker.length; i++) {
    hash = ticker.charCodeAt(i) + ((hash << 5) - hash);
  }
  const r = Math.abs(hash);
  
  const sp500Beta = parseFloat((0.5 + (r % 150) / 100).toFixed(2));
  const downsideBeta = parseFloat((0.4 + ((r >> 2) % 120) / 100).toFixed(2));
  const riskVol = parseFloat((10 + (r % 50)).toFixed(1));
  const score = 40 + (r % 55);
  
  const sectors = ['Technology', 'Financial', 'Consumer Cyclical', 'Energy', 'Communication', 'Healthcare'];
  
  return {
    ticker,
    name: `${ticker} Asset (AI Calc)`,
    price: 100 + (r % 1000),
    sector: sectors[r % sectors.length],
    riskVol,
    sp500Beta,
    downsideBeta,
    score,
    logo: ticker.substring(0, 3).toUpperCase(),
    logoColor: `hsl(${r % 360}, 60%, 45%)`
  };
};
