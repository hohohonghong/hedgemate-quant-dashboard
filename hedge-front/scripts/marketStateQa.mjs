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
if (source.includes('신뢰도')) {
  fail('market-state page should not render confidence copy');
}
if (source.includes('한국장 방어적 로테이션')) {
  fail('defensive nowcast label must use the previous user-facing wording');
}

requireIncludes('if (!rows.length) return null;', 'empty news fallback behavior');
requireIncludes("const statusText = '뉴스 참고 자료';", 'minimal news status text');
requireIncludes('formatKstDateOnly(item.date', 'date-only news rendering');
requireIncludes('출처: {source}', 'source link rendering');
requireIncludes('시장 뉴스 참고자료', 'neutral news section title');
requireIncludes('한국장 방어주 상대강세', 'relative defensive strength label');
requireIncludes("DEFENSIVE_ROTATION: '방어주 상대강세'", 'defensive state chip label');
requireIncludes('nowcast-driver-list', 'nowcast driver evidence chips');
requireIncludes('const primary = hasDailyPrimary ?', 'daily market state primary selection');
requireIncludes('<span className="state-chip neutral">시장국면</span>', 'market-state label chip');
requireIncludes('장중 참고 신호', 'intraday reference label');
requireIncludes('정식 시장국면을 대체하지 않는 장중 참고 신호입니다.', 'summary intraday helper copy');
requireIncludes('단기 보조 신호', 'restored short-term tab label');
requireIncludes('<ScenarioCard key={`${row.nowcast_code || index}-nowcast`} row={row} compact />', 'restored short-term scenario card UI');

if (source.includes('intraday-signal-row')) {
  fail('short-term intraday tab should use the previous scenario-card UI');
}

console.log('MarketState QA passed');
