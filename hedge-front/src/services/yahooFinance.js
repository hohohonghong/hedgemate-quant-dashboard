/**
 * Yahoo Finance API Service
 * Uses the same-origin backend Yahoo proxy in production and Vite proxy in dev.
 */

const rawYahooApiUrl = import.meta.env?.VITE_YAHOO_API_URL;
const YAHOO_API_BASE = rawYahooApiUrl
  ? String(rawYahooApiUrl).replace(/\/+$/, '')
  : '/api/yahoo';

const CACHE = {
  search: new Map(),
  quotes: new Map(),
};

const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

export const searchTickers = async (query, options = {}) => {
  if (!query || query.length < 1) return [];
  
  const cacheKey = query.toLowerCase().trim();
  if (CACHE.search.has(cacheKey)) {
    const { data, timestamp } = CACHE.search.get(cacheKey);
    if (Date.now() - timestamp < CACHE_TTL) return data;
  }

  try {
    const response = await fetch(`${YAHOO_API_BASE}/v1/finance/search?q=${encodeURIComponent(query)}&quotesCount=10&newsCount=0`);
    if (!response.ok) throw new Error('Network response was not ok');
    
    const data = await response.json();
    const results = (data.quotes || []).map(quote => ({
      ticker: quote.symbol,
      name: quote.shortname || quote.longname || quote.symbol,
      exchange: quote.exchange,
      type: quote.quoteType,
    }));

    CACHE.search.set(cacheKey, { data: results, timestamp: Date.now() });
    return results;
  } catch (error) {
    if (options.throwOnError) throw error;
    return [];
  }
};

export const getTickerQuote = async (ticker) => {
  if (!ticker) return null;
  
  const cacheKey = ticker.toUpperCase().trim();
  if (CACHE.quotes.has(cacheKey)) {
    const { data, timestamp } = CACHE.quotes.get(cacheKey);
    if (Date.now() - timestamp < CACHE_TTL) return data;
  }

  try {
    const chartQuote = await getTickerQuoteFromChart(ticker);
    if (chartQuote) {
      CACHE.quotes.set(cacheKey, { data: chartQuote, timestamp: Date.now() });
      return chartQuote;
    }
  } catch {
    // Continue to the quote endpoint as a secondary fallback.
  }

  try {
    const response = await fetch(`${YAHOO_API_BASE}/v7/finance/quote?symbols=${encodeURIComponent(ticker)}`);
    if (!response.ok) throw new Error('Network response was not ok');
    
    const data = await response.json();
    const quote = data.quoteResponse?.result?.[0];
    
    if (!quote) return null;
    
    const result = {
      ticker: quote.symbol,
      name: quote.shortName || quote.longName || quote.symbol,
      price: quote.regularMarketPrice,
      currency: quote.currency,
      exchange: quote.exchange,
      change: quote.regularMarketChange,
      changePercent: quote.regularMarketChangePercent,
    };

    CACHE.quotes.set(cacheKey, { data: result, timestamp: Date.now() });
    return result;
  } catch {
    // The unauthenticated Yahoo quote endpoint can return 401 even when the
    // chart fallback or HedgeMate price lookup has usable cached prices.
    return null;
  }
};

const getTickerQuoteFromChart = async (ticker) => {
  const response = await fetch(`${YAHOO_API_BASE}/v8/finance/chart/${encodeURIComponent(ticker)}?range=5d&interval=1d`);
  if (!response.ok) throw new Error('Chart fallback response was not ok');

  const data = await response.json();
  const result = data.chart?.result?.[0];
  if (!result) return null;

  const meta = result.meta || {};
  const closes = result.indicators?.quote?.[0]?.close || [];
  const latestClose = [...closes].reverse().find((price) => Number.isFinite(Number(price)));
  const price = meta.regularMarketPrice ?? latestClose;
  if (!Number.isFinite(Number(price))) return null;

  return {
    ticker: meta.symbol || ticker,
    name: meta.shortName || meta.longName || meta.symbol || ticker,
    price: Number(price),
    currency: meta.currency,
    exchange: meta.exchangeName || meta.fullExchangeName,
    change: null,
    changePercent: null,
    source: 'yahoo_chart',
  };
};

export const getTickerHistory = async (ticker, range = '1y', interval = '1d') => {
  if (!ticker) return null;
  
  try {
    const response = await fetch(`${YAHOO_API_BASE}/v8/finance/chart/${encodeURIComponent(ticker)}?range=${range}&interval=${interval}`);
    if (!response.ok) throw new Error('Network response was not ok');
    
    const data = await response.json();
    const result = data.chart?.result?.[0];
    
    if (!result) return null;
    
    const timestamps = result.timestamp || [];
    const prices = result.indicators?.quote?.[0]?.close || [];
    
    // Calculate daily returns
    const returns = [];
    for (let i = 1; i < prices.length; i++) {
      if (prices[i] && prices[i-1]) {
        returns.push((prices[i] - prices[i-1]) / prices[i-1]);
      }
    }
    
    return {
      ticker: result.meta.symbol,
      prices,
      timestamps,
      returns
    };
  } catch (error) {
    console.error('Error fetching ticker history:', error);
    return null;
  }
};
