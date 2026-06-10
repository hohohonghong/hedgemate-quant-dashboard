import { pathToFileURL } from 'node:url';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import * as esbuild from 'esbuild';

const tempDir = await mkdtemp(path.join(os.tmpdir(), 'hedgemate-scenario-guide-'));
const bundlePath = path.join(tempDir, 'marketStateAssetGuide.bundle.mjs');

const fail = (message, detail = {}) => {
  console.error(JSON.stringify({ ok: false, message, detail }, null, 2));
  process.exit(1);
};

try {
  const bundled = await esbuild.build({
    entryPoints: [path.resolve('src/services/marketStateAssetGuide.js')],
    bundle: true,
    platform: 'node',
    format: 'esm',
    write: false,
    logLevel: 'silent',
  });
  await writeFile(bundlePath, bundled.outputFiles[0].text, 'utf8');
  const {
    MARKET_STATE_ASSET_GUIDE_EMPTY_MESSAGE,
    buildMarketStateAssetGuide,
  } = await import(pathToFileURL(bundlePath).href);

  const dashboardA = {
    topActiveScenarios: [
      { scenario_code: 'stress_usd', scenario_name_ko: '달러 강세', final_score: 80 },
      { scenario_code: 'rates', scenario_name_ko: '장기금리 부담', final_score: 60 },
      { scenario_code: 'china', scenario_name_ko: '중국 둔화', final_score: 40 },
    ],
    scenarioVectorLeaders: [
      { scenario_code: 'unused', scenario_name_ko: '미사용', score: 99 },
    ],
    topMarketRows: [],
  };
  const rows = [
    {
      ticker: 'AAA',
      asset_name: 'Alpha Asset',
      asset_class: 'equity',
      scenario_code: 'stress_usd',
      scenario_beta: '-1',
      confidence: '80',
      source_quality: 'market',
      recommended_role: 'offset',
    },
    {
      ticker: 'AAA',
      asset_name: 'Alpha Asset',
      asset_class: 'equity',
      scenario_code: 'rates',
      scenario_beta: '0.5',
      confidence: '80',
      source_quality: 'manual',
      notes: 'partly vulnerable',
    },
    {
      ticker: 'BBB',
      asset_name: 'Beta Asset',
      asset_class: 'bond',
      scenario_code: 'stress_usd',
      scenario_beta: '1.5',
      confidence: '90',
      source_quality: 'direct_beta',
    },
    {
      ticker: 'CCC',
      asset_name: 'Gamma Asset',
      asset_class: 'commodity',
      scenario_code: 'china',
      scenario_beta: '-1.2',
      confidence: '70',
      source_quality: 'seed',
    },
    {
      ticker: 'DDD',
      asset_name: 'Delta Asset',
      asset_class: 'cash',
      scenario_code: 'not_active',
      scenario_beta: '-10',
      confidence: '100',
      source_quality: 'market',
    },
  ];

  const guideA = buildMarketStateAssetGuide(dashboardA, { rows });
  if (guideA.emptyMessage) {
    fail('guide with matching rows should not show empty state', guideA);
  }
  if (guideA.interestAssets[0]?.ticker !== 'AAA') {
    fail('same ticker should aggregate and classify by total_signal', guideA.interestAssets);
  }
  if (guideA.reduceAssets[0]?.ticker !== 'BBB') {
    fail('positive total_signal should classify into reduce assets', guideA.reduceAssets);
  }
  if (guideA.interestAssets.some((asset) => asset.ticker === 'BBB') || guideA.reduceAssets.some((asset) => asset.ticker === 'AAA')) {
    fail('one ticker must not appear in both columns', guideA);
  }
  if (guideA.interestAssets.some((asset) => asset.ticker === 'DDD') || guideA.reduceAssets.some((asset) => asset.ticker === 'DDD')) {
    fail('displayed assets must come from active scenario sensitivity rows only', guideA);
  }
  if (!guideA.interestAssets[0].matchedScenarios.includes('달러 강세') || !guideA.interestAssets[0].matchedScenarios.includes('장기금리 부담')) {
    fail('aggregated ticker should keep all matched scenario labels', guideA.interestAssets[0]);
  }

  const dashboardB = {
    topActiveScenarios: [
      { scenario_code: 'not_active', scenario_name_ko: '다른 국면', final_score: 100 },
    ],
  };
  const guideB = buildMarketStateAssetGuide(dashboardB, { rows });
  if (guideB.interestAssets[0]?.ticker !== 'DDD') {
    fail('changing active scenarios should change selected assets', guideB);
  }

  const emptyGuide = buildMarketStateAssetGuide(dashboardA, { rows: [] });
  if (emptyGuide.emptyMessage !== MARKET_STATE_ASSET_GUIDE_EMPTY_MESSAGE) {
    fail('empty sensitivities should return the required empty message', emptyGuide);
  }
  if (emptyGuide.interestAssets.length || emptyGuide.reduceAssets.length) {
    fail('empty sensitivities should not produce fallback cards', emptyGuide);
  }

  console.log(JSON.stringify({
    ok: true,
    emptyMessage: emptyGuide.emptyMessage,
    dashboardA: {
      interest: guideA.interestAssets.map((asset) => asset.ticker),
      reduce: guideA.reduceAssets.map((asset) => asset.ticker),
      matchedRowCount: guideA.matchedRowCount,
    },
    dashboardB: {
      interest: guideB.interestAssets.map((asset) => asset.ticker),
      reduce: guideB.reduceAssets.map((asset) => asset.ticker),
    },
  }, null, 2));
} finally {
  await rm(tempDir, { recursive: true, force: true });
}
