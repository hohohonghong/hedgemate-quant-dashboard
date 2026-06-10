import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

const apiBase = (process.env.HEDGEMATE_API_BASE || 'http://127.0.0.1:8766/api').replace(/\/$/, '');
const rootDir = path.resolve(import.meta.dirname, '..');
const outputDir = path.resolve(rootDir, '..', 'output', 'qa', 'portfolio-matrix');
await mkdir(outputDir, { recursive: true });

const previewPortfolio = async (portfolioRows) => {
  const response = await fetch(`${apiBase}/portfolio/preview`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      portfolioRows,
      useLivePrices: true,
    }),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || `${response.status} ${response.statusText}`);
  }
  return payload;
};

const cases = [
  {
    id: 'balanced_50_50',
    expectedCanRunAnalysis: true,
    rows: [
      { asset: 'AAPL', amountKrw: 5000000 },
      { asset: 'MSFT', amountKrw: 5000000 },
    ],
  },
  {
    id: 'multi_asset_65pct_blocked',
    expectedCanRunAnalysis: false,
    expectedErrorIncludes: ['AAPL', '50.0%'],
    rows: [
      { asset: 'AAPL', amountKrw: 6500000 },
      { asset: 'MSFT', amountKrw: 2000000 },
      { asset: 'TLT', amountKrw: 1500000 },
    ],
  },
  {
    id: 'single_asset_100pct_allowed',
    expectedCanRunAnalysis: true,
    expectedWarningIncludes: ['50%'],
    rows: [
      { asset: 'NVDA', amountKrw: 10000000 },
    ],
  },
  {
    id: 'mixed_kr_us_amounts_allowed',
    expectedCanRunAnalysis: true,
    rows: [
      { asset: '005930.KS', amountKrw: 5000000 },
      { asset: 'GLD', amountKrw: 2500000 },
      { asset: 'TLT', amountKrw: 2500000 },
    ],
  },
];

const results = [];
const failures = [];

for (const qaCase of cases) {
  const preview = await previewPortfolio(qaCase.rows);
  const weights = Object.fromEntries((preview.analysisRows || []).map((row) => [
    row.ticker,
    Number(row.weight_pct),
  ]));
  const errorsText = (preview.errors || []).join(' | ');
  const warningsText = (preview.rows || []).flatMap((row) => row.warnings || []).join(' | ');
  const record = {
    id: qaCase.id,
    ok: preview.ok,
    canRunAnalysis: preview.canRunAnalysis,
    weights,
    errors: preview.errors || [],
    warnings: (preview.rows || []).map((row) => ({
      ticker: row.resolvedTicker,
      warnings: row.warnings || [],
    })),
  };
  results.push(record);

  if (preview.canRunAnalysis !== qaCase.expectedCanRunAnalysis) {
    failures.push(`${qaCase.id}: expected canRunAnalysis=${qaCase.expectedCanRunAnalysis}, got ${preview.canRunAnalysis}`);
  }
  for (const marker of qaCase.expectedErrorIncludes || []) {
    if (!errorsText.includes(marker)) failures.push(`${qaCase.id}: expected error marker "${marker}"`);
  }
  for (const marker of qaCase.expectedWarningIncludes || []) {
    if (!warningsText.includes(marker)) failures.push(`${qaCase.id}: expected warning marker "${marker}"`);
  }
}

const evidence = {
  ok: failures.length === 0,
  apiBase,
  results,
  failures,
  completedAt: new Date().toISOString(),
};

await writeFile(path.join(outputDir, 'portfolio-matrix-result.json'), JSON.stringify(evidence, null, 2), 'utf8');
console.log(JSON.stringify(evidence, null, 2));

if (failures.length > 0) {
  process.exit(1);
}
