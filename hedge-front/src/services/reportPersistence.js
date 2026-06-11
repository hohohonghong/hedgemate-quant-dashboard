import { toBackendPortfolioRows } from './hedgemateApi';

export const REPORT_PORTFOLIO_STORAGE_KEY = 'hedgemate:lastReportPortfolioId';
const REPORT_ANALYSIS_RUNS_STORAGE_KEY = 'hedgemate:lastAnalysisRunsByPortfolio';

const safeStorage = () => {
  if (typeof window === 'undefined') return null;
  try {
    return window.localStorage || null;
  } catch {
    return null;
  }
};

const storageGet = (key) => {
  const storage = safeStorage();
  if (!storage) return '';
  try {
    return storage.getItem(key) || '';
  } catch {
    return '';
  }
};

const storageSet = (key, value) => {
  const storage = safeStorage();
  if (!storage) return;
  try {
    storage.setItem(key, String(value));
  } catch {
    // Local storage is best-effort; backend saved runs remain authoritative.
  }
};

const readStoredRuns = () => {
  const raw = storageGet(REPORT_ANALYSIS_RUNS_STORAGE_KEY);
  if (!raw) return {};
  try {
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {};
  } catch {
    return {};
  }
};

const writeStoredRuns = (runs) => {
  const entries = Object.entries(runs || {})
    .sort(([, a], [, b]) => Date.parse(b?.savedAt || b?.completedAt || 0) - Date.parse(a?.savedAt || a?.completedAt || 0))
    .slice(0, 25);
  storageSet(REPORT_ANALYSIS_RUNS_STORAGE_KEY, JSON.stringify(Object.fromEntries(entries)));
};

export const portfolioRunKey = (portfolio) => {
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

const portfolioIdValue = (portfolio) => {
  const id = portfolio?.id ?? portfolio?.portfolioId;
  return id ? String(id) : '';
};

const hasPortfolioId = (portfolios = [], id) => Boolean(
  id && portfolios.some((portfolio) => portfolioIdValue(portfolio) === String(id))
);

const portfolioTimestamp = (portfolio) => {
  const value = portfolio?.latestAnalysisAt || portfolio?.updatedAt || portfolio?.createdAt || '';
  const time = Date.parse(value);
  return Number.isFinite(time) ? time : 0;
};

export const latestAnalyzedPortfolioId = (portfolios = []) => {
  const [latest] = [...portfolios]
    .filter((portfolio) => portfolio?.latestAnalysisRunId || portfolio?.latestAnalysisAt || portfolio?.status === 'analyzed')
    .sort((a, b) => portfolioTimestamp(b) - portfolioTimestamp(a));
  return portfolioIdValue(latest);
};

export const getStoredReportPortfolioId = (portfolios = []) => {
  const storedId = storageGet(REPORT_PORTFOLIO_STORAGE_KEY);
  return hasPortfolioId(portfolios, storedId) ? storedId : '';
};

export const persistReportPortfolioId = (id) => {
  if (id) storageSet(REPORT_PORTFOLIO_STORAGE_KEY, id);
};

const runStorageKey = (portfolio) => portfolioIdValue(portfolio) || portfolioRunKey(portfolio);

const runTimestamp = (run) => {
  const time = Date.parse(run?.completedAt || run?.savedAt || 0);
  return Number.isFinite(time) ? time : 0;
};

const normalizeStoredRun = (portfolio, run, source) => {
  if (!portfolio || !run) return null;
  const currentPortfolioKey = portfolioRunKey(portfolio);
  const runPortfolioKey = run.portfolioKey || currentPortfolioKey;
  if (currentPortfolioKey && runPortfolioKey && currentPortfolioKey !== runPortfolioKey) return null;
  return {
    status: run.status || 'completed',
    runId: run.runId || '',
    portfolioInputFingerprintHash: run.portfolioInputFingerprintHash || '',
    portfolioKey: runPortfolioKey,
    portfolioId: portfolioIdValue(portfolio),
    completedAt: run.completedAt || '',
    savedAt: run.savedAt || run.completedAt || '',
    source,
  };
};

const runFromPortfolioRecord = (portfolio) => {
  const runId = portfolio?.latestAnalysisRunId || '';
  if (!runId) return null;
  return normalizeStoredRun(portfolio, {
    status: 'completed',
    runId,
    portfolioInputFingerprintHash: portfolio?.latestAnalysisFingerprintHash || '',
    portfolioKey: portfolio?.latestAnalysisPortfolioKey || portfolioRunKey(portfolio),
    completedAt: portfolio?.latestAnalysisAt || portfolio?.updatedAt || '',
    savedAt: portfolio?.latestAnalysisAt || portfolio?.updatedAt || '',
  }, 'portfolio-record');
};

export const getStoredAnalysisRunForPortfolio = (portfolio) => {
  if (!portfolio) return null;
  const stored = normalizeStoredRun(portfolio, readStoredRuns()[runStorageKey(portfolio)], 'local-storage');
  const fromRecord = runFromPortfolioRecord(portfolio);
  if (!stored) return fromRecord;
  if (!fromRecord) return stored;
  return runTimestamp(fromRecord) > runTimestamp(stored) ? fromRecord : stored;
};

export const persistAnalysisRunForPortfolio = (portfolio, run) => {
  const key = runStorageKey(portfolio);
  if (!key || !run) return;
  const currentPortfolioKey = portfolioRunKey(portfolio);
  const nextRun = normalizeStoredRun(portfolio, {
    ...run,
    portfolioKey: run.portfolioKey || currentPortfolioKey,
    completedAt: run.completedAt || '',
    savedAt: new Date().toISOString(),
  }, 'local-storage');
  if (!nextRun) return;
  writeStoredRuns({
    ...readStoredRuns(),
    [key]: nextRun,
  });
  persistReportPortfolioId(portfolioIdValue(portfolio));
};

export const resolveReportPortfolioSelection = (portfolios = [], search = '') => {
  const params = new URLSearchParams(search || '');
  const requestedPortfolioId = params.get('portfolio') || '';
  const requestedValid = hasPortfolioId(portfolios, requestedPortfolioId);
  const storedPortfolioId = getStoredReportPortfolioId(portfolios);
  const analyzedPortfolioId = latestAnalyzedPortfolioId(portfolios);
  const fallbackPortfolioId = portfolioIdValue(portfolios[0]);
  return {
    portfolioId: requestedValid
      ? String(requestedPortfolioId)
      : storedPortfolioId || analyzedPortfolioId || fallbackPortfolioId,
    requestedPortfolioId,
    requestedValid,
  };
};

export const reportPathForPortfolioId = (portfolioId) => (
  portfolioId ? `/report?portfolio=${encodeURIComponent(portfolioId)}` : '/report'
);
