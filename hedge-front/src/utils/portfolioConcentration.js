export const SINGLE_ASSET_WEIGHT_LIMIT_PCT = 50;

const toFiniteNumber = (value, fallback = 0) => {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
};

export const formatWeightPct = (value) => {
  const number = toFiniteNumber(value);
  return `${number.toFixed(Math.abs(number) >= 10 ? 1 : 2)}%`;
};

export const getPortfolioConcentrationSummary = (assets = [], limitPct = SINGLE_ASSET_WEIGHT_LIMIT_PCT) => {
  const normalizedAssets = (assets || [])
    .filter((asset) => asset && (asset.ticker || asset.name))
    .map((asset) => ({
      ...asset,
      ticker: asset.ticker || asset.name,
      weightPct: toFiniteNumber(asset.weightPct ?? asset.weight),
    }));
  const concentrated = normalizedAssets
    .filter((asset) => asset.weightPct > limitPct)
    .sort((a, b) => b.weightPct - a.weightPct);
  const assetCount = normalizedAssets.length;

  return {
    assetCount,
    concentrated,
    hasConcentration: concentrated.length > 0,
    blocksMultiAssetAnalysis: assetCount > 1 && concentrated.length > 0,
    isSingleAssetAnalysis: assetCount === 1 && concentrated.length > 0,
    topAsset: concentrated[0] || null,
    limitPct,
  };
};

export const getConcentrationLabel = (summary) => {
  if (!summary?.topAsset) return '';
  return `${summary.topAsset.ticker} ${formatWeightPct(summary.topAsset.weightPct)}`;
};
