export const MARKET_STATE_ASSET_GUIDE_EMPTY_MESSAGE = '현재 국면 기준으로 충분한 자산 민감도 데이터가 없습니다';

const PREFERRED_SOURCE_QUALITY = new Set(['market', 'direct_beta']);

const toNumber = (value, fallback = null) => {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
};

const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

const scenarioCode = (row) => String(row?.scenario_code || row?.code || row?.scenario || row?.nowcast_code || '').trim();

const scenarioLabel = (row) => (
  row?.scenario_name_ko
  || row?.scenario_name
  || row?.scenario_label_ko
  || row?.nowcast_name_ko
  || scenarioCode(row)
  || '시장국면'
);

const scoreCandidate = (row) => (
  toNumber(row?.final_score)
  ?? toNumber(row?.score)
  ?? toNumber(row?.activation_weight)
  ?? toNumber(row?.structured_score)
  ?? 0
);

const normalizeScenarioWeight = (row) => {
  const rawScore = scoreCandidate(row);
  if (!Number.isFinite(rawScore) || rawScore <= 0) return 0;
  return clamp(rawScore > 1 ? rawScore / 100 : rawScore, 0, 1);
};

const confidenceWeight = (row) => {
  const confidence = toNumber(row?.confidence, 0);
  return clamp(confidence / 100, 0, 1);
};

const normalizeTicker = (row) => String(row?.ticker || row?.asset_ticker || row?.symbol || row?.asset || '').trim().toUpperCase();

const preferredSourceRank = (sourceQuality) => (
  PREFERRED_SOURCE_QUALITY.has(String(sourceQuality || '').trim().toLowerCase()) ? 1 : 0
);

const uniqueScenarioRows = (dashboard = {}) => {
  const candidates = [
    ...(dashboard.topActiveScenarios || []),
    ...(dashboard.scenarioVectorLeaders || []),
    ...(dashboard.topMarketRows || []),
  ];
  const byCode = new Map();
  for (const row of candidates) {
    const code = scenarioCode(row);
    if (!code || byCode.has(code)) continue;
    const weight = normalizeScenarioWeight(row);
    if (weight <= 0) continue;
    byCode.set(code, {
      ...row,
      scenario_code: code,
      scenarioWeight: weight,
      scenarioLabel: scenarioLabel(row),
      rawScore: scoreCandidate(row),
    });
  }
  return [...byCode.values()]
    .sort((a, b) => b.scenarioWeight - a.scenarioWeight)
    .slice(0, 3);
};

const chooseRepresentative = (current, next) => {
  if (!current) return next;
  const currentRank = [
    Math.abs(current.finalAssetSignal),
    preferredSourceRank(current.row.source_quality),
    toNumber(current.row.confidence, 0),
  ];
  const nextRank = [
    Math.abs(next.finalAssetSignal),
    preferredSourceRank(next.row.source_quality),
    toNumber(next.row.confidence, 0),
  ];
  for (let index = 0; index < currentRank.length; index += 1) {
    if (nextRank[index] !== currentRank[index]) {
      return nextRank[index] > currentRank[index] ? next : current;
    }
  }
  return current;
};

const toDisplayItem = (asset) => {
  const representative = asset.representative || {};
  const row = representative.row || {};
  const confidence = asset.confidenceDenominator > 0
    ? asset.confidenceNumerator / asset.confidenceDenominator
    : null;
  return {
    ticker: asset.ticker,
    assetName: asset.assetName || asset.ticker,
    assetClass: asset.assetClass || '-',
    totalSignal: asset.totalSignal,
    representativeScenarioBeta: representative.scenarioBeta,
    maxAbsBeta: asset.maxAbsBeta,
    confidence,
    matchedScenarios: [...asset.matchedScenarios],
    matchedScenarioCodes: [...asset.matchedScenarioCodes],
    recommendedRole: row.recommended_role || '',
    notes: row.notes || '',
    sourceQuality: row.source_quality || '',
    preferredSourceRank: asset.preferredSourceRank,
    sourceRowCount: asset.sourceRowCount,
  };
};

const sortInterestAssets = (a, b) => (
  (a.totalSignal - b.totalSignal)
  || (Math.abs(b.totalSignal) - Math.abs(a.totalSignal))
  || ((b.confidence || 0) - (a.confidence || 0))
  || (b.preferredSourceRank - a.preferredSourceRank)
  || a.ticker.localeCompare(b.ticker)
);

const sortReduceAssets = (a, b) => (
  (b.totalSignal - a.totalSignal)
  || (Math.abs(b.totalSignal) - Math.abs(a.totalSignal))
  || ((b.confidence || 0) - (a.confidence || 0))
  || (b.preferredSourceRank - a.preferredSourceRank)
  || a.ticker.localeCompare(b.ticker)
);

export const buildMarketStateAssetGuide = (dashboard = {}, sensitivityPayload = {}) => {
  const activeScenarios = uniqueScenarioRows(dashboard);
  const sensitivityRows = Array.isArray(sensitivityPayload?.rows) ? sensitivityPayload.rows : [];
  if (!activeScenarios.length || !sensitivityRows.length) {
    return {
      activeScenarios,
      interestAssets: [],
      reduceAssets: [],
      matchedRowCount: 0,
      totalSensitivityRows: sensitivityRows.length,
      emptyMessage: MARKET_STATE_ASSET_GUIDE_EMPTY_MESSAGE,
    };
  }

  const scenarioByCode = new Map(activeScenarios.map((scenario) => [scenario.scenario_code, scenario]));
  const assets = new Map();
  let matchedRowCount = 0;

  for (const row of sensitivityRows) {
    const code = scenarioCode(row);
    const scenario = scenarioByCode.get(code);
    if (!scenario) continue;

    const ticker = normalizeTicker(row);
    const scenarioBeta = toNumber(row.scenario_beta ?? row.asset_scenario_beta ?? row.signed_sensitivity);
    if (!ticker || !Number.isFinite(scenarioBeta)) continue;

    const scenarioWeight = scenario.scenarioWeight;
    const assetScore = scenarioBeta * scenarioWeight;
    const finalAssetSignal = assetScore * confidenceWeight(row);
    if (!Number.isFinite(finalAssetSignal) || finalAssetSignal === 0) continue;

    matchedRowCount += 1;
    const contributionWeight = Math.abs(assetScore) || scenarioWeight || 1;
    const confidence = toNumber(row.confidence, 0);
    const sourceRank = preferredSourceRank(row.source_quality);
    const existing = assets.get(ticker) || {
      ticker,
      assetName: row.asset_name || row.asset_label || ticker,
      assetClass: row.asset_class || row.class || '',
      totalSignal: 0,
      maxAbsBeta: 0,
      confidenceNumerator: 0,
      confidenceDenominator: 0,
      matchedScenarios: new Set(),
      matchedScenarioCodes: new Set(),
      preferredSourceRank: 0,
      sourceRowCount: 0,
      representative: null,
    };

    existing.totalSignal += finalAssetSignal;
    existing.maxAbsBeta = Math.max(existing.maxAbsBeta, Math.abs(scenarioBeta));
    existing.confidenceNumerator += confidence * contributionWeight;
    existing.confidenceDenominator += contributionWeight;
    existing.matchedScenarios.add(scenario.scenarioLabel);
    existing.matchedScenarioCodes.add(code);
    existing.preferredSourceRank = Math.max(existing.preferredSourceRank, sourceRank);
    existing.sourceRowCount += 1;
    existing.assetName = existing.assetName || row.asset_name || ticker;
    existing.assetClass = existing.assetClass || row.asset_class || '';
    existing.representative = chooseRepresentative(existing.representative, {
      row,
      scenario,
      scenarioBeta,
      finalAssetSignal,
    });
    assets.set(ticker, existing);
  }

  const displayItems = [...assets.values()]
    .map(toDisplayItem)
    .filter((asset) => Number.isFinite(asset.totalSignal) && asset.totalSignal !== 0);
  const interestAssets = displayItems
    .filter((asset) => asset.totalSignal < 0)
    .sort(sortInterestAssets);
  const reduceAssets = displayItems
    .filter((asset) => asset.totalSignal > 0)
    .sort(sortReduceAssets);

  return {
    activeScenarios,
    interestAssets,
    reduceAssets,
    matchedRowCount,
    totalSensitivityRows: sensitivityRows.length,
    emptyMessage: interestAssets.length || reduceAssets.length ? '' : MARKET_STATE_ASSET_GUIDE_EMPTY_MESSAGE,
  };
};
