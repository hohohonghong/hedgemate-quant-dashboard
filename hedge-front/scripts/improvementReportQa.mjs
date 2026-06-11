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
const autoRefreshEnd = source.indexOf('const ensureMarketDataCurrent');
if (marketDataOnlyStart !== -1) {
  fail('page-entry market-data refresh helper should be removed');
}

if (source.includes('refreshMarketDataBeforeDashboard')) {
  fail('page-entry refreshMarketDataBeforeDashboard flow should be removed');
}
if (source.includes('refreshMarketData(') || source.includes("mode: 'market_data_only'")) {
  fail('ImprovementReport must not create market refresh jobs');
}
if (autoRefreshEnd === -1) {
  fail('market-data freshness check block could not be isolated');
}

const freshnessCheckBlock = source.slice(autoRefreshEnd, source.indexOf('const handleRunAnalysis'));
if (!freshnessCheckBlock.includes('getHedgeMateStatus({')) {
  fail('analysis preflight must inspect status instead of refreshing market data');
}
if (!freshnessCheckBlock.includes("marketStatus !== 'FRESH'") || !freshnessCheckBlock.includes("intradayStatus !== 'FRESH'")) {
  fail('analysis preflight must require fresh market and intraday statuses');
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
requireIncludes('공통 시장데이터 갱신이 백그라운드에서 진행 중입니다. 완료 후 포트폴리오 분석을 다시 실행해 주세요.', 'background refresh warning');
requireIncludes('시장데이터가 최신 상태가 아닙니다. 스케줄러 갱신 또는 명시적 갱신 완료 후 분석을 실행해 주세요.', 'stale data preflight warning');

if (source.includes('>시장데이터 갱신<') || source.includes('시장데이터 갱신</Button>')) {
  fail('do not add a separate market-data refresh button');
}

console.log('ImprovementReport QA passed');
