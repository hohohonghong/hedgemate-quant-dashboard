const rawApiUrl = import.meta.env?.VITE_HEDGEMATE_API_URL;

const normalizeApiBase = (value) => {
  if (!value) return '/api';
  const trimmed = String(value).replace(/\/+$/, '');
  return trimmed.endsWith('/api') || trimmed.includes('/api/')
    ? trimmed
    : `${trimmed}/api`;
};

const API_BASE = normalizeApiBase(rawApiUrl);
const DEFAULT_REQUEST_TIMEOUT_MS = 30 * 1000;

const KOREAN_ASSET_ALIASES = {
  SAMSUNG: '005930.KS',
  '삼성전자': '005930.KS',
  '삼성': '005930.KS',
  '005930': '005930.KS',
  HYNIX: '000660.KS',
  SKHYNIX: '000660.KS',
  'SK하이닉스': '000660.KS',
  '하이닉스': '000660.KS',
  '000660': '000660.KS',
  KIA: '000270.KS',
  '기아': '000270.KS',
  '000270': '000270.KS',
  HYUNDAI: '005380.KS',
  '현대차': '005380.KS',
  '현대자동차': '005380.KS',
  NAVER: '035420.KS',
  '네이버': '035420.KS',
  KAKAO: '035720.KS',
  '카카오': '035720.KS',
};

export const resolveBackendAssetId = (asset = {}) => {
  const candidates = [asset.ticker, asset.symbol, asset.code, asset.asset, asset.name];
  for (const raw of candidates) {
    const value = String(raw || '').trim();
    if (!value) continue;
    const upper = value.toUpperCase();
    return KOREAN_ASSET_ALIASES[value] || KOREAN_ASSET_ALIASES[upper] || value;
  }
  return '';
};

const maybeNumber = (value) => {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
};

const assetAmountKrw = (asset, portfolio, options = {}) => {
  const explicit = maybeNumber(asset.amountKrw ?? asset.marketValueKrw ?? asset.valueKrw);
  if (explicit && explicit > 0) return explicit;

  const total = maybeNumber(portfolio?.totalValue ?? portfolio?.totalValueKrw);
  const weight = maybeNumber(asset.weight ?? asset.weightPct ?? asset.currentWeight);
  if (total && total > 0 && weight && weight > 0) {
    return (total * weight) / 100;
  }

  const qty = maybeNumber(asset.qty ?? asset.quantity);
  const cost = maybeNumber(asset.cost ?? asset.price ?? asset.unitPrice);
  if (qty && qty > 0 && cost && cost > 0) {
    const currency = String(asset.currency || '').toUpperCase();
    const fx = currency === 'USD' ? maybeNumber(options.usdKrwRate) || 1380 : 1;
    return qty * cost * fx;
  }

  return null;
};

export const toBackendPortfolioRows = (portfolio, options = {}) => {
  return (portfolio?.assets || [])
    .map((asset) => {
      const assetId = resolveBackendAssetId(asset);
      const quantity = maybeNumber(asset.qty ?? asset.quantity);
      const amountKrw = quantity && quantity > 0
        ? null
        : assetAmountKrw(asset, portfolio, options);
      return {
        asset: assetId,
        ticker: assetId,
        quantity: quantity && quantity > 0 ? quantity : undefined,
        amountKrw: amountKrw && amountKrw > 0 ? Math.round(amountKrw) : undefined,
      };
    })
    .filter((row) => row.asset);
};

const parseApiError = async (response) => {
  try {
    const payload = await response.json();
    return payload.error || payload.message || `${response.status} ${response.statusText}`;
  } catch {
    return `${response.status} ${response.statusText}`;
  }
};

const hedgemateFetch = async (path, options = {}) => {
  const {
    timeoutMs = DEFAULT_REQUEST_TIMEOUT_MS,
    signal,
    ...fetchOptions
  } = options;
  const controller = new AbortController();
  let timedOut = false;
  const timeoutId = timeoutMs > 0
    ? setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, timeoutMs)
    : null;
  const abortFromCaller = () => controller.abort();
  if (signal) {
    if (signal.aborted) abortFromCaller();
    else signal.addEventListener('abort', abortFromCaller, { once: true });
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...fetchOptions,
    signal: controller.signal,
    headers: {
      ...(fetchOptions.body ? { 'Content-Type': 'application/json' } : {}),
      ...(fetchOptions.headers || {}),
    },
  }).catch((error) => {
    if (signal?.aborted) {
      const abortError = new Error('요청이 취소되었습니다.');
      abortError.name = 'AbortError';
      throw abortError;
    }
    if (timedOut) {
      const timeoutError = new Error('요청 시간이 초과되었습니다.');
      timeoutError.name = 'TimeoutError';
      throw timeoutError;
    }
    throw error;
  }).finally(() => {
    if (timeoutId) clearTimeout(timeoutId);
    if (signal) signal.removeEventListener('abort', abortFromCaller);
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response));
  }
  return response.json();
};

export const getHedgeMateHealth = (options = {}) => hedgemateFetch('/health', options);

export const getHedgeMateStatus = (options = {}) => hedgemateFetch('/status', options);

export const getAssets = (options = {}) => hedgemateFetch('/assets', options);

export const getProductDashboard = (options = {}) => {
  const compact = options.compact !== false;
  if (options.portfolio) {
    return hedgemateFetch('/product-dashboard', {
      method: 'POST',
      signal: options.signal,
      timeoutMs: options.timeoutMs,
      body: JSON.stringify({
        portfolioRows: toBackendPortfolioRows(options.portfolio, options),
        hedgeBudgetKrw: options.hedgeBudgetKrw ?? '',
        maxComboSize: options.maxComboSize ?? 2,
        dataVersion: options.dataVersion,
        useLivePrices: options.useLivePrices !== false,
        mutateActiveBundle: Boolean(options.mutateActiveBundle),
        compact,
      }),
    });
  }
  return hedgemateFetch(`/product-dashboard${compact ? '?compact=1' : ''}`, {
    signal: options.signal,
    timeoutMs: options.timeoutMs,
  });
};

export const getScenarioSensitivities = (options = {}) => {
  const ticker = typeof options === 'string' ? options : options.ticker;
  const query = ticker ? `?ticker=${encodeURIComponent(resolveBackendAssetId({ ticker }))}` : '';
  return hedgemateFetch(`/scenario-sensitivities${query}`, typeof options === 'string' ? {} : {
    signal: options.signal,
    timeoutMs: options.timeoutMs,
  });
};

export const getScenarioRuns = (options = {}) => hedgemateFetch('/scenario-runs', options);

export const getScenarioDashboard = (runId, options = {}) => {
  const query = runId ? `?run_id=${encodeURIComponent(runId)}` : '';
  return hedgemateFetch(`/scenario-dashboard${query}`, options);
};

export const lookupAssetPrice = (asset, options = {}) => {
  const assetId = typeof asset === 'string' ? resolveBackendAssetId({ ticker: asset }) : resolveBackendAssetId(asset);
  return hedgemateFetch('/price-lookup', {
    method: 'POST',
    signal: options.signal,
    timeoutMs: options.timeoutMs,
    body: JSON.stringify({
      asset: assetId,
      ticker: assetId,
      quantity: options.quantity,
      amountKrw: options.amountKrw,
      useLivePrices: options.useLivePrices !== false,
      dataVersion: options.dataVersion,
    }),
  });
};

export const previewPortfolio = (portfolio, options = {}) => {
  return hedgemateFetch('/portfolio/preview', {
    method: 'POST',
    signal: options.signal,
    timeoutMs: options.timeoutMs,
    body: JSON.stringify({
      portfolioRows: toBackendPortfolioRows(portfolio, options),
      useLivePrices: options.useLivePrices !== false,
      dataVersion: options.dataVersion,
    }),
  });
};

export const runPortfolioAnalysis = (portfolio, options = {}) => {
  return hedgemateFetch('/run', {
    method: 'POST',
    signal: options.signal,
    timeoutMs: options.timeoutMs,
    body: JSON.stringify({
      mode: 'portfolio',
      portfolioRows: toBackendPortfolioRows(portfolio, options),
      hedgeBudgetKrw: options.hedgeBudgetKrw ?? '',
      hedgeBudgets: options.hedgeBudgets,
      maxComboSize: options.maxComboSize ?? 2,
      dataVersion: options.dataVersion,
      useLivePrices: options.useLivePrices !== false,
      forceRefreshRaw: Boolean(options.forceRefreshRaw),
    }),
  });
};

export const getRunStatus = (jobId, options = {}) => {
  return hedgemateFetch(`/run-status?job_id=${encodeURIComponent(jobId)}`, options);
};

export const refreshMarketData = (payload = {}, options = {}) => {
  return hedgemateFetch('/refresh-market-data', {
    method: 'POST',
    signal: options.signal,
    timeoutMs: options.timeoutMs,
    body: JSON.stringify(payload),
  });
};

export const pollRunStatus = async (jobId, onUpdate, options = {}) => {
  const intervalMs = options.intervalMs ?? 2500;
  const timeoutMs = options.timeoutMs ?? 15 * 60 * 1000;
  const stagnantStageMs = options.stagnantStageMs ?? 5 * 60 * 1000;
  const signal = options.signal;
  const started = Date.now();
  let lastStageKey = '';
  let lastStageChangedAt = started;

  while (Date.now() - started < timeoutMs) {
    if (signal?.aborted) {
      const abortError = new Error('요청이 취소되었습니다.');
      abortError.name = 'AbortError';
      throw abortError;
    }
    const status = await getRunStatus(jobId, {
      signal,
      timeoutMs: options.requestTimeoutMs ?? 20 * 1000,
    });
    const stageKey = `${status.status || ''}:${status.stage || ''}:${status.currentStep || ''}`;
    if (stageKey !== lastStageKey) {
      lastStageKey = stageKey;
      lastStageChangedAt = Date.now();
    }
    const stagnant = Date.now() - lastStageChangedAt >= stagnantStageMs;
    const enriched = {
      ...status,
      elapsedSeconds: status.elapsedSeconds ?? Math.floor((Date.now() - started) / 1000),
      stagnantStage: stagnant,
      estimatedRemainingMessage: stagnant
        ? (status.estimatedRemainingMessage || '같은 단계가 오래 지속되고 있습니다. 백테스트, gate 검증, active bundle 갱신 단계에서 시간이 걸릴 수 있습니다.')
        : status.estimatedRemainingMessage,
    };
    onUpdate?.(enriched);
    if (status.status === 'completed' || status.status === 'failed' || status.error) {
      return enriched;
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }

  throw new Error('분석 작업 시간이 초과되었습니다. 이전 결과는 실행 가능한 추천으로 표시하지 않습니다.');
};
