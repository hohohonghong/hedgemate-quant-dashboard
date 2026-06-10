import { pathToFileURL } from 'node:url';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import * as esbuild from 'esbuild';

const tempDir = await mkdtemp(path.join(os.tmpdir(), 'hedgemate-viewmodel-'));
const bundlePath = path.join(tempDir, 'hedgemateViewModel.bundle.mjs');

const fail = (message, detail = {}) => {
  console.error(JSON.stringify({ ok: false, message, detail }, null, 2));
  process.exit(1);
};

try {
  const bundled = await esbuild.build({
    entryPoints: [path.resolve('src/services/hedgemateViewModel.js')],
    bundle: true,
    platform: 'node',
    format: 'esm',
    write: false,
    logLevel: 'silent',
  });
  await writeFile(bundlePath, bundled.outputFiles[0].text, 'utf8');
  const { toHedgeMateViewModel } = await import(pathToFileURL(bundlePath).href);

  const matchingHash = 'portfolio-hash-aapl';
  const runId = 'run-aapl';
  const matchingPortfolio = {
    name: 'QA Stale Same Portfolio',
    totalValue: 1000000,
    assets: [{ ticker: 'AAPL', weight: 100 }],
  };
  const basePayload = {
    productStatus: 'STALE',
    freshnessStatus: 'STALE',
    dataFreshness: {
      freshnessStatus: 'STALE',
      marketDataFresh: false,
      needsRefresh: true,
      reasons: ['daily bar pending'],
    },
    manifest: {
      active_hedgemate_run: runId,
      generated_at_utc: '2026-05-28T09:00:00Z',
      portfolio_input_fingerprint: { hash: matchingHash, tickers: ['AAPL'] },
      active_bundle: {
        hedgemate_run: runId,
        portfolio_input_fingerprint: { hash: matchingHash, tickers: ['AAPL'] },
        portfolioInputSha256: 'sha-aapl',
      },
    },
    activeBundle: {
      hedgemate_run: runId,
      portfolio_input_fingerprint: { hash: matchingHash, tickers: ['AAPL'] },
      portfolioInputSha256: 'sha-aapl',
    },
    activeBundleIntegrity: {
      ok: true,
      activeRunId: runId,
      portfolioFingerprintHash: matchingHash,
      portfolioInputSha256: 'sha-aapl',
      tickers: ['AAPL'],
      missingArtifacts: [],
    },
    analysisCacheLookup: { requested: true, matched: true },
    hedgeActionPlan: [{ source_asset: 'AAPL', hedge_asset: 'TLT', action_status: 'REVIEW_ACTION' }],
    hedgeActionCandidates: [],
    portfolioVulnerabilitySummary: {
      data: {
        portfolio_total_vulnerability: 1,
        risk_sleeves: [{
          risk_sleeve: 'equity',
          net_vulnerability: 1,
          contribution_pct: 100,
          source_holdings: [{ ticker: 'AAPL' }],
        }],
      },
    },
    actionPlanDecision: { canExecuteAction: true, reviewActionCount: 1, reasonsKo: ['stale data'] },
    recommendationDecision: {},
  };

  const staleSamePortfolio = toHedgeMateViewModel(basePayload, matchingPortfolio, {
    expectedRunId: runId,
    portfolioInputFingerprintHash: matchingHash,
    runStatus: 'completed',
  });
  if (!staleSamePortfolio.reportDisplayReady) {
    fail('stale same-portfolio result should remain displayable', staleSamePortfolio.portfolioMatchDetail);
  }
  if (staleSamePortfolio.officialReportReady) {
    fail('stale same-portfolio result should not be treated as official/action-ready', staleSamePortfolio.portfolioMatchDetail);
  }
  if (staleSamePortfolio.decisionBanner.canExecuteAction) {
    fail('stale same-portfolio result should not enable execution action', staleSamePortfolio.decisionBanner);
  }

  const aliasHash = 'portfolio-hash-alias-edge';
  const aliasRunId = 'run-alias-edge';
  const aliasSelectedPortfolio = {
    name: 'QA Micro Edge Alias Portfolio',
    totalValue: 1000000,
    assets: [
      { ticker: 'Microsoft', weight: 38 },
      { ticker: 'BTC', weight: 34 },
      { ticker: 'Samsung', weight: 28 },
    ],
  };
  const aliasPayload = {
    ...basePayload,
    productStatus: 'REVIEW_ONLY',
    freshnessStatus: 'FRESH',
    dataFreshness: {
      freshnessStatus: 'FRESH',
      marketDataFresh: true,
      needsRefresh: false,
      reasons: [],
    },
    manifest: {
      ...basePayload.manifest,
      active_hedgemate_run: aliasRunId,
      portfolio_input_fingerprint: { hash: aliasHash, tickers: ['005930.KS', 'BTC-USD', 'MSFT'] },
      active_bundle: {
        ...basePayload.manifest.active_bundle,
        hedgemate_run: aliasRunId,
        portfolio_input_fingerprint: { hash: aliasHash, tickers: ['005930.KS', 'BTC-USD', 'MSFT'] },
      },
    },
    activeBundle: {
      ...basePayload.activeBundle,
      hedgemate_run: aliasRunId,
      portfolio_input_fingerprint: { hash: aliasHash, tickers: ['005930.KS', 'BTC-USD', 'MSFT'] },
    },
    activeBundleIntegrity: {
      ...basePayload.activeBundleIntegrity,
      activeRunId: aliasRunId,
      portfolioFingerprintHash: aliasHash,
      tickers: ['005930.KS', 'BTC-USD', 'MSFT'],
    },
  };
  const aliasTickerMismatch = toHedgeMateViewModel(aliasPayload, aliasSelectedPortfolio, {
    expectedRunId: aliasRunId,
    portfolioInputFingerprintHash: aliasHash,
    runStatus: 'completed',
  });
  if (aliasTickerMismatch.portfolioMatchDetail.tickersMatch) {
    fail('alias edge test setup should keep ticker arrays mismatched', aliasTickerMismatch.portfolioMatchDetail);
  }
  if (!aliasTickerMismatch.portfolioMatchDetail.fingerprintMatchVerified) {
    fail('alias edge should verify identity by fingerprint hash', aliasTickerMismatch.portfolioMatchDetail);
  }
  if (!aliasTickerMismatch.reportDisplayReady) {
    fail('matching run/hash/artifact should display even when ticker strings differ', aliasTickerMismatch.portfolioMatchDetail);
  }

  const foreignPayload = {
    ...basePayload,
    activeBundle: {
      ...basePayload.activeBundle,
      portfolio_input_fingerprint: { hash: 'foreign-hash-msft', tickers: ['MSFT'] },
    },
    manifest: {
      ...basePayload.manifest,
      portfolio_input_fingerprint: { hash: 'foreign-hash-msft', tickers: ['MSFT'] },
      active_bundle: {
        ...basePayload.manifest.active_bundle,
        portfolio_input_fingerprint: { hash: 'foreign-hash-msft', tickers: ['MSFT'] },
      },
    },
    activeBundleIntegrity: {
      ...basePayload.activeBundleIntegrity,
      portfolioFingerprintHash: 'foreign-hash-msft',
      tickers: ['MSFT'],
    },
  };
  const foreignResult = toHedgeMateViewModel(foreignPayload, matchingPortfolio, {
    expectedRunId: runId,
    portfolioInputFingerprintHash: matchingHash,
    runStatus: 'completed',
  });
  if (foreignResult.reportDisplayReady) {
    fail('foreign cached result must stay hidden', foreignResult.portfolioMatchDetail);
  }

  const scorePayload = {
    ...basePayload,
    productStatus: 'REVIEW_ONLY',
    freshnessStatus: 'FRESH',
    dataFreshness: {
      freshnessStatus: 'FRESH',
      marketDataFresh: true,
      needsRefresh: false,
      reasons: [],
    },
    hedgeActionPlan: [
      {
        action_id: 'c_candidate',
        action_status: 'REVIEW_ACTION',
        action_type: 'ADD_HEDGE',
        recommendation_grade: 'C',
        final_score: 1.0,
        user_display_score: 95,
        prescription_score: 100,
        direct_vulnerability_prescription: 'Y',
        risk_sleeve: 'equity',
        risk_sleeve_label_ko: 'Equity',
        source_tickers: 'AAPL',
        candidate_tickers: 'GLD',
        candidate_label: 'GLD',
        vulnerability_improve_pct: 99,
      },
      {
        action_id: 'b_candidate',
        action_status: 'REVIEW_ACTION',
        action_type: 'ADD_HEDGE',
        recommendation_grade: 'B',
        final_score: 0.1,
        prescription_score: 10,
        direct_vulnerability_prescription: 'Y',
        risk_sleeve: 'equity',
        risk_sleeve_label_ko: 'Equity',
        source_tickers: 'AAPL',
        candidate_tickers: 'PSQ',
        candidate_label: 'PSQ',
        vulnerability_improve_pct: 8,
      },
    ],
    hedgeActionCandidates: [
      {
        action_id: 'candidate_c',
        action_status: 'REVIEW_ACTION',
        recommendation_grade: 'C',
        final_score: 1.0,
        prescription_score: 100,
        vulnerability_improve_pct: 99,
      },
      {
        action_id: 'candidate_b',
        action_status: 'REVIEW_ACTION',
        recommendation_grade: 'B',
        final_score: 0.1,
        prescription_score: 10,
        vulnerability_improve_pct: 8,
      },
    ],
    portfolioVulnerabilitySummary: {
      data: {
        portfolio_total_vulnerability: 1,
        risk_sleeves: [{
          risk_sleeve: 'equity',
          risk_sleeve_label_ko: 'Equity',
          net_vulnerability: 1,
          contribution_pct: 100,
          source_holdings: [{ ticker: 'AAPL' }],
        }],
      },
    },
  };
  const scoreResult = toHedgeMateViewModel(scorePayload, matchingPortfolio, {
    expectedRunId: runId,
    portfolioInputFingerprintHash: matchingHash,
    runStatus: 'completed',
  });
  if (scoreResult.actionCards[0]?.id !== 'b_candidate') {
    fail('B grade action should sort ahead of C despite lower final_score', scoreResult.actionCards.map((row) => ({
      id: row.id,
      grade: row.recommendationGrade,
      userDisplayScore: row.userDisplayScore,
      linkedFinalScore: row.linkedFinalScore,
      prescriptionScore: row.prescriptionScore,
    })));
  }
  if (scoreResult.actionCards[0].userDisplayScore !== 72) {
    fail('B grade userDisplayScore fallback should use 70-89 band', scoreResult.actionCards[0]);
  }
  if (scoreResult.actionCards[1].userDisplayScore !== 69) {
    fail('C grade userDisplayScore should be clamped to 50-69 band', scoreResult.actionCards[1]);
  }
  if (scoreResult.actionCards[1].userDisplayScore === scoreResult.actionCards[1].prescriptionScore) {
    fail('prescriptionScore must not be used as the main recommendation score', scoreResult.actionCards[1]);
  }
  if (scoreResult.prescriptionRows[0]?.candidate?.id !== 'b_candidate') {
    fail('prescription row should use grade -> userDisplayScore -> improvePct ordering', scoreResult.prescriptionRows[0]);
  }

  console.log(JSON.stringify({
    ok: true,
    staleSamePortfolio: {
      reportDisplayReady: staleSamePortfolio.reportDisplayReady,
      officialReportReady: staleSamePortfolio.officialReportReady,
      canExecuteAction: staleSamePortfolio.decisionBanner.canExecuteAction,
    },
    aliasTickerMismatch: {
      reportDisplayReady: aliasTickerMismatch.reportDisplayReady,
      tickersMatch: aliasTickerMismatch.portfolioMatchDetail.tickersMatch,
      fingerprintMatchVerified: aliasTickerMismatch.portfolioMatchDetail.fingerprintMatchVerified,
    },
    foreignCachedResult: {
      reportDisplayReady: foreignResult.reportDisplayReady,
      tickersMatch: foreignResult.portfolioMatchDetail.tickersMatch,
    },
    scoreContract: {
      firstAction: scoreResult.actionCards[0]?.id,
      firstActionScore: scoreResult.actionCards[0]?.userDisplayScore,
      cActionScore: scoreResult.actionCards[1]?.userDisplayScore,
      prescriptionPrimary: scoreResult.prescriptionRows[0]?.candidate?.id,
    },
  }, null, 2));
} finally {
  await rm(tempDir, { recursive: true, force: true });
}
