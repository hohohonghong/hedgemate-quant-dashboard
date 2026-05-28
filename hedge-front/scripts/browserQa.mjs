import { createRequire } from 'node:module';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

const require = createRequire(import.meta.url);

const resolvePlaywright = () => {
  const firstPathEntry = (process.env.PATH || '').split(path.delimiter)[0] || '';
  const injectedNodeModules = firstPathEntry.replace(/[\\/]\.bin$/, '');
  try {
    return require(path.join(injectedNodeModules, 'playwright'));
  } catch {
    return require('playwright');
  }
};

const { chromium } = resolvePlaywright();

const rootDir = path.resolve(import.meta.dirname, '..');
const outputDir = path.resolve(rootDir, '..', 'output', 'qa', 'hedgemate-browser');
await mkdir(outputDir, { recursive: true });

const seededPortfolio = {
  id: 'qa-active-bundle',
  name: 'QA Active Bundle',
  purpose: '백엔드 active bundle 검증',
  createdAt: '2026-05-27',
  totalValue: 100000000,
  returnRate: 0,
  riskLevel: 'Moderate',
  status: 'analyzed',
  assets: [
    {
      ticker: '005930.KS',
      name: '삼성전자',
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
      name: '카카오',
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

const priceMovementPortfolio = {
  id: 'qa-price-movement',
  name: 'QA Price Movement',
  purpose: '현재가 수익률 검증',
  createdAt: '2026-05-27',
  totalValue: 3206000,
  returnRate: 0,
  riskLevel: 'Moderate',
  status: 'analyzed',
  assets: [
    {
      ticker: '005930.KS',
      name: '삼성전자',
      qty: 10,
      cost: 293000,
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

const browser = await chromium.launch({
  channel: 'chrome',
  headless: true,
  args: ['--disable-gpu', '--no-first-run', '--no-default-browser-check'],
});

const context = await browser.newContext({
  viewport: { width: 1440, height: 1100 },
  locale: 'ko-KR',
});

await context.addInitScript((portfolios) => {
  localStorage.setItem('hedgemate_portfolios', JSON.stringify(portfolios));
  localStorage.setItem('hm_profile', JSON.stringify({
    name: 'Premium User',
    email: 'premium.user@hedgemate.io',
  }));
  localStorage.setItem('hm_theme', 'dark');
}, [seededPortfolio, priceMovementPortfolio]);

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
  if (failure === 'net::ERR_ABORTED') {
    ignoredAbortedRequests.push({
      url: request.url(),
      method: request.method(),
      failure,
    });
    return;
  }
  failedRequests.push({
    url: request.url(),
    method: request.method(),
    failure,
  });
});
page.on('pageerror', (error) => {
  pageErrors.push(error.message);
});

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
  const keyTexts = [
    '저장된 분석 결과 표시 중',
    '환경 설정',
    '내 포트폴리오',
    '분석 리포트 보기',
  ];
  const body = document.body;
  const root = document.documentElement;
  const visibleText = body.innerText;
  const keyRects = keyTexts
    .filter((text) => visibleText.includes(text))
    .map((text) => {
      const walker = document.createTreeWalker(body, NodeFilter.SHOW_TEXT);
      let node;
      while ((node = walker.nextNode())) {
        if (!node.nodeValue.includes(text)) continue;
        const range = document.createRange();
        range.selectNodeContents(node);
        const rect = range.getBoundingClientRect();
        return {
          text,
          width: Math.round(rect.width),
          height: Math.round(rect.height),
          top: Math.round(rect.top),
          left: Math.round(rect.left),
        };
      }
      return null;
    })
    .filter(Boolean);
  return {
    viewport: { width: window.innerWidth, height: window.innerHeight },
    scrollWidth: root.scrollWidth,
    clientWidth: root.clientWidth,
    horizontalOverflow: root.scrollWidth > root.clientWidth + 2,
    bodyTextLength: visibleText.length,
    keyRects,
  };
});

const bodyText = async () => page.locator('body').innerText({ timeout: 10000 });

const waitForReportDecision = async () => {
  await page.waitForFunction(() => {
    const text = document.body.innerText;
    return text.includes('저장된 분석 결과 표시 중')
      || text.includes('검증된 액션 플랜이 있습니다')
      || text.includes('분석 완료 · 검토 후보 표시 중')
      || text.includes('이 포트폴리오에 대한 최신 분석 결과가 없습니다')
      || text.includes('등록된 포트폴리오가 없습니다');
  }, null, { timeout: 45000 });
};

const evidence = {
  startedAt: new Date().toISOString(),
  seededPortfolio: {
    id: seededPortfolio.id,
    tickers: seededPortfolio.assets.map((asset) => asset.ticker),
    weights: Object.fromEntries(seededPortfolio.assets.map((asset) => [asset.ticker, asset.weight])),
  },
  priceMovementPortfolio: {
    id: priceMovementPortfolio.id,
    tickers: priceMovementPortfolio.assets.map((asset) => asset.ticker),
    costBasis: priceMovementPortfolio.totalValue,
  },
  pages: {},
  interactions: [],
  screenshots: {},
};

try {
  await page.goto('http://127.0.0.1:5173/report?portfolio=qa-active-bundle', { waitUntil: 'domcontentloaded' });
  await waitForReportDecision();
  await page.waitForLoadState('networkidle', { timeout: 45000 }).catch(() => {});
  const reportText = await bodyText();
  evidence.pages.initialReport = {
    url: page.url(),
    hasStoredResultsBanner: reportText.includes('저장된 분석 결과 표시 중'),
    hasNoLatestBlocker: reportText.includes('이 포트폴리오에 대한 최신 분석 결과가 없습니다'),
    hasActionPlan: reportText.includes('선택된 검토 액션') || reportText.includes('평가 후보'),
    hasCandidateDetails: reportText.includes('전체 후보와 근거 보기'),
    productStatusVisible: reportText.includes('STALE'),
    textSample: reportText.slice(0, 1200),
  };
  evidence.pages.initialReport.layout = await layoutSnapshot();
  evidence.screenshots.initialReport = await screenshot('01-report-stored-results', { viewport: true });

  await page.getByRole('button', { name: /Settings/i }).click();
  await page.waitForURL('**/settings', { timeout: 10000 });
  await page.getByRole('button', { name: '프로필 수정' }).click();
  const modal = page.locator('.modal-content');
  await modal.waitFor({ state: 'visible', timeout: 10000 });
  await modal.locator('input[type="text"]').fill('QA User');
  await modal.locator('input[type="email"]').fill('qa.user@hedgemate.io');
  await page.getByRole('button', { name: '저장하기' }).click();
  await page.getByText('Light').click();
  await page.getByText('Dark').click();
  const settingsText = await bodyText();
  evidence.pages.settings = {
    url: page.url(),
    profileSaved: settingsText.includes('QA User') && settingsText.includes('qa.user@hedgemate.io'),
    hasSettingsHeader: settingsText.includes('환경 설정'),
    hasThemeControls: settingsText.includes('Dark') && settingsText.includes('Light') && settingsText.includes('System'),
  };
  evidence.interactions.push('settings: profile modal save, theme Light/Dark buttons');
  evidence.pages.settings.layout = await layoutSnapshot();
  evidence.screenshots.settings = await screenshot('02-settings-after-profile-save', { viewport: true });

  await page.getByRole('link', { name: /내 포트폴리오/ }).first().click();
  await page.waitForURL('**/portfolios', { timeout: 10000 });
  await page.waitForFunction(() => document.body.innerText.includes('현재가 반영됨'), null, { timeout: 45000 });
  const priceMovementCard = page.locator('.portfolio-card').filter({ hasText: 'QA Price Movement' });
  await priceMovementCard.click();
  await page.getByRole('button', { name: /삭제/ }).click();
  await page.getByRole('button', { name: '취소' }).click();
  const portfoliosText = await bodyText();
  const priceMovementText = await priceMovementCard.innerText();
  evidence.pages.portfolios = {
    url: page.url(),
    hasSeededPortfolio: portfoliosText.includes('QA Active Bundle'),
    hasPriceMovementPortfolio: portfoliosText.includes('QA Price Movement'),
    deleteCancelKeptPortfolio: portfoliosText.includes('QA Price Movement') && !portfoliosText.includes('정말로 이 포트폴리오를 삭제하시겠습니까?'),
    hasReportButton: portfoliosText.includes('분석 리포트 보기'),
    hasEditButton: portfoliosText.includes('수정'),
    hasLivePriceRefresh: portfoliosText.includes('현재가 반영됨'),
    priceMovementHasNonZeroReturn: /[+-](?!0\.0%)\d+(\.\d+)?%/.test(priceMovementText),
    priceMovementHasCurrentPriceColumns: priceMovementText.includes('현재가') && priceMovementText.includes('손익'),
    priceMovementTextSample: priceMovementText.slice(0, 900),
  };
  evidence.interactions.push('portfolios: expand card, open delete modal, cancel delete');
  evidence.pages.portfolios.layout = await layoutSnapshot();
  evidence.screenshots.portfolios = await screenshot('03-portfolios-expanded', { viewport: true });

  await page.locator('.portfolio-card').filter({ hasText: 'QA Active Bundle' }).click();
  await page.getByRole('button', { name: /분석 리포트 보기/ }).click();
  await page.waitForURL('**/report?portfolio=qa-active-bundle', { timeout: 10000 });
  await waitForReportDecision();
  await page.getByRole('button', { name: 'MDD' }).click();
  await page.locator('summary').filter({ hasText: '전체 후보와 근거 보기' }).click();
  const finalReportText = await bodyText();
  evidence.pages.finalReport = {
    url: page.url(),
    hasStoredResultsBanner: finalReportText.includes('저장된 분석 결과 표시 중'),
    hasNoLatestBlocker: finalReportText.includes('이 포트폴리오에 대한 최신 분석 결과가 없습니다'),
    hasReviewCounts: finalReportText.includes('REVIEW'),
    hasVulnerabilitySection: finalReportText.includes('포트폴리오 취약성 요약') || finalReportText.includes('포트폴리오 취약점 요약'),
    hasCandidateDetails: finalReportText.includes('전체 후보와 근거 보기'),
    hasMetricSelection: finalReportText.includes('MDD'),
  };
  evidence.interactions.push('report: navigate from portfolio card, select MDD tab, expand candidate details');
  evidence.pages.finalReport.layout = await layoutSnapshot();
  evidence.screenshots.finalReport = await screenshot('04-report-from-card-candidates-open', { viewport: true });

  await page.getByRole('button', { name: '알림 설정 열기' }).click();
  await page.waitForURL('**/settings', { timeout: 10000 });
  await page.getByRole('button', { name: '프로필 설정 열기' }).click();
  await page.waitForURL('**/settings', { timeout: 10000 });
  await page.getByRole('button', { name: /Logout/i }).click();
  await page.waitForURL('http://127.0.0.1:5173/', { timeout: 10000 });
  evidence.pages.topAndLogoutButtons = {
    topIconsRouteToSettings: true,
    logoutRoutesHome: page.url() === 'http://127.0.0.1:5173/',
  };
  evidence.interactions.push('topnav: notification/profile icons route to settings; sidebar logout routes home');
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
if (!evidence.pages.initialReport?.hasStoredResultsBanner) {
  criticalFailures.push('initial /report did not show stored-results banner');
}
if (evidence.pages.initialReport?.hasNoLatestBlocker) {
  criticalFailures.push('initial /report still showed no-latest-analysis blocker');
}
if (!evidence.pages.settings?.profileSaved) {
  criticalFailures.push('/settings profile save interaction failed');
}
if (!evidence.pages.portfolios?.deleteCancelKeptPortfolio) {
  criticalFailures.push('/portfolios delete cancel interaction failed');
}
if (!evidence.pages.portfolios?.hasLivePriceRefresh || !evidence.pages.portfolios?.priceMovementHasNonZeroReturn) {
  criticalFailures.push('/portfolios did not show live-price based non-zero return');
}
if (!evidence.pages.portfolios?.priceMovementHasCurrentPriceColumns) {
  criticalFailures.push('/portfolios expanded detail missing current price/profit columns');
}
if (!evidence.pages.finalReport?.hasStoredResultsBanner || evidence.pages.finalReport?.hasNoLatestBlocker) {
  criticalFailures.push('report opened from portfolio card did not display stored results correctly');
}
if (!evidence.pages.finalReport?.hasVulnerabilitySection) {
  criticalFailures.push('final /report missing vulnerability section');
}
if (!evidence.pages.topAndLogoutButtons?.topIconsRouteToSettings || !evidence.pages.topAndLogoutButtons?.logoutRoutesHome) {
  criticalFailures.push('top navigation or logout routing failed');
}
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
  screenshots: evidence.screenshots,
  pages: evidence.pages,
  failedRequestCount: failedRequests.length,
  ignoredAbortedRequestCount: ignoredAbortedRequests.length,
  pageErrorCount: pageErrors.length,
}, null, 2));

if (criticalFailures.length > 0) {
  process.exit(1);
}
