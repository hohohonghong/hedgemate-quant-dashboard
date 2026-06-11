import { readFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const source = await readFile(join(root, 'src/pages/MarketStateDashboard.jsx'), 'utf8');

const fail = (message) => {
  throw new Error(`[MarketState QA] ${message}`);
};

const requireIncludes = (needle, description) => {
  if (!source.includes(needle)) fail(`${description} not found`);
};

if (source.includes('refreshMarketData') || source.includes('refreshIntradayNews') || source.includes('pollRunStatus')) {
  fail('market-state page must not auto-create market/news refresh jobs');
}

if (source.includes('검증된 실시간 뉴스가 없어 Top5 뉴스를 표시하지 않습니다')) {
  fail('fallback news absence message must not be rendered');
}

if (source.includes('Top5 뉴스 오버레이가 아직 없습니다')) {
  fail('empty Top5 news placeholder must not be rendered');
}

requireIncludes('if (!rows.length || status?.fallbackUsed) return null;', 'quiet news fallback behavior');
requireIncludes('const primary = hasDailyPrimary ?', 'daily market state primary selection');
requireIncludes('<span className="state-chip neutral">시장국면</span>', 'market-state label chip');
requireIncludes('장중 참고 신호', 'intraday reference label');
requireIncludes('정식 시장국면을 대체하지 않는 보조 신호입니다.', 'intraday helper copy');
requireIncludes('intraday-signal-row', 'compact intraday row UI');

console.log('MarketState QA passed');
