import { resolveBackendAssetId } from './hedgemateApi';

const ACTION_STATUS_LABELS = {
  FORMAL_ACTION: '공식 실행 액션',
  REVIEW_ACTION: '검토 액션',
  RESEARCH_ONLY: '리서치 전용',
  FAIL_ACTION: '기준 미통과',
  NO_ACTION: '유효 액션 없음',
};

const ACTION_TYPE_LABELS = {
  ADD_HEDGE: '헷지 추가 검토',
  TRIM_AND_HEDGE: '비중 축소 + 헷지',
  REPLACE_SLEEVE: '대체 편입 검토',
  NO_ACTION: '액션 없음',
  FAIL_ACTION: '기준 미통과',
};

const RECOMMENDATION_GRADE_LABELS = {
  A: 'A 공식 실행 추천',
  B: 'B 조건부 처방',
  C: 'C 검토 후보',
  D: 'D 참고 benchmark',
};

const SAFE_BENCHMARK_TICKERS = new Set([
  '__CASH__',
  'CASH',
  'BIL',
  'SGOV',
  'SHV',
  'SHY',
  'VGSH',
  'VGIT',
  'VGLT',
  'EDV',
  'BND',
  'AGG',
  'GOVT',
  'IEF',
  'TLT',
  'GLD',
  'IAU',
  'TIP',
  'LQD',
  'VCSH',
  'VCIT',
  '132030.KS',
  '153130.KS',
]);

const GRADE_RANK = { A: 4, B: 3, C: 2, D: 1 };
const SCORE_METHOD_VERSION = 'grade_banded_final_score_v1';
const REPORT_READY_STATUSES = new Set(['ACTION_READY', 'READY', 'REVIEW_ONLY', 'STALE']);
const ACTION_READY_STATUSES = new Set(['ACTION_READY', 'READY']);
const GRADE_SCORE_BANDS = {
  A: [90, 100],
  B: [70, 89],
  C: [50, 69],
  D: [0, 49],
};

export const METRIC_DEFINITIONS = {
  cvar: {
    label: 'CVaR',
    helper: '극단적으로 나쁜 장에서 예상되는 평균 손실',
    lowerIsBetter: true,
    baseKeys: ['base_cvar_95', 'baseCvar95', 'base_cvar', 'cvar'],
    proposedKeys: ['proposed_cvar_95', 'proposedCvar95', 'proposed_cvar'],
    deltaKeys: ['cvar_delta', 'cvarDelta'],
    format: 'percent',
  },
  mdd: {
    label: 'MDD',
    helper: '고점 대비 최대 하락폭',
    lowerIsBetter: true,
    baseKeys: ['base_mdd', 'baseMdd', 'mdd'],
    proposedKeys: ['proposed_mdd', 'proposedMdd'],
    deltaKeys: ['mdd_delta', 'mddDelta'],
    format: 'percent',
  },
  beta: {
    label: 'beta',
    helper: '시장 또는 특정 리스크에 얼마나 민감한지',
    lowerIsBetter: true,
    baseKeys: ['base_beta_sp500_krw', 'baseBetaSp500Krw', 'base_beta', 'beta'],
    proposedKeys: ['proposed_beta_sp500_krw', 'proposedBetaSp500Krw', 'proposed_beta'],
    deltaKeys: ['beta_delta', 'betaDelta'],
    format: 'number',
  },
  stress: {
    label: 'stress',
    helper: '충격 상황에서의 예상 반응',
    lowerIsBetter: true,
    baseKeys: ['base_stress_avg_ret_krw', 'baseStressAvgRetKrw', 'base_stress', 'stress'],
    proposedKeys: ['proposed_stress_avg_ret_krw', 'proposedStressAvgRetKrw', 'proposed_stress'],
    deltaKeys: ['stress_delta', 'stressDelta'],
    format: 'percent',
  },
  sharpe: {
    label: 'Sharpe',
    helper: '변동성 대비 수익 효율',
    lowerIsBetter: false,
    baseKeys: ['base_sharpe_krw_proxy', 'baseSharpeKrwProxy', 'base_sharpe', 'sharpe'],
    proposedKeys: ['proposed_sharpe_krw_proxy', 'proposedSharpeKrwProxy', 'proposed_sharpe'],
    deltaKeys: ['sharpe_delta', 'sharpeDelta'],
    format: 'number',
  },
};

const asArray = (value) => Array.isArray(value) ? value : [];

const pick = (row, keys, fallback = null) => {
  for (const key of keys) {
    if (row?.[key] !== undefined && row?.[key] !== null && row?.[key] !== '') {
      return row[key];
    }
  }
  return fallback;
};

const toNumber = (value, fallback = null) => {
  if (value === null || value === undefined || value === '') return fallback;
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
};

const toBool = (value) => {
  if (typeof value === 'boolean') return value;
  return ['true', '1', 'y', 'yes'].includes(String(value || '').trim().toLowerCase());
};

const normalizeGrade = (row) => {
  const grade = String(row?.recommendation_grade || row?.recommendationGrade || '').trim().toUpperCase();
  return ['A', 'B', 'C', 'D'].includes(grade) ? grade : '';
};

const clip01 = (value) => Math.max(0, Math.min(1, toNumber(value, 0) ?? 0));

const scoreBandForGrade = (grade) => GRADE_SCORE_BANDS[grade] || null;

const scoreGradeForContract = (grade) => GRADE_SCORE_BANDS[grade] ? grade : 'D';

const scoreBandLabel = (grade) => {
  const scoreGrade = scoreGradeForContract(grade);
  const band = scoreBandForGrade(scoreGrade);
  return band ? `${scoreGrade}:${band[0]}-${band[1]}` : '';
};

const scoreContractFromRow = (row, recommendationGrade) => {
  const grade = recommendationGrade || normalizeGrade(row);
  const scoreGrade = scoreGradeForContract(grade);
  const band = scoreBandForGrade(scoreGrade);
  const linkedFinalScore = clip01(pick(row, ['linked_final_score', 'linkedFinalScore', 'final_score', 'finalScore'], 0));
  const providedDisplayScore = toNumber(pick(row, ['user_display_score', 'userDisplayScore'], null), null);
  let userDisplayScore = providedDisplayScore;

  if (userDisplayScore === null && band) {
    userDisplayScore = Math.round(band[0] + linkedFinalScore * (band[1] - band[0]));
  }
  if (userDisplayScore !== null && band) {
    userDisplayScore = Math.max(band[0], Math.min(band[1], Math.round(userDisplayScore)));
  }

  return {
    linkedFinalScore,
    userDisplayScore,
    scoreBand: row.score_band || row.scoreBand || scoreBandLabel(scoreGrade),
    scoreMethodVersion: row.score_method_version || row.scoreMethodVersion || SCORE_METHOD_VERSION,
  };
};

const splitTickers = (value) => {
  if (Array.isArray(value)) return value.filter(Boolean);
  return String(value || '')
    .split(/[|,+]/)
    .map((item) => item.trim())
    .filter(Boolean);
};

const parseWeightMap = (value) => {
  if (!value) return {};
  if (typeof value === 'object' && !Array.isArray(value)) return value;
  try {
    const parsed = JSON.parse(String(value));
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {};
  } catch {
    return {};
  }
};

const buildAdjustmentRows = (row, sourceTickers = [], hedgeTickers = []) => {
  const before = parseWeightMap(row.before_weights_json || row.beforeWeightsJson || row.beforeWeights);
  const after = parseWeightMap(row.after_weights_json || row.afterWeightsJson || row.afterWeights);
  const tickers = new Set([...Object.keys(before), ...Object.keys(after)]);

  if (tickers.size === 0) {
    sourceTickers.forEach((ticker) => tickers.add(ticker));
    hedgeTickers.forEach((ticker) => tickers.add(ticker));
  }

  return [...tickers]
    .map((ticker) => {
      const beforeWeight = toNumber(before[ticker], null);
      const afterWeight = toNumber(after[ticker], null);
      const fallbackBefore = sourceTickers.includes(ticker)
        ? toNumber(row.source_current_weight_pct ?? row.current_weight, 0)
        : toNumber(row.hedge_current_weight_pct, 0);
      const fallbackAfter = sourceTickers.includes(ticker)
        ? toNumber(row.source_proposed_weight_pct ?? row.proposed_weight, 0)
        : toNumber(row.hedge_proposed_weight_pct, 0);
      const currentWeight = beforeWeight ?? fallbackBefore;
      const proposedWeight = afterWeight ?? fallbackAfter;
      const delta = proposedWeight - currentWeight;
      return {
        ticker,
        currentWeight,
        proposedWeight,
        delta,
        role: sourceTickers.includes(ticker) ? 'source' : hedgeTickers.includes(ticker) ? 'hedge' : 'unchanged',
      };
    })
    .filter((item) => Math.abs(item.delta) >= 0.005)
    .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta) || a.ticker.localeCompare(b.ticker));
};

const unsafeDisplayReplacements = [
  ['정식 실행 추천', '검증 통과 액션'],
  ['정식 추천', '검증 통과 액션'],
  ['즉시 매수', '매수 검토'],
  ['즉시 매도', '매도 검토'],
  ['실행하기', '분석 실행'],
  ['추천 포트폴리오 확정', '검토 포트폴리오'],
  ['active bundle', '저장된 분석 결과'],
];

const safeKo = (value) => unsafeDisplayReplacements.reduce(
  (text, [unsafe, replacement]) => text.replaceAll(unsafe, replacement),
  String(value || '')
);

const friendlyFreshnessReason = (reason) => {
  const text = safeKo(reason).trim();
  const lower = text.toLowerCase();
  if (!text) return '';
  if (lower.startsWith('market data latest date')) {
    return '실시간 시장데이터 확인이 필요합니다. 일부 종목의 최신 가격이 아직 반영되지 않았습니다.';
  }
  if (lower.startsWith('scenario vector stale') || lower.startsWith('active analysis bundle data_version')) {
    return '';
  }
  if (lower.startsWith('scenario data_version')) {
    return '시장국면 분석 데이터와 현재 분석 기준일이 맞지 않습니다. 포트폴리오 분석을 다시 실행해 주세요.';
  }
  if (lower.startsWith('portfolio input mismatch')) {
    return '선택한 포트폴리오와 저장된 분석 결과가 다릅니다. 포트폴리오 분석을 다시 실행해 주세요.';
  }
  return text;
};

const uniqueMessages = (messages) => [...new Set(messages.map((message) => String(message || '').trim()).filter(Boolean))];

const metricSetFromAction = (row, prefix = 'base') => {
  const result = {};
  Object.entries(METRIC_DEFINITIONS).forEach(([key, definition]) => {
    const valueKeys = prefix === 'base' ? definition.baseKeys : definition.proposedKeys;
    result[key] = toNumber(pick(row, valueKeys), 0);
  });
  return result;
};

const improvementPct = (base, proposed, key) => {
  const definition = METRIC_DEFINITIONS[key];
  if (!Number.isFinite(base) || !Number.isFinite(proposed) || base === 0) return 0;
  if (definition.lowerIsBetter) {
    if (base < 0 || proposed < 0) {
      return ((Math.abs(base) - Math.abs(proposed)) / Math.abs(base)) * 100;
    }
    return ((base - proposed) / Math.abs(base)) * 100;
  }
  return ((proposed - base) / Math.abs(base)) * 100;
};

export const formatMetricValue = (value, key) => {
  if (!Number.isFinite(Number(value))) return 'N/A';
  const definition = METRIC_DEFINITIONS[key];
  if (definition?.format === 'percent') {
    return `${(Number(value) * 100).toFixed(2)}%`;
  }
  return Number(value).toFixed(key === 'sharpe' ? 2 : 3);
};

export const formatMetricDelta = (base, proposed, key) => {
  const pct = improvementPct(base, proposed, key);
  const direction = pct >= 0 ? '개선' : '악화';
  return `${Math.abs(pct).toFixed(2)}% ${direction}`;
};

const normalizeAction = (row, index, decision, portfolioMatches = true) => {
  const actionStatus = String(row.action_status || row.actionStatus || 'NO_ACTION').toUpperCase();
  const canExecute = Boolean(decision?.canExecuteAction) && portfolioMatches && actionStatus === 'FORMAL_ACTION' && toBool(row.can_execute_action);
  const displayStatus = canExecute ? actionStatus : (actionStatus === 'FORMAL_ACTION' ? 'REVIEW_ACTION' : actionStatus);
  const baseMetrics = metricSetFromAction(row, 'base');
  const proposedMetrics = metricSetFromAction(row, 'proposed');
  const hedgeTickers = splitTickers(row.candidate_tickers || row.hedge_asset || row.hedgeAsset);
  const sourceTickers = splitTickers(row.source_tickers || row.source_asset || row.sourceAsset);
  const recommendationGrade = normalizeGrade(row);
  const scoreContract = scoreContractFromRow(row, recommendationGrade);
  const adjustmentRows = buildAdjustmentRows(row, sourceTickers, hedgeTickers);

  return {
    id: row.action_id || row.actionId || `action-${index + 1}`,
    rank: index + 1,
    raw: row,
    title: ACTION_TYPE_LABELS[row.action_type] || row.action_type || '검토 액션',
    badge: ACTION_STATUS_LABELS[displayStatus] || '검토 필요 후보',
    actionStatus,
    displayStatus,
    actionType: row.action_type || row.actionType || '',
    recommendationGrade,
    recommendationGradeLabel: row.recommendation_grade_label_ko || row.recommendationGradeLabelKo || RECOMMENDATION_GRADE_LABELS[recommendationGrade] || '등급 미분류',
    recommendationGradeReason: safeKo(row.recommendation_grade_reason_ko || row.recommendationGradeReasonKo),
    directVulnerabilityPrescription: toBool(row.direct_vulnerability_prescription || row.directVulnerabilityPrescription),
    basisRiskLevel: row.basis_risk_level || row.basisRiskLevel || '',
    prescriptionScore: toNumber(row.prescription_score ?? row.prescriptionScore, null),
    linkedFinalScore: scoreContract.linkedFinalScore,
    userDisplayScore: scoreContract.userDisplayScore,
    scoreBand: scoreContract.scoreBand,
    scoreMethodVersion: scoreContract.scoreMethodVersion,
    canExecute,
    riskSleeve: row.risk_sleeve || row.riskSleeve || '',
    riskSleeveLabel: row.risk_sleeve_label_ko || row.riskSleeveLabelKo || row.risk_sleeve || '리스크 축',
    sourceTickers,
    hedgeTickers,
    adjustmentRows,
    candidateLabel: row.candidate_label || row.candidateLabel || hedgeTickers.join(' + ') || '헷지 후보',
    currentWeight: toNumber(row.current_weight ?? row.source_current_weight_pct, 0),
    proposedWeight: toNumber(row.proposed_weight ?? row.source_proposed_weight_pct, 0),
    hedgeWeight: toNumber(row.hedge_proposed_weight_pct, 0),
    vulnerabilityImprovePct: toNumber(row.vulnerability_improve_pct, 0),
    beforeSleeveVulnerability: toNumber(row.before_sleeve_vulnerability, 0),
    afterSleeveVulnerability: toNumber(row.after_sleeve_vulnerability, 0),
    expectedEffect: safeKo(row.expected_effect),
    actionReasonKo: safeKo(row.action_reason_ko || row.plain_korean_reason),
    plainKoreanReason: safeKo(row.plain_korean_reason || row.action_reason_ko),
    statusReasonKo: safeKo(row.status_reason_ko),
    rejectedReasonKo: safeKo(row.rejected_reason_ko),
    selectionReasonKo: safeKo(row.selection_reason_ko || row.not_selected_reason_ko),
    baseMetrics,
    proposedMetrics,
    metricRows: Object.keys(METRIC_DEFINITIONS).map((metricKey) => ({
      key: metricKey,
      label: METRIC_DEFINITIONS[metricKey].label,
      helper: METRIC_DEFINITIONS[metricKey].helper,
      base: baseMetrics[metricKey],
      proposed: proposedMetrics[metricKey],
      formattedBase: formatMetricValue(baseMetrics[metricKey], metricKey),
      formattedProposed: formatMetricValue(proposedMetrics[metricKey], metricKey),
      improvementText: formatMetricDelta(baseMetrics[metricKey], proposedMetrics[metricKey], metricKey),
    })),
  };
};

const normalizeVulnerability = (row, index, total = 0) => {
  const sourceHoldings = asArray(row.source_holdings || row.sourceHoldings);
  return {
    rank: index + 1,
    riskSleeve: row.risk_sleeve || row.riskSleeve || '',
    label: row.risk_sleeve_label_ko || row.riskSleeveLabelKo || row.risk_sleeve || '리스크 축',
    netVulnerability: toNumber(row.net_vulnerability ?? row.netVulnerability, 0),
    contributionPct: total ? (toNumber(row.net_vulnerability ?? row.netVulnerability, 0) / total) * 100 : 0,
    sourceHoldings: sourceHoldings.slice(0, 5).map((holding) => ({
      ticker: holding.ticker,
      contribution: toNumber(holding.contribution, 0),
      contributionPct: toNumber(
        holding.contribution_pct
        ?? holding.contributionPct
        ?? holding.sleeve_contribution_pct
        ?? holding.contribution_pct_of_sleeve,
        null
      ),
      weightPct: toNumber(holding.current_weight_pct ?? holding.weight_pct ?? holding.weightPct, null),
    })),
    offsetHoldings: asArray(row.offset_holdings || row.offsetHoldings).slice(0, 5),
  };
};

const normalizeAttribution = (row, index) => ({
  id: `${row.risk_sleeve || row.scenario || 'risk'}-${row.ticker || row.asset_ticker || 'asset'}-${index}`,
  riskSleeve: row.risk_sleeve || row.riskSleeve || '',
  riskSleeveLabel: row.risk_sleeve_label_ko || row.riskSleeveLabelKo || row.risk_sleeve || '',
  scenario: row.scenario_name_ko || row.scenario || row.scenario_code || '',
  asset: row.asset_ticker || row.ticker || row.source_asset || '',
  sourceOrOffset: row.source_or_offset || '',
  currentWeight: toNumber(row.current_weight_pct ?? row.current_weight ?? row.weight_pct, 0),
  contributionPct: toNumber(row.contribution_pct ?? row.contribution_pct_of_sleeve ?? row.sleeve_contribution_pct, 0),
  vulnerabilityContribution: toNumber(row.vulnerability_contribution ?? row.weighted_contribution, 0),
  evidenceQuality: row.evidence_quality || '',
  reason: safeKo(row.plain_korean_reason || row.plain_reason_ko),
});

const normalizeCandidate = (row, index) => {
  const recommendationGrade = normalizeGrade(row);
  const scoreContract = scoreContractFromRow(row, recommendationGrade);
  const sourceTickers = splitTickers(row.source_tickers || row.source_asset || row.sourceAsset);
  const hedgeTickers = splitTickers(row.candidate_tickers || row.hedge_asset || row.hedgeAsset);
  const adjustmentRows = buildAdjustmentRows(row, sourceTickers, hedgeTickers);
  return {
    id: row.action_id || `candidate-${index + 1}`,
    status: row.action_status === 'FORMAL_ACTION' && !toBool(row.can_execute_action) ? 'REVIEW_ACTION' : (row.action_status || 'NO_ACTION'),
    actionType: row.action_type || '',
    recommendationGrade,
    recommendationGradeLabel: row.recommendation_grade_label_ko || row.recommendationGradeLabelKo || RECOMMENDATION_GRADE_LABELS[recommendationGrade] || '등급 미분류',
    recommendationGradeReason: safeKo(row.recommendation_grade_reason_ko || row.recommendationGradeReasonKo),
    linkedFinalScore: scoreContract.linkedFinalScore,
    userDisplayScore: scoreContract.userDisplayScore,
    scoreBand: scoreContract.scoreBand,
    scoreMethodVersion: scoreContract.scoreMethodVersion,
    riskSleeve: row.risk_sleeve || row.riskSleeve || '',
    riskSleeveLabel: row.risk_sleeve_label_ko || row.risk_sleeve || '',
    sourceAsset: sourceTickers.join(', ') || row.source_asset || row.source_tickers || '',
    hedgeAsset: row.candidate_label || hedgeTickers.join(', ') || row.hedge_asset || row.candidate_tickers || '',
    sourceTickers,
    hedgeTickers,
    adjustmentRows,
    improvePct: toNumber(row.vulnerability_improve_pct, 0),
    canExecute: toBool(row.can_execute_action),
    directVulnerabilityPrescription: toBool(row.direct_vulnerability_prescription || row.directVulnerabilityPrescription),
    blockers: row.formal_gate_blockers || row.linked_formal_gate_blockers || row.formal_gate_status || '',
    reason: safeKo(
      row.plain_korean_reason
      || row.action_reason_ko
      || row.status_reason_ko
      || row.not_selected_reason_ko
      || row.rejected_reason_ko
      || row.recommendation_grade_reason_ko
      || row.formal_gate_blockers
      || row.linked_formal_gate_blocker_summary
      || row.formal_gate_status
      || row.action_status
    ),
  };
};

const normalizeActionTypeCoverage = (coverage = {}) => {
  return Object.entries(coverage).map(([actionType, item]) => ({
    actionType,
    label: ACTION_TYPE_LABELS[actionType] || actionType,
    candidateCount: Number(item?.candidate_count ?? item?.count ?? 0),
    selectedCount: Number(item?.selected_count ?? 0),
    presentInCandidates: Boolean(item?.present_in_candidates ?? item?.present),
    presentInSelected: Boolean(item?.present_in_selected),
    reasonKo: safeKo(item?.reason_ko),
    absenceReasonKo: safeKo(item?.absence_reason_ko),
    absenceReasonCode: item?.absence_reason_code || '',
  }));
};

const selectedTickerList = (portfolio) => {
  return (portfolio?.assets || [])
    .map((asset) => resolveBackendAssetId(asset))
    .filter(Boolean)
    .sort();
};

const activeTickerList = (payload) => {
  const tickers = payload?.activeBundle?.portfolio_input_fingerprint?.tickers
    || payload?.manifest?.active_bundle?.portfolio_input_fingerprint?.tickers
    || payload?.activeBundle?.portfolioTickers
    || payload?.manifest?.active_bundle?.portfolioTickers
    || [];
  return [...tickers].filter(Boolean).sort();
};

const sameSet = (a, b) => a.size === b.size && [...a].every((value) => b.has(value));

const normalizeTicker = (ticker) => String(ticker || '').trim().toUpperCase();

const normalizeTickerList = (tickers) => [...new Set((tickers || []).map(normalizeTicker).filter(Boolean))].sort();

const splitAssetText = (value) => splitTickers(value).map(normalizeTicker).filter(Boolean);

const includesBenchmarkAsset = (value) => splitAssetText(value).some((ticker) => SAFE_BENCHMARK_TICKERS.has(ticker));

const sameRiskSleeve = (left, right) => normalizeTicker(left) === normalizeTicker(right);

const prescriptionCandidateFromAction = (action) => ({
  id: action.id,
  source: 'selected',
  status: action.displayStatus || action.actionStatus || '',
  actionType: action.actionType,
  riskSleeve: action.riskSleeve,
  riskSleeveLabel: action.riskSleeveLabel,
  sourceAsset: action.sourceTickers.join(', '),
  hedgeAsset: action.candidateLabel || action.hedgeTickers.join(', '),
  sourceTickers: action.sourceTickers,
  hedgeTickers: action.hedgeTickers,
  adjustmentRows: action.adjustmentRows,
  improvePct: action.vulnerabilityImprovePct,
  canExecute: action.canExecute,
  directVulnerabilityPrescription: Boolean(action.directVulnerabilityPrescription),
  recommendationGrade: action.recommendationGrade,
  recommendationGradeLabel: action.recommendationGradeLabel,
  linkedFinalScore: action.linkedFinalScore,
  userDisplayScore: action.userDisplayScore,
  scoreBand: action.scoreBand,
  scoreMethodVersion: action.scoreMethodVersion,
  prescriptionScore: action.prescriptionScore,
  reason: action.plainKoreanReason || action.actionReasonKo || action.expectedEffect || action.statusReasonKo || '',
  metricRows: action.metricRows,
});

const classifyPrescription = (candidate, directMatch) => {
  if (!candidate) return { grade: 'D', benchmarkOnly: true };
  const benchmarkOnly = includesBenchmarkAsset(candidate.hedgeAsset) && !directMatch;
  if (benchmarkOnly) return { grade: 'D', benchmarkOnly: true };
  if (candidate.canExecute && candidate.status === 'FORMAL_ACTION') return { grade: 'A', benchmarkOnly: false };
  if (candidate.source === 'selected' && directMatch && ['FORMAL_ACTION', 'REVIEW_ACTION'].includes(candidate.status)) {
    const existing = candidate.recommendationGrade || normalizeGrade(candidate);
    return { grade: existing === 'A' ? 'A' : (existing || 'B'), benchmarkOnly: false };
  }
  if (directMatch && candidate.improvePct > 0) {
    const existing = candidate.recommendationGrade || normalizeGrade(candidate);
    return { grade: existing && existing !== 'A' ? existing : 'C', benchmarkOnly: false };
  }
  return { grade: 'D', benchmarkOnly: true };
};

const gradeRankForSort = (grade) => GRADE_RANK[grade] || 0;

const scoreForSort = (value) => Number.isFinite(Number(value)) ? Number(value) : -1;

const compareRecommendationRows = (a, b) => (
  gradeRankForSort(b.recommendationGrade) - gradeRankForSort(a.recommendationGrade)
  || scoreForSort(b.userDisplayScore) - scoreForSort(a.userDisplayScore)
  || Number(b.vulnerabilityImprovePct ?? b.improvePct ?? 0) - Number(a.vulnerabilityImprovePct ?? a.improvePct ?? 0)
  || scoreForSort(b.linkedFinalScore) - scoreForSort(a.linkedFinalScore)
  || String(a.id || '').localeCompare(String(b.id || ''))
);

const buildPrescriptionRows = (topVulnerabilities, actionCards) => {
  const pool = actionCards.map(prescriptionCandidateFromAction);

  return topVulnerabilities.slice(0, 3).map((vulnerability) => {
    const directMatches = pool
      .filter((candidate) => (
        sameRiskSleeve(candidate.riskSleeve, vulnerability.riskSleeve)
        && candidate.directVulnerabilityPrescription
        && Number(candidate.improvePct) > 0
      ))
      .sort((a, b) => {
        const aClass = classifyPrescription(a, true);
        const bClass = classifyPrescription(b, true);
        return (GRADE_RANK[bClass.grade] || 0) - (GRADE_RANK[aClass.grade] || 0)
          || scoreForSort(b.userDisplayScore) - scoreForSort(a.userDisplayScore)
          || Number(b.improvePct || 0) - Number(a.improvePct || 0);
      });
    const primary = directMatches[0] || null;
    const directMatch = Boolean(directMatches[0]);
    const classification = classifyPrescription(primary, directMatch);
    const grade = classification.grade;

    return {
      id: `prescription-${vulnerability.riskSleeve || vulnerability.rank}`,
      vulnerability,
      candidate: primary,
      grade,
      gradeLabel: RECOMMENDATION_GRADE_LABELS[grade],
      userDisplayScore: primary?.userDisplayScore ?? null,
      scoreBand: primary?.scoreBand || scoreBandLabel(grade),
      scoreMethodVersion: primary?.scoreMethodVersion || (scoreBandForGrade(grade) ? SCORE_METHOD_VERSION : ''),
      benchmarkOnly: classification.benchmarkOnly,
      directMatch,
      sourceAssets: vulnerability.sourceHoldings.map((holding) => holding.ticker).filter(Boolean),
      reason: primary
        ? (directMatch
          ? `${primary.hedgeAsset || '후보'}는 ${vulnerability.label} 취약점에 직접 연결된 후보입니다.`
          : `${primary.hedgeAsset || '후보'}는 직접 처방 근거가 부족해 benchmark로만 표시합니다.`)
        : '이 취약점에 직접 연결된 헷지 후보가 아직 없습니다.',
    };
  });
};

export const toHedgeMateViewModel = (payload, selectedPortfolio, options = {}) => {
  const actionPlan = asArray(payload?.hedgeActionPlan);
  const candidateRows = asArray(payload?.hedgeActionCandidates)
    .map(normalizeCandidate)
    .sort(compareRecommendationRows)
    .slice(0, 40);
  const decision = payload?.actionPlanDecision || {};
  const recommendationDecision = payload?.recommendationDecision || {};
  const dataFreshness = { ...(payload?.dataFreshness || {}) };
  const summaryData = payload?.portfolioVulnerabilitySummary?.data || payload?.portfolioVulnerabilitySummary || {};
  const totalVulnerability = toNumber(summaryData.portfolio_total_vulnerability, 0);
  const topVulnerabilities = asArray(summaryData.risk_sleeves)
    .map((row, index) => normalizeVulnerability(row, index, totalVulnerability))
    .filter((row) => row.netVulnerability > 0)
    .slice(0, 6);

  const selectedTickers = normalizeTickerList(selectedTickerList(selectedPortfolio));
  const activeTickers = normalizeTickerList(activeTickerList(payload));
  const activeBundleFingerprint = payload?.activeBundle?.portfolio_input_fingerprint
    || payload?.manifest?.active_bundle?.portfolio_input_fingerprint
    || {};
  const manifestFingerprint = payload?.manifest?.portfolio_input_fingerprint || {};
  const manifestRunId = payload?.manifest?.active_hedgemate_run || '';
  const bundleRunId = payload?.activeBundle?.hedgemate_run || payload?.manifest?.active_bundle?.hedgemate_run || '';
  const activeRunId = bundleRunId || manifestRunId || '';
  const productStatus = payload?.productStatus || '';
  const analysisCacheLookup = payload?.analysisCacheLookup || {};
  const analysisCacheHit = analysisCacheLookup.hit === true || analysisCacheLookup.matched === true;
  const cacheLookupOk = !analysisCacheLookup.requested || analysisCacheHit;
  const expectedRunId = options.expectedRunId || '';
  const expectedFingerprintHash = options.portfolioInputFingerprintHash || '';
  const hasExpectedRunId = Boolean(expectedRunId);
  const hasExpectedFingerprintHash = Boolean(expectedFingerprintHash);
  const selectedPortfolioId = selectedPortfolio?.portfolioId || selectedPortfolio?.id || '';
  const payloadPortfolioId = payload?.selectedPortfolio?.portfolioId
    || payload?.selectedPortfolio?.id
    || payload?.portfolioRun?.portfolioId
    || '';
  const savedPortfolioRunVerified = Boolean(
    payload?.serverContractVersion === 'action_contract_v4_portfolio_runs'
    && selectedPortfolioId
    && payloadPortfolioId
    && String(selectedPortfolioId) === String(payloadPortfolioId)
    && String(payload?.portfolioRun?.status || '').toUpperCase() === 'SUCCESS'
  );
  const integrityFingerprintHash = payload?.activeBundleIntegrity?.portfolioFingerprintHash || '';
  const activeFingerprintHash = activeBundleFingerprint?.hash || manifestFingerprint?.hash || integrityFingerprintHash || '';
  const rawFreshnessStatus = payload?.freshnessStatus || dataFreshness.freshnessStatus || '';
  const marketDataFresh = dataFreshness.marketDataFresh !== undefined
    ? dataFreshness.marketDataFresh !== false
    : dataFreshness.freshnessStatus !== 'STALE';
  const freshnessStatus = rawFreshnessStatus || (marketDataFresh ? 'FRESH' : 'STALE');
  const displayFreshEnough = freshnessStatus !== 'STALE' && marketDataFresh;
  const rawDataNeedsRefresh = Boolean(dataFreshness.needsRefresh);
  if (rawDataNeedsRefresh && displayFreshEnough) {
    dataFreshness.needsRefresh = false;
  }
  const artifactIntegrity = payload?.activeBundleIntegrity || {};
  const artifactIntegrityOk = Boolean(payload?.activeBundleIntegrity)
    && artifactIntegrity.ok === true
    && asArray(artifactIntegrity.missingArtifacts).length === 0;
  const tickersMatch = payload ? sameSet(new Set(selectedTickers), new Set(activeTickers)) : false;
  const manifestRunMatches = hasExpectedRunId ? manifestRunId === expectedRunId : Boolean(manifestRunId);
  const bundleRunMatches = hasExpectedRunId ? bundleRunId === expectedRunId : Boolean(bundleRunId);
  const runMatches = savedPortfolioRunVerified || (hasExpectedRunId ? manifestRunMatches && bundleRunMatches : Boolean(activeRunId));
  const cacheEvidenceOk = cacheLookupOk || (hasExpectedRunId && runMatches);
  const bundleHashMatches = savedPortfolioRunVerified || (hasExpectedFingerprintHash ? activeBundleFingerprint?.hash === expectedFingerprintHash : Boolean(activeBundleFingerprint?.hash));
  const manifestHashMatches = savedPortfolioRunVerified || (hasExpectedFingerprintHash ? manifestFingerprint?.hash === expectedFingerprintHash : Boolean(manifestFingerprint?.hash || activeBundleFingerprint?.hash));
  const integrityHashMatches = savedPortfolioRunVerified || (hasExpectedFingerprintHash ? integrityFingerprintHash === expectedFingerprintHash : Boolean(integrityFingerprintHash || activeBundleFingerprint?.hash));
  const portfolioHashMatches = bundleHashMatches && manifestHashMatches && integrityHashMatches;
  const fingerprintMatchVerified = savedPortfolioRunVerified || (hasExpectedFingerprintHash && portfolioHashMatches);
  const portfolioIdentityMatches = savedPortfolioRunVerified || tickersMatch || fingerprintMatchVerified;
  const runCompleted = savedPortfolioRunVerified || (options.runStatus ? options.runStatus === 'completed' : Boolean(activeRunId));
  const backendAllowsReport = REPORT_READY_STATUSES.has(productStatus);
  const portfolioMatches = Boolean(selectedPortfolio) && (savedPortfolioRunVerified || (portfolioIdentityMatches && portfolioHashMatches));
  const verifiedSelectedPortfolioResult = savedPortfolioRunVerified
    ? Boolean(selectedPortfolio) && backendAllowsReport && artifactIntegrityOk && runCompleted
    : Boolean(selectedPortfolio)
    && selectedTickers.length > 0
    && (activeTickers.length > 0 || fingerprintMatchVerified)
    && portfolioIdentityMatches
    && portfolioHashMatches
    && runMatches
    && runCompleted
    && backendAllowsReport
    && artifactIntegrityOk
    && cacheEvidenceOk;
  const officialReportReady = verifiedSelectedPortfolioResult && displayFreshEnough;
  // Do not surface stale/foreign active-bundle data for the selected portfolio.
  // The report view must stay in the analysis-required state until the backend
  // proves ticker, weight fingerprint, run, cache, and artifacts all match the
  // currently selected portfolio. Market freshness is surfaced as a warning so
  // a just-finished analysis is not hidden merely because today's final bar is
  // not available yet.
  const reportDisplayReady = verifiedSelectedPortfolioResult;
  const actionCards = actionPlan
    .map((row, index) => normalizeAction(row, index, decision, reportDisplayReady))
    .sort(compareRecommendationRows)
    .map((action, index) => ({ ...action, rank: index + 1 }));
  const prescriptionRows = buildPrescriptionRows(topVulnerabilities, actionCards);
  const firstAction = actionCards[0] || null;
  const secondAction = actionCards[1] || null;
  const baseMetrics = firstAction?.baseMetrics || { cvar: 0, mdd: 0, beta: 0, stress: 0, sharpe: 0 };
  const canExecuteAction = Boolean(decision.canExecuteAction) && officialReportReady && ACTION_READY_STATUSES.has(productStatus);
  const evaluatedCandidateCount = candidateRows.length;
  const selectedActionCount = actionCards.length;
  const candidateStatusCounts = candidateRows.reduce((counts, row) => {
    counts[row.status] = (counts[row.status] || 0) + 1;
    return counts;
  }, {});
  const recommendationGradeCounts = decision.recommendationGradeCounts || decision.recommendation_grade_counts || {};
  const selectedRecommendationGradeCounts = decision.selectedRecommendationGradeCounts
    || decision.selected_recommendation_grade_counts
    || recommendationGradeCounts;
  const noSelectedActionSummary = reportDisplayReady && !canExecuteAction && selectedActionCount === 0 && evaluatedCandidateCount > 0
    ? `평가 후보 ${evaluatedCandidateCount}개를 계산했지만 backtest/formal gate를 통과한 최종 선택 액션은 없습니다. 후보 테이블에서 실패 사유를 확인할 수 있습니다.`
    : '';
  const rawFreshnessReasons = asArray(dataFreshness.reasons).map((reason) => String(reason || '').trim()).filter(Boolean);
  const marketDataDelayed = dataFreshness.marketDataFresh === false
    || asArray(dataFreshness.marketDataStaleTickers).length > 0
    || asArray(dataFreshness.marketDataFailedTickers).length > 0
    || rawFreshnessReasons.some((reason) => /^market data latest date/i.test(reason));
  const analysisBundleStale = Boolean(dataFreshness.activeBundleOlderThanMarketCache)
    || rawFreshnessReasons.some((reason) => /scenario vector stale|active analysis bundle data_version/i.test(reason));
  const userFacingFreshnessReasons = rawFreshnessReasons
    .map(friendlyFreshnessReason)
    .filter(Boolean);
  const portfolioMatchMessage = !selectedPortfolio
    ? '선택된 프론트 포트폴리오가 없습니다.'
    : tickersMatch
      ? '선택 포트폴리오와 저장된 분석 결과의 종목은 일치합니다. 비중 일치 여부는 재분석으로 확인합니다.'
      : `선택 포트폴리오(${selectedTickers.join(', ') || '-'})와 저장된 분석 결과(${activeTickers.join(', ') || '-'})의 종목 구성이 다릅니다.`;
  const blockerText = safeKo(asArray(decision.reasonsKo || decision.reasons_ko).join(' ')
    || decision.whyNoFormalKo
    || decision.why_no_formal_ko)
    || '분석은 완료됐지만 실행 추천으로 확정할 만큼의 검증 근거가 아직 부족합니다.';
  const actionTypeCoverage = normalizeActionTypeCoverage(decision.actionTypeCoverage);
  const selectedTypeCount = Object.keys(decision.selectedActionTypeCounts || {}).length;
  const actionDiversityWarning = selectedTypeCount === 1 && actionTypeCoverage.some((item) => item.presentInCandidates && !item.presentInSelected)
    ? '선택 액션이 특정 유형에 집중되어 있습니다. 후보는 있었지만 취약성 개선 우선순위 때문에 선택 계획에서 제외된 유형이 있습니다.'
    : '';

  return {
    raw: options.includeRawPayload ? payload : null,
    activeRunId,
    updatedAt: payload?.activeBundle?.generated_at_utc || payload?.manifest?.generated_at_utc || payload?.dataFreshness?.generatedAtUtc || '',
    productStatus,
    freshnessStatus,
    officialReportReady,
    reportDisplayReady,
    portfolioMatches,
    portfolioMatchDetail: {
      savedPortfolioRunVerified,
      tickersMatch,
      fingerprintMatchVerified,
      portfolioIdentityMatches,
      weightVerified: Boolean(expectedFingerprintHash && portfolioHashMatches),
      portfolioHashMatches,
      bundleHashMatches,
      manifestHashMatches,
      integrityHashMatches,
      manifestRunMatches,
      bundleRunMatches,
      runMatches,
      runCompleted,
      artifactIntegrityOk,
      cacheLookupOk: cacheEvidenceOk,
      analysisCacheHit,
      displayFreshEnough,
      marketDataFresh,
      dataNeedsRefresh: rawDataNeedsRefresh,
      missingArtifacts: asArray(artifactIntegrity.missingArtifacts),
      selectedTickers,
      activeTickers,
      activeFingerprintHash,
      expectedFingerprintHash,
      expectedRunId,
      message: portfolioMatchMessage,
    },
    decisionBanner: {
      canExecuteAction,
      title: !reportDisplayReady
        ? '분석 필요'
        : !officialReportReady
          ? '저장된 분석 결과 표시 중'
        : canExecuteAction
          ? '검증된 액션 플랜이 있습니다'
          : '분석 완료 · 검토 후보 표시 중',
      badge: !reportDisplayReady ? (productStatus || 'NEEDS_ANALYSIS') : !officialReportReady ? 'REVIEW_ONLY' : canExecuteAction ? 'READY' : 'REVIEW_ONLY',
      tone: !reportDisplayReady ? 'stale' : canExecuteAction ? 'ready' : 'review',
      summary: !reportDisplayReady
        ? '이 포트폴리오에 대한 최신 분석 결과가 없습니다. 분석을 실행해야 리포트를 볼 수 있습니다.'
        : !officialReportReady
          ? '선택 포트폴리오와 최신성 조건을 다시 확인해야 하지만, 백엔드에 저장된 분석 결과가 있어 검토용으로 먼저 표시합니다.'
        : noSelectedActionSummary
          ? noSelectedActionSummary
          : safeKo(canExecuteAction
          ? '백엔드 gate를 통과한 액션 플랜이 있어 최종 확인 단계로 볼 수 있습니다.'
          : `실행 추천은 아니며, 현재는 검토용 액션 후보입니다. ${blockerText}`),
      blockers: asArray(decision.blockers).map(safeKo),
      upgradeRequirements: asArray(decision.upgradeRequirements || decision.upgrade_requirements).map(safeKo),
      counts: {
        formal: reportDisplayReady ? (decision.formalActionCount || 0) : 0,
        formalRecommendations: reportDisplayReady ? (recommendationDecision.formalRecommendationCount || 0) : 0,
        review: reportDisplayReady ? (decision.reviewActionCount || 0) : 0,
        fail: reportDisplayReady ? (decision.failActionCount || 0) : 0,
        noAction: reportDisplayReady ? (decision.noActionCount || 0) : 0,
        selectedActions: reportDisplayReady ? selectedActionCount : 0,
        evaluatedCandidates: reportDisplayReady ? evaluatedCandidateCount : 0,
        failCandidates: reportDisplayReady ? (candidateStatusCounts.FAIL_ACTION || 0) : 0,
        gradeA: reportDisplayReady ? Number(decision.gradeAActionCount ?? selectedRecommendationGradeCounts.A ?? 0) : 0,
        gradeB: reportDisplayReady ? Number(decision.gradeBActionCount ?? selectedRecommendationGradeCounts.B ?? 0) : 0,
        gradeC: reportDisplayReady ? Number(decision.gradeCActionCount ?? selectedRecommendationGradeCounts.C ?? 0) : 0,
        gradeD: reportDisplayReady ? Number(decision.gradeDActionCount ?? selectedRecommendationGradeCounts.D ?? 0) : 0,
      },
      actionTypeCoverage,
    },
    portfolioData: {
      base: baseMetrics,
      recommended: firstAction?.proposedMetrics || baseMetrics,
      optimized: secondAction?.proposedMetrics || firstAction?.proposedMetrics || baseMetrics,
      labels: {
        base: '현재 포트폴리오',
        recommended: firstAction ? `검토 액션 1 · ${firstAction.candidateLabel}` : '검토 액션 없음',
        optimized: secondAction ? `검토 액션 2 · ${secondAction.candidateLabel}` : '추가 액션 없음',
      },
      actions: [firstAction, secondAction].filter(Boolean),
    },
    actionCards,
    prescriptionRows,
    topVulnerabilities,
    attributionRows: asArray(payload?.portfolioVulnerabilityAttribution)
      .map(normalizeAttribution)
      .filter((row) => row.sourceOrOffset === 'source' || row.vulnerabilityContribution > 0)
      .sort((a, b) => b.vulnerabilityContribution - a.vulnerabilityContribution)
      .slice(0, 18),
    candidateRows,
    warnings: uniqueMessages([
      ...(rawDataNeedsRefresh && displayFreshEnough ? ['시장데이터는 최신이지만 실행 검증 조건 일부가 차단되어 검토 후보로만 표시합니다.'] : []),
      ...(marketDataDelayed ? ['실시간 시장데이터 확인이 필요합니다. 일부 종목의 최신 가격이 아직 반영되지 않았습니다.'] : []),
      ...(analysisBundleStale ? ['최신 시장데이터는 반영됐지만, 현재 리포트는 이전 분석 결과입니다. 포트폴리오 분석을 다시 실행하면 새 기준으로 갱신됩니다.'] : []),
      ...userFacingFreshnessReasons,
      ...asArray(payload?.staleReasons).map(friendlyFreshnessReason),
      ...asArray(payload?.actionArtifactWarnings).map(safeKo),
      ...(!cacheEvidenceOk ? ['선택 포트폴리오 기준으로 저장된 분석 캐시를 찾지 못했습니다.'] : []),
      ...(!portfolioMatches ? ['선택한 포트폴리오와 저장된 분석 결과가 다를 수 있습니다.'] : []),
      ...(actionDiversityWarning ? [actionDiversityWarning] : []),
    ]),
  };
};
