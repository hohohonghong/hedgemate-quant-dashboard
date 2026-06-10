import { readFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const source = await readFile(join(root, 'src/pages/ImprovementReport.jsx'), 'utf8');

const fail = (message) => {
  throw new Error(`[ImprovementReport QA] ${message}`);
};

const requireIncludes = (needle, description) => {
  if (!source.includes(needle)) {
    fail(`${description} not found`);
  }
};

const marketDataOnlyStart = source.indexOf('const runMarketDataOnlyRefresh');
const autoRefreshStart = source.indexOf('const refreshMarketDataBeforeDashboard');
const autoRefreshEnd = source.indexOf('const ensureMarketDataCurrent');
if (
  marketDataOnlyStart === -1
  || autoRefreshStart === -1
  || autoRefreshEnd === -1
  || !(marketDataOnlyStart < autoRefreshStart && autoRefreshStart < autoRefreshEnd)
) {
  fail('market-data refresh blocks could not be isolated');
}

const marketDataOnlyBlock = source.slice(marketDataOnlyStart, autoRefreshStart);
const autoRefreshBlock = source.slice(autoRefreshStart, autoRefreshEnd);
if (!marketDataOnlyBlock.includes("mode: 'market_data_only'")) {
  fail('page-entry refresh must stay market_data_only');
}
if (!autoRefreshBlock.includes('runMarketDataOnlyRefresh(')) {
  fail('page-entry refresh must call the market-data-only helper');
}
if (autoRefreshBlock.includes('runPortfolioAnalysis(')) {
  fail('page-entry refresh must not start portfolio analysis');
}

const analysisCalls = [...source.matchAll(/runPortfolioAnalysis\(/g)].map((match) => match.index);
if (analysisCalls.length !== 1) {
  fail(`expected exactly one explicit portfolio analysis call, found ${analysisCalls.length}`);
}
const handleRunAnalysisStart = source.indexOf('const handleRunAnalysis');
if (analysisCalls[0] < handleRunAnalysisStart) {
  fail('portfolio analysis call must live inside the explicit CTA handler');
}

requireIncludes('const staleAnalysisBundle = Boolean', 'stale analysis bundle state');
requireIncludes('const analysisCtaLabel = runState.running', 'dynamic analysis CTA label');
requireIncludes('최신 데이터로 재분석', 'stale analysis CTA text');
requireIncludes('포트폴리오 분석 실행', 'default analysis CTA text');
requireIncludes('재분석 중', 'running analysis CTA text');
requireIncludes('최신 시장데이터는 반영됐지만 현재 리포트는 이전 분석 결과입니다. 최신 데이터로 재분석하세요.', 'stale analysis warning');

if (source.includes('시장데이터 갱신')) {
  fail('do not add a separate market-data refresh button');
}

console.log('ImprovementReport QA passed');
