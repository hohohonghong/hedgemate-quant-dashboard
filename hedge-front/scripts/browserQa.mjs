import { createRequire } from 'node:module';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

const require = createRequire(import.meta.url);

const resolvePlaywright = () => {
  const firstPathEntry = (process.env.PATH || '').split(path.delimiter)[0] || '';
  const injectedNodeModules = firstPathEntry.replace(/[\\/]\.bin$/, '');
  const candidates = [
    injectedNodeModules && path.join(injectedNodeModules, 'playwright'),
    injectedNodeModules && path.join(injectedNodeModules, 'playwright-core'),
    'playwright',
    'playwright-core',
  ].filter(Boolean);
  const errors = [];

  for (const candidate of candidates) {
    try {
      return require(candidate);
    } catch (error) {
      errors.push(`${candidate}: ${error.message}`);
    }
  }

  throw new Error(`Playwright runtime is missing. Run "npm ci" in hedge-front first.\n${errors.join('\n')}`);
};

const { chromium } = resolvePlaywright();

const frontendBase = (process.env.HEDGEMATE_FRONTEND_URL || 'http://127.0.0.1:5173').replace(/\/$/, '');
const browserChannel = process.env.HEDGEMATE_BROWSER_CHANNEL || 'chrome';
const rootDir = path.resolve(import.meta.dirname, '..');
const outputDir = path.resolve(rootDir, '..', 'output', 'qa', 'hedgemate-browser');
await mkdir(outputDir, { recursive: true });

const selectedPortfolio = {
  id: 'qa-active-bundle',
  name: 'QA Active Bundle',
  purpose: 'cache isolation check',
  createdAt: '2026-05-28',
  totalValue: 100000000,
  returnRate: 0,
  riskLevel: 'Moderate',
  status: 'analyzed',
  assets: [
    {
      ticker: '005930.KS',
      name: 'Samsung Electronics',
      qty: 0,
      cost: 38422800,
      currency: 'KRW',
      amountKrw: 38422800,
      weight: 38.4228,
    },
    {
      ticker: '035420.KS',
      name: 'NAVER',
      qty: 0,
      cost: 17777400,
      currency: 'KRW',
      amountKrw: 17777400,
      weight: 17.7774,
    },
    {
      ticker: '035720.KS',
      name: 'Kakao',
      qty: 0,
      cost: 14659800,
      currency: 'KRW',
      amountKrw: 14659800,
      weight: 14.6598,
    },
    {
      ticker: 'NVDA',
      name: 'NVIDIA',
      qty: 0,
      cost: 29140100,
      currency: 'KRW',
      amountKrw: 29140100,
      weight: 29.1401,
    },
  ],
};

const krAmountPortfolio = {
  id: 'qa-kr-amount-bundle',
  name: 'QA KR Amount Bundle',
  purpose: 'amount-only KR equity preview',
  createdAt: '2026-05-28',
  totalValue: 85000000,
  returnRate: 0,
  riskLevel: 'Balanced',
  status: 'analyzed',
  assets: [
    { ticker: '005930.KS', name: 'Samsung Electronics', qty: 0, cost: 38250000, currency: 'KRW', amountKrw: 38250000, weight: 45 },
    { ticker: '000660.KS', name: 'SK Hynix', qty: 0, cost: 25500000, currency: 'KRW', amountKrw: 25500000, weight: 30 },
    { ticker: '000270.KS', name: 'Kia', qty: 0, cost: 21250000, currency: 'KRW', amountKrw: 21250000, weight: 25 },
  ],
};

const usQuantityPortfolio = {
  id: 'qa-us-quantity-bundle',
  name: 'QA US Quantity Bundle',
  purpose: 'USD quantity live price preview',
  createdAt: '2026-05-28',
  totalValue: 70000000,
  returnRate: 0,
  riskLevel: 'Growth',
  status: 'analyzed',
  assets: [
    { ticker: 'AAPL', name: 'Apple', qty: 12, cost: 175, currency: 'USD', weight: 27 },
    { ticker: 'MSFT', name: 'Microsoft', qty: 6, cost: 420, currency: 'USD', weight: 31 },
    { ticker: 'TLT', name: '20Y Treasury ETF', qty: 35, cost: 88, currency: 'USD', weight: 23 },
    { ticker: 'GLD', name: 'Gold ETF', qty: 8, cost: 225, currency: 'USD', weight: 19 },
  ],
};

const mixedGlobalPortfolio = {
  id: 'qa-mixed-global-bundle',
  name: 'QA Mixed Global Bundle',
  purpose: 'KR amount plus US quantity mix',
  createdAt: '2026-05-28',
  totalValue: 120000000,
  returnRate: 0,
  riskLevel: 'Moderate',
  status: 'analyzed',
  assets: [
    { ticker: '005930.KS', name: 'Samsung Electronics', qty: 0, cost: 42000000, currency: 'KRW', amountKrw: 42000000, weight: 35 },
    { ticker: 'NVDA', name: 'NVIDIA', qty: 10, cost: 120, currency: 'USD', weight: 25 },
    { ticker: 'TLT', name: '20Y Treasury ETF', qty: 50, cost: 88, currency: 'USD', weight: 25 },
    { ticker: 'GLD', name: 'Gold ETF', qty: 9, cost: 225, currency: 'USD', weight: 15 },
  ],
};

const priceMovementPortfolio = {
  id: 'qa-price-movement',
  name: 'QA Price Movement',
  purpose: 'portfolio card signed return check',
  createdAt: '2026-05-28',
  totalValue: 3206000,
  returnRate: 0,
  riskLevel: 'Moderate',
  status: 'analyzed',
  assets: [
    {
      ticker: '005930.KS',
      name: 'Samsung Electronics',
      qty: 10,
      cost: 29300,
      currency: 'KRW',
      weight: 91,
    },
    {
      ticker: 'NVDA',
      name: 'NVIDIA',
      qty: 2,
      cost: 100,
      currency: 'USD',
      weight: 9,
    },
  ],
};

const concentratedMultiPortfolio = {
  id: 'qa-concentrated-multi',
  name: 'QA Concentrated Multi',
  purpose: 'single holding over 50 percent should block analysis',
  createdAt: '2026-05-28',
  totalValue: 100000000,
  returnRate: 0,
  riskLevel: 'High',
  status: 'new',
  assets: [
    { ticker: 'AAPL', name: 'Apple', qty: 0, cost: 65000000, currency: 'KRW', amountKrw: 65000000, weight: 65, weightPct: 65 },
    { ticker: 'MSFT', name: 'Microsoft', qty: 0, cost: 20000000, currency: 'KRW', amountKrw: 20000000, weight: 20, weightPct: 20 },
    { ticker: 'TLT', name: '20Y Treasury ETF', qty: 0, cost: 15000000, currency: 'KRW', amountKrw: 15000000, weight: 15, weightPct: 15 },
  ],
};

const singleAssetPortfolio = {
  id: 'qa-single-asset-100',
  name: 'QA Single Asset 100',
  purpose: 'single asset analysis should remain allowed',
  createdAt: '2026-05-28',
  totalValue: 100000000,
  returnRate: 0,
  riskLevel: 'High',
  status: 'new',
  assets: [
    { ticker: 'NVDA', name: 'NVIDIA', qty: 0, cost: 100000000, currency: 'KRW', amountKrw: 100000000, weight: 100, weightPct: 100 },
  ],
};

const qaPortfolios = [
  selectedPortfolio,
  krAmountPortfolio,
  usQuantityPortfolio,
  mixedGlobalPortfolio,
  priceMovementPortfolio,
  concentratedMultiPortfolio,
  singleAssetPortfolio,
];

const portfolioExpectations = {
  [priceMovementPortfolio.id]: { shouldBlockAnalysis: true },
  [concentratedMultiPortfolio.id]: { shouldBlockAnalysis: true },
  [singleAssetPortfolio.id]: { shouldAllowSingleAssetAnalysis: true },
};

const browser = await chromium.launch({
  channel: browserChannel,
  headless: process.env.HEADED !== '1',
  args: ['--disable-gpu', '--no-first-run', '--no-default-browser-check'],
}).catch((error) => {
  throw new Error(`Unable to launch Chromium channel "${browserChannel}". Install Chrome or set HEDGEMATE_BROWSER_CHANNEL=msedge.\n${error.message}`);
});

const context = await browser.newContext({
  viewport: { width: 1440, height: 1100 },
  locale: 'ko-KR',
});

await context.addInitScript((portfolios) => {
  localStorage.clear();
  localStorage.setItem('hedgemate_portfolios', JSON.stringify(portfolios));
  localStorage.setItem('hm_profile', JSON.stringify({
    name: 'Premium User',
    email: 'premium.user@hedgemate.io',
  }));
  localStorage.setItem('hm_theme', 'dark');
}, qaPortfolios);

const page = await context.newPage();
const consoleMessages = [];
const failedRequests = [];
const ignoredAbortedRequests = [];
const pageErrors = [];

page.on('console', (message) => {
  const type = message.type();
  if (type === 'error' || type === 'warning') {
    consoleMessages.push({ type, text: message.text() });
  }
});

page.on('requestfailed', (request) => {
  const failure = request.failure()?.errorText || '';
  const record = { url: request.url(), method: request.method(), failure };
  if (failure === 'net::ERR_ABORTED') {
    ignoredAbortedRequests.push(record);
    return;
  }
  failedRequests.push(record);
});

page.on('pageerror', (error) => {
  pageErrors.push(error.message);
});

const toUrl = (pathname) => `${frontendBase}${pathname}`;

const bodyText = async () => page.locator('body').innerText({ timeout: 10000 });

const tickerList = (portfolio) => portfolio.assets.map((asset) => asset.ticker).filter(Boolean);
const allQaTickers = [...new Set([...qaPortfolios.flatMap(tickerList), 'BTC-USD'])];

const foreignTickersFor = (portfolio) => {
  const selected = new Set(tickerList(portfolio));
  return allQaTickers.filter((ticker) => !selected.has(ticker));
};

const screenshot = async (name, options = {}) => {
  const file = path.join(outputDir, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  if (options.viewport) {
    const viewportFile = path.join(outputDir, `${name}-viewport.png`);
    await page.screenshot({ path: viewportFile, fullPage: false });
    return { fullPage: file, viewport: viewportFile };
  }
  return file;
};

const layoutSnapshot = async () => page.evaluate(() => {
  const root = document.documentElement;
  const visibleText = document.body.innerText;
  return {
    viewport: { width: window.innerWidth, height: window.innerHeight },
    scrollWidth: root.scrollWidth,
    clientWidth: root.clientWidth,
    horizontalOverflow: root.scrollWidth > root.clientWidth + 2,
    bodyTextLength: visibleText.length,
  };
});

const waitForPageText = async (markers, timeout = 60000) => {
  await page.waitForFunction((expectedMarkers) => {
    const text = document.body.innerText;
    return expectedMarkers.every((marker) => text.includes(marker));
  }, markers, { timeout });
};

const waitForReportStable = async (portfolio, timeout = 90000) => {
  const selectedTickers = tickerList(portfolio);
  const waitForStableState = async () => page.waitForFunction((markers) => {
    const text = document.body.innerText;
    const stableReportState = document.querySelector(
      '.analysis-required-card, .analysis-progress-card, .decision-banner',
    );
    const loadingState = document.querySelector('.backend-loading-card');
    return !loadingState && Boolean(stableReportState) && markers.every((marker) => text.includes(marker));
  }, [portfolio.name, ...selectedTickers], { timeout });

  await waitForStableState();
  await page.waitForTimeout(1500);
  await waitForStableState();
};

const evaluateReportIsolation = (text, portfolio) => {
  const selectedTickers = tickerList(portfolio);
  const foreignTickers = foreignTickersFor(portfolio);
  return {
    portfolioId: portfolio.id,
    portfolioName: portfolio.name,
    hasSelectedPortfolio: text.includes(portfolio.name),
    selectedTickersPresent: selectedTickers.filter((ticker) => text.includes(ticker)),
    missingSelectedTickers: selectedTickers.filter((ticker) => !text.includes(ticker)),
    foreignTickersPresent: foreignTickers.filter((ticker) => text.includes(ticker)),
    hasMatchedResultSections: text.includes('ACTION_READY')
      || text.includes('REVIEW_ONLY')
      || text.includes('Portfolio Vulnerability Top 3')
      || text.includes('Vulnerability Prescriptions'),
    hasAnalysisRequiredState: text.includes('ANALYSIS_RUNNING')
      || text.includes('analysis')
      || text.includes('portfolio')
      || text.includes(portfolio.name),
    hasConcentrationBlockState: /비중 조정 필요|리밸런싱 필요|단일 자산 비중이 50%를 넘어 분석/.test(text),
    hasSingleAssetAllowedState: /1종목 포트폴리오|단일자산 분석|단일 보유자산/.test(text),
    sample: text.slice(0, 1400),
  };
};

const evidence = {
  startedAt: new Date().toISOString(),
  frontendBase,
  browserChannel,
  seededPortfolios: qaPortfolios.map((portfolio) => ({
    id: portfolio.id,
    name: portfolio.name,
    tickers: tickerList(portfolio),
  })),
  reportCases: [],
  pages: {},
  interactions: [],
  screenshots: {},
};

const openReportForPortfolio = async (portfolio, index, pageKey) => {
  await page.goto(toUrl(`/report?portfolio=${encodeURIComponent(portfolio.id)}`), { waitUntil: 'domcontentloaded' });
  await waitForReportStable(portfolio);
  await page.waitForLoadState('networkidle', { timeout: 45000 }).catch(() => {});
  const reportText = await bodyText();
  const reportEvidence = {
    url: page.url(),
    ...evaluateReportIsolation(reportText, portfolio),
    layout: await layoutSnapshot(),
  };
  evidence.reportCases.push(reportEvidence);
  evidence.pages[pageKey] = reportEvidence;
  evidence.screenshots[pageKey] = await screenshot(`${String(index).padStart(2, '0')}-report-${portfolio.id}`, {
    viewport: index === 1,
  });
};

try {
  let reportIndex = 1;
  for (const portfolio of qaPortfolios) {
    await openReportForPortfolio(portfolio, reportIndex, `report:${portfolio.id}`);
    reportIndex += 1;
  }

  await page.goto(toUrl('/settings'), { waitUntil: 'domcontentloaded' });
  await waitForPageText(['Premium User', 'Dark', 'Light', 'System']);
  await page.locator('.settings-page .card-box').first().locator('button').first().click();
  await page.locator('.modal-content').waitFor({ state: 'visible', timeout: 10000 });
  await page.locator('.modal-content input[type="text"]').fill('QA User');
  await page.locator('.modal-content input[type="email"]').fill('qa.user@hedgemate.io');
  await page.locator('.modal-content button.btn-primary').click();
  await page.locator('.theme-btn').filter({ hasText: 'Light' }).click();
  await page.waitForFunction(() => document.documentElement.classList.contains('light-mode'), null, { timeout: 10000 });
  await page.locator('.theme-btn').filter({ hasText: 'Dark' }).click();
  await page.waitForFunction(() => !document.documentElement.classList.contains('light-mode'), null, { timeout: 10000 });
  const settingsText = await bodyText();
  evidence.pages.settings = {
    url: page.url(),
    profileSaved: settingsText.includes('QA User') && settingsText.includes('qa.user@hedgemate.io'),
    themeControlsWorked: true,
    layout: await layoutSnapshot(),
  };
  evidence.interactions.push('settings: profile modal save and theme Light/Dark toggles');
  evidence.screenshots.settings = await screenshot('06-settings-profile-theme', { viewport: true });

  await page.goto(toUrl('/portfolios'), { waitUntil: 'domcontentloaded' });
  await waitForPageText(qaPortfolios.map((portfolio) => portfolio.name));
  const cardEvidence = {};
  for (const portfolio of qaPortfolios) {
    const card = page.locator('.portfolio-card').filter({ hasText: portfolio.name }).first();
    await card.scrollIntoViewIfNeeded();
    await card.click();
    await card.locator('.detail-table').waitFor({ state: 'visible', timeout: 30000 });
    await page.waitForFunction(({ portfolioName, tickers }) => {
      const cards = [...document.querySelectorAll('.portfolio-card')];
      const matchedCard = cards.find((element) => element.innerText.includes(portfolioName));
      return Boolean(matchedCard && tickers.every((ticker) => matchedCard.innerText.includes(ticker)));
    }, { portfolioName: portfolio.name, tickers: tickerList(portfolio) }, { timeout: 30000 });
    const cardText = await card.innerText();
    cardEvidence[portfolio.id] = {
      hasName: cardText.includes(portfolio.name),
      expandedCardHasTickers: tickerList(portfolio).every((ticker) => cardText.includes(ticker)),
      hasSignedReturn: /[+-]\d+(\.\d+)?%/.test(cardText),
      hasAnalysisGuard: /리밸런싱|단일자산|50%/.test(cardText),
      sample: cardText.slice(0, 1000),
    };
  }

  const priceMovementCard = page.locator('.portfolio-card').filter({ hasText: priceMovementPortfolio.name }).first();
  await priceMovementCard.scrollIntoViewIfNeeded();
  if (await priceMovementCard.locator('.detail-table').count() === 0) {
    await priceMovementCard.click();
    await priceMovementCard.locator('.detail-table').waitFor({ state: 'visible', timeout: 30000 });
  }
  await priceMovementCard.locator('button.btn-delete').click();
  await page.locator('.delete-modal').waitFor({ state: 'visible', timeout: 10000 });
  await page.locator('.delete-modal button.btn-secondary').click();
  await page.locator('.delete-modal').waitFor({ state: 'hidden', timeout: 10000 });
  const portfoliosText = await bodyText();
  evidence.pages.portfolios = {
    url: page.url(),
    hasAllSeededPortfolios: qaPortfolios.every((portfolio) => portfoliosText.includes(portfolio.name)),
    deleteCancelKeptPortfolio: portfoliosText.includes(priceMovementPortfolio.name),
    cards: cardEvidence,
    layout: await layoutSnapshot(),
  };
  evidence.interactions.push('portfolios: expand every QA portfolio card and cancel delete modal');
  evidence.screenshots.portfolios = await screenshot('07-portfolios-expanded-cancel-delete', { viewport: true });

  const selectedCard = page.locator('.portfolio-card').filter({ hasText: selectedPortfolio.name }).first();
  await selectedCard.scrollIntoViewIfNeeded();
  await selectedCard.click();
  await selectedCard.locator('.detail-table').waitFor({ state: 'visible', timeout: 30000 });
  await selectedCard.locator('button.btn-primary').first().click();
  await page.waitForURL(`**/report?portfolio=${selectedPortfolio.id}`, { timeout: 10000 });
  await waitForReportStable(selectedPortfolio);
  await page.waitForLoadState('networkidle', { timeout: 45000 }).catch(() => {});
  const finalReportText = await bodyText();
  evidence.pages.finalReport = {
    url: page.url(),
    ...evaluateReportIsolation(finalReportText, selectedPortfolio),
    layout: await layoutSnapshot(),
  };
  evidence.reportCases.push(evidence.pages.finalReport);
  evidence.interactions.push('portfolios: open selected portfolio report from card');
  evidence.screenshots.finalReport = await screenshot('08-report-from-portfolio-card', { viewport: true });

  await page.goto(toUrl('/'), { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => document.body.innerText.length > 100, null, { timeout: 10000 });
  evidence.pages.home = {
    url: page.url(),
    layout: await layoutSnapshot(),
  };
} finally {
  evidence.consoleMessages = consoleMessages;
  evidence.failedRequests = failedRequests;
  evidence.ignoredAbortedRequests = ignoredAbortedRequests;
  evidence.pageErrors = pageErrors;
  evidence.completedAt = new Date().toISOString();
  await writeFile(path.join(outputDir, 'browser-qa-result.json'), JSON.stringify(evidence, null, 2), 'utf8');
  await browser.close();
}

const criticalFailures = [];
const requireCondition = (condition, message) => {
  if (!condition) criticalFailures.push(message);
};

for (const report of evidence.reportCases) {
  requireCondition(report?.hasSelectedPortfolio, `${report?.portfolioName || 'report'} did not show the selected portfolio`);
  requireCondition(report?.missingSelectedTickers?.length === 0, `${report?.portfolioName || 'report'} missed selected tickers: ${(report?.missingSelectedTickers || []).join(', ')}`);
  requireCondition(report?.foreignTickersPresent?.length === 0, `${report?.portfolioName || 'report'} leaked foreign stale tickers: ${(report?.foreignTickersPresent || []).join(', ')}`);
  const expectation = portfolioExpectations[report?.portfolioId];
  if (expectation?.shouldBlockAnalysis) {
    requireCondition(report?.hasConcentrationBlockState, `${report?.portfolioName || 'report'} did not show the 50% concentration block state`);
  }
  if (expectation?.shouldAllowSingleAssetAnalysis) {
    requireCondition(!report?.hasConcentrationBlockState, `${report?.portfolioName || 'report'} incorrectly showed a blocking concentration state`);
    requireCondition(report?.hasSingleAssetAllowedState, `${report?.portfolioName || 'report'} did not show the single-asset allowed state`);
  }
}

requireCondition(evidence.pages.settings?.profileSaved, 'settings profile save interaction failed');
requireCondition(evidence.pages.settings?.themeControlsWorked, 'settings theme interaction failed');
requireCondition(evidence.pages.portfolios?.hasAllSeededPortfolios, 'portfolio page did not show every seeded QA portfolio');
requireCondition(evidence.pages.portfolios?.deleteCancelKeptPortfolio, 'portfolio delete cancel interaction failed');

for (const portfolio of qaPortfolios) {
  const card = evidence.pages.portfolios?.cards?.[portfolio.id];
  requireCondition(card?.expandedCardHasTickers, `${portfolio.name} expanded card did not show seeded tickers`);
  const expectation = portfolioExpectations[portfolio.id];
  if (expectation?.shouldBlockAnalysis || expectation?.shouldAllowSingleAssetAnalysis) {
    requireCondition(card?.hasAnalysisGuard, `${portfolio.name} card did not show concentration guidance`);
  }
}
requireCondition(
  evidence.pages.portfolios?.cards?.[priceMovementPortfolio.id]?.hasSignedReturn,
  'price movement portfolio card did not show signed return text',
);

for (const [pageName, pageEvidence] of Object.entries(evidence.pages)) {
  if (pageEvidence?.layout?.horizontalOverflow) {
    criticalFailures.push(`${pageName} has horizontal overflow`);
  }
  if (pageEvidence?.layout && pageEvidence.layout.bodyTextLength < 100) {
    criticalFailures.push(`${pageName} rendered with suspiciously little text`);
  }
}

if (pageErrors.length > 0) {
  criticalFailures.push(`page errors: ${pageErrors.join(' | ')}`);
}

console.log(JSON.stringify({
  ok: criticalFailures.length === 0,
  criticalFailures,
  outputDir,
  portfolioCount: qaPortfolios.length,
  reportCaseCount: evidence.reportCases.length,
  screenshots: evidence.screenshots,
  failedRequestCount: failedRequests.length,
  ignoredAbortedRequestCount: ignoredAbortedRequests.length,
  pageErrorCount: pageErrors.length,
}, null, 2));

if (criticalFailures.length > 0) {
  process.exit(1);
}
