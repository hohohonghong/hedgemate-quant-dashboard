import math
import statistics
from collections import defaultdict


FX_TICKER = "KRW=X"
ENGINE_VERSION = "phase4_scenario_vector_v2"
MIN_TRUSTED_COVERAGE = 0.75
MIN_TRUSTED_CONFIDENCE = 40.0

BREADTH_ALL_20D = "__BREADTH_ALL_20D_POSITIVE__"
BREADTH_ALL_60D = "__BREADTH_ALL_60D_POSITIVE__"
BREADTH_ALL_ABOVE_200D = "__BREADTH_ALL_ABOVE_200D__"
BREADTH_US_STOCK_20D = "__BREADTH_US_STOCK_20D_POSITIVE__"
BREADTH_KR_STOCK_20D = "__BREADTH_KR_STOCK_20D_POSITIVE__"

AI_BASKET = "AI_BASKET"
KR_SEMIS_BASKET = "KR_SEMIS_BASKET"
KR_FINANCIAL_BASKET = "KR_FINANCIAL_BASKET"
KR_CONSTRUCTION_BASKET = "KR_CONSTRUCTION_BASKET"
KR_CREDIT_SPREAD = "KR_CREDIT_SPREAD_AA3Y_GOV3Y"
KR_CP_CD_SPREAD = "KR_CP_CD_SPREAD_91D"
KR_HOUSEHOLD_LOAN_YOY = "KR_HOUSEHOLD_LOAN_YOY"
GEOPOLITICAL_EVENT_OVERLAY = "GEOPOLITICAL_EVENT_OVERLAY"

MARKET_BREADTH_SERIES_SPECS = [
    {
        "ticker": BREADTH_ALL_20D,
        "label": "70-asset universe 20d positive breadth",
        "group": "all",
        "kind": "positive_return",
        "horizon": 20,
        "min_count": 20,
    },
    {
        "ticker": BREADTH_ALL_60D,
        "label": "70-asset universe 60d positive breadth",
        "group": "all",
        "kind": "positive_return",
        "horizon": 60,
        "min_count": 20,
    },
    {
        "ticker": BREADTH_ALL_ABOVE_200D,
        "label": "70-asset universe above 200d average breadth",
        "group": "all",
        "kind": "above_moving_average",
        "horizon": 200,
        "min_count": 20,
    },
    {
        "ticker": BREADTH_US_STOCK_20D,
        "label": "US stock 20d positive breadth",
        "group": "us_stock",
        "kind": "positive_return",
        "horizon": 20,
        "min_count": 8,
    },
    {
        "ticker": BREADTH_KR_STOCK_20D,
        "label": "Korea stock 20d positive breadth",
        "group": "kr_stock",
        "kind": "positive_return",
        "horizon": 20,
        "min_count": 8,
    },
]

SYNTHETIC_BASKET_SPECS = [
    {
        "ticker": AI_BASKET,
        "label": "AI leaders equal-weight basket",
        "currency": "USD",
        "role": "synthetic_basket",
        "members": ["NVDA", "AVGO", "AMD", "MSFT", "GOOGL"],
        "min_count": 3,
    },
    {
        "ticker": KR_SEMIS_BASKET,
        "label": "Korea semiconductors equal-weight basket",
        "currency": "KRW",
        "role": "synthetic_basket",
        "members": ["005930.KS", "000660.KS"],
        "min_count": 2,
    },
    {
        "ticker": KR_FINANCIAL_BASKET,
        "label": "Korea financials equal-weight basket",
        "currency": "KRW",
        "role": "synthetic_basket",
        "members": ["105560.KS", "055550.KS", "032830.KS"],
        "min_count": 2,
    },
    {
        "ticker": KR_CONSTRUCTION_BASKET,
        "label": "Korea construction/real-estate equal-weight basket",
        "currency": "KRW",
        "role": "synthetic_basket",
        "members": ["000720.KS", "006360.KS", "047040.KS"],
        "min_count": 2,
    },
]

LOW_FREQUENCY_INDICATOR_SPECS = [
    {
        "ticker": KR_CREDIT_SPREAD,
        "label": "Korea credit spread AA- 3Y minus Treasury 3Y",
        "currency": "KRW",
        "role": "external_credit",
        "frequency": "monthly",
        "max_staleness_days": 120,
    },
    {
        "ticker": KR_CP_CD_SPREAD,
        "label": "Korea CP 91D minus CD 91D spread",
        "currency": "KRW",
        "role": "external_money_market",
        "frequency": "monthly",
        "max_staleness_days": 90,
    },
    {
        "ticker": KR_HOUSEHOLD_LOAN_YOY,
        "label": "Korea household loan YoY growth",
        "currency": "KRW",
        "role": "external_household_credit",
        "frequency": "monthly",
        "max_staleness_days": 120,
    },
    {
        "ticker": GEOPOLITICAL_EVENT_OVERLAY,
        "label": "Geopolitical event overlay score",
        "currency": "USD",
        "role": "event_overlay",
        "frequency": "daily",
        "max_staleness_days": 14,
    },
]

MARKET_STATE_TICKER_SPECS = [
    {"ticker": FX_TICKER, "label": "USD/KRW", "currency": "KRW", "role": "fx"},
    {"ticker": "SPY", "label": "S&P 500", "currency": "USD", "role": "risk_asset"},
    {"ticker": "QQQ", "label": "Nasdaq 100", "currency": "USD", "role": "growth_asset"},
    {"ticker": "DIA", "label": "Dow Jones Industrial Average ETF", "currency": "USD", "role": "risk_asset"},
    {"ticker": "IWM", "label": "Russell 2000 ETF", "currency": "USD", "role": "small_cap"},
    {"ticker": "VTI", "label": "US Total Market ETF", "currency": "USD", "role": "risk_asset"},
    {"ticker": "EFA", "label": "Developed ex-US Equity ETF", "currency": "USD", "role": "global_equity"},
    {"ticker": "VXUS", "label": "Total International Stock ETF", "currency": "USD", "role": "global_equity"},
    {"ticker": "TLT", "label": "US Long Treasury", "currency": "USD", "role": "rates"},
    {"ticker": "IEF", "label": "US 7-10Y Treasury ETF", "currency": "USD", "role": "rates"},
    {"ticker": "SHY", "label": "US 1-3Y Treasury ETF", "currency": "USD", "role": "front_end_rates"},
    {"ticker": "HYG", "label": "US High Yield", "currency": "USD", "role": "credit"},
    {"ticker": "LQD", "label": "US Investment Grade Credit", "currency": "USD", "role": "credit"},
    {"ticker": "TIP", "label": "US TIPS", "currency": "USD", "role": "inflation"},
    {"ticker": "GLD", "label": "Gold", "currency": "USD", "role": "defensive"},
    {"ticker": "IAU", "label": "Gold mini ETF", "currency": "USD", "role": "defensive"},
    {"ticker": "DBC", "label": "Broad Commodities", "currency": "USD", "role": "commodity"},
    {"ticker": "USO", "label": "Oil", "currency": "USD", "role": "energy"},
    {"ticker": "XLE", "label": "US Energy Sector ETF", "currency": "USD", "role": "energy"},
    {"ticker": "XLP", "label": "US Consumer Staples Sector ETF", "currency": "USD", "role": "defensive_sector"},
    {"ticker": "XLU", "label": "US Utilities Sector ETF", "currency": "USD", "role": "defensive_sector"},
    {"ticker": "XLV", "label": "US Health Care Sector ETF", "currency": "USD", "role": "defensive_sector"},
    {"ticker": "EWY", "label": "Korea ETF", "currency": "USD", "role": "korea_equity"},
    {"ticker": "^KS200", "label": "KOSPI 200", "currency": "KRW", "role": "korea_equity"},
    {"ticker": "UUP", "label": "US Dollar ETF", "currency": "USD", "role": "dollar"},
    {"ticker": "FXI", "label": "China Large Cap", "currency": "USD", "role": "china_equity"},
    {"ticker": "SOXX", "label": "Semiconductor ETF", "currency": "USD", "role": "semiconductor"},
    {"ticker": "SMH", "label": "VanEck Semiconductor ETF", "currency": "USD", "role": "semiconductor"},
    {"ticker": "NVDA", "label": "NVIDIA", "currency": "USD", "role": "ai_leader"},
    {"ticker": "AVGO", "label": "Broadcom", "currency": "USD", "role": "ai_leader"},
    {"ticker": "AMD", "label": "Advanced Micro Devices", "currency": "USD", "role": "ai_leader"},
    {"ticker": "MSFT", "label": "Microsoft", "currency": "USD", "role": "ai_leader"},
    {"ticker": "GOOGL", "label": "Alphabet", "currency": "USD", "role": "ai_leader"},
    {"ticker": "005930.KS", "label": "Samsung Electronics", "currency": "KRW", "role": "korea_semiconductor"},
    {"ticker": "000660.KS", "label": "SK Hynix", "currency": "KRW", "role": "korea_semiconductor"},
    {"ticker": "105560.KS", "label": "KB Financial Group", "currency": "KRW", "role": "korea_financial"},
    {"ticker": "055550.KS", "label": "Shinhan Financial Group", "currency": "KRW", "role": "korea_financial"},
    {"ticker": "032830.KS", "label": "Samsung Life Insurance", "currency": "KRW", "role": "korea_financial"},
    {"ticker": "000720.KS", "label": "Hyundai Engineering & Construction", "currency": "KRW", "role": "korea_construction"},
    {"ticker": "006360.KS", "label": "GS Engineering & Construction", "currency": "KRW", "role": "korea_construction"},
    {"ticker": "047040.KS", "label": "Daewoo Engineering & Construction", "currency": "KRW", "role": "korea_construction"},
    {"ticker": "ITA", "label": "US Aerospace & Defense ETF", "currency": "USD", "role": "defense"},
    {"ticker": "PPA", "label": "US Aerospace & Defense ETF", "currency": "USD", "role": "defense"},
    {"ticker": "^VIX", "label": "VIX", "currency": "USD", "role": "volatility"},
]

SCENARIO_REGISTRY_FIELDS = [
    "scenario_code",
    "scenario_name",
    "scenario_name_ko",
    "lens",
    "related_lenses",
    "source_quality",
    "event_or_seed_dependent",
    "phase",
    "layer",
    "description",
    "market_interpretation_ko",
    "merged_concepts",
    "signal_count",
    "status_model",
    "is_favorable",
]

SCENARIO_FEATURE_FIELDS = [
    "date",
    "scenario_code",
    "scenario_name",
    "signal_name",
    "signal_label",
    "metric_type",
    "ticker",
    "reference_ticker",
    "lookback_days",
    "weight",
    "direction",
    "raw_value",
    "normalized_value",
    "aligned_value",
    "unit_score",
    "contribution",
]

SCENARIO_STATE_FIELDS = [
    "date",
    "scenario_code",
    "scenario_name",
    "scenario_name_ko",
    "lens",
    "related_lenses",
    "source_quality",
    "event_or_seed_dependent",
    "phase",
    "layer",
    "structured_score",
    "coverage_ratio",
    "breadth_score",
    "confidence",
    "raw_state",
    "display_state",
    "state_label",
    "top_positive_drivers",
    "top_negative_drivers",
    "market_interpretation_ko",
]

MARKET_FACTOR_FIELDS = [
    "date",
    "factor_code",
    "factor_name",
    "factor_group",
    "factor_polarity",
    "factor_score",
    "coverage_ratio",
    "breadth_score",
    "confidence",
    "factor_state",
    "interpretation",
]

SCENARIO_DRIVER_FIELDS = [
    "date",
    "scenario_code",
    "scenario_name",
    "driver_rank",
    "signal_name",
    "signal_label",
    "metric_type",
    "driver_effect",
    "contribution",
    "raw_value",
    "normalized_value",
    "aligned_value",
    "unit_score",
]

SCENARIO_VECTOR_FIELDS = [
    "as_of_date",
    "date",
    "scenario_code",
    "scenario_name",
    "scenario_name_ko",
    "lens",
    "related_lenses",
    "source_quality",
    "event_or_seed_dependent",
    "score",
    "raw_state",
    "display_state",
    "confidence",
    "coverage",
    "top_positive_drivers",
    "top_negative_drivers",
    "market_interpretation_ko",
    "engine_version",
]


SCENARIO_METADATA = {
    "soft_landing_goldilocks": {
        "scenario_name_ko": "우호적 위험선호장",
        "lens": "us_global",
        "related_lenses": ["korea_market"],
        "market_interpretation_ko": "성장은 버티고 물가 부담은 완화되어 미국/글로벌 위험자산과 성장자산에 우호적인 장세입니다. 한국장은 글로벌 위험선호의 수혜 여부를 별도 확인합니다.",
        "is_favorable": True,
    },
    "slowdown_recession_deflation_risk": {
        "scenario_name_ko": "경기둔화/침체 우려장",
        "lens": "us_global",
        "related_lenses": ["korea_market"],
        "market_interpretation_ko": "수요 둔화와 침체/디플레이션 압력이 커지는 방어적 장세입니다. 주식 beta와 신용위험을 보수적으로 봅니다.",
        "is_favorable": False,
    },
    "higher_for_longer_long_rate_shock": {
        "scenario_name_ko": "장기금리 부담장",
        "lens": "us_global",
        "related_lenses": ["korea_semiconductor", "fx_krw"],
        "market_interpretation_ko": "장기금리와 달러 강세 부담이 채권·성장주·신용자산을 압박하는 장세입니다. 고밸류 성장주와 반도체 factor 민감도를 점검합니다.",
        "is_favorable": False,
    },
    "stagflation_reinflation_energy_shock": {
        "scenario_name_ko": "물가·에너지 재상승장",
        "lens": "us_global",
        "related_lenses": ["fx_krw"],
        "market_interpretation_ko": "성장 부담이 있는데 유가·원자재·인플레이션 압력이 다시 커지는 장세입니다. 에너지/원자재 수혜와 장기채 부담을 함께 봅니다.",
        "is_favorable": False,
    },
    "usd_strength_krw_weakness": {
        "scenario_name_ko": "달러강세/원화약세장",
        "lens": "fx_krw",
        "related_lenses": ["korea_market"],
        "market_interpretation_ko": "달러가 강하고 원화가 약해져 KRW 기준 투자자의 환율 리스크가 커지는 장세입니다. 한국 자산과 USD 노출의 역할을 분리해 봅니다.",
        "is_favorable": False,
    },
    "acute_global_stress_liquidity_crunch": {
        "scenario_name_ko": "급성 리스크오프/유동성 경색장",
        "lens": "us_global",
        "related_lenses": ["korea_market", "fx_krw"],
        "market_interpretation_ko": "변동성이 튀고 위험자산이 동반 약세를 보이는 단기 스트레스 장세입니다. 상관관계 상승과 유동성 악화를 우선 점검합니다.",
        "is_favorable": False,
    },
    "china_trade_fragmentation_shock": {
        "scenario_name_ko": "중국·무역분절 충격장",
        "lens": "china_asia",
        "related_lenses": ["korea_market", "korea_semiconductor", "fx_krw"],
        "market_interpretation_ko": "중국 경기·무역갈등·공급망 충격이 한국/아시아와 반도체 자산에 번지는 장세입니다. 한국 반도체 factor와 원화 약세를 함께 확인합니다.",
        "is_favorable": False,
    },
    "semiconductor_ai_cycle_shock": {
        "scenario_name_ko": "AI·반도체 사이클 충격장",
        "lens": "korea_semiconductor",
        "related_lenses": ["us_global", "korea_market", "fx_krw"],
        "market_interpretation_ko": "AI capex 기대와 반도체 모멘텀이 꺾이면서 미국 성장주와 한국 반도체 대형주가 동시에 압박받는 장세입니다. SOXX, AI leader basket, 한국 반도체 basket의 동반 약세와 원화 압력을 함께 봅니다.",
        "is_favorable": False,
    },
    "korea_domestic_financial_stress": {
        "scenario_name_ko": "한국 내수 금융스트레스장",
        "lens": "korea_market",
        "related_lenses": ["fx_krw", "credit", "real_estate"],
        "market_interpretation_ko": "가계부채, 부동산 PF, 비은행권, 금융주와 건설주 스트레스가 한국 자산 전반으로 번지는 장세입니다. 금융/건설 basket, 신용 spread, 단기자금 spread, 원화 약세를 함께 점검합니다.",
        "is_favorable": False,
    },
    "geopolitical_escalation_supply_shock": {
        "scenario_name_ko": "지정학 확전·공급충격장",
        "lens": "geopolitical",
        "related_lenses": ["us_global", "korea_market", "fx_krw", "inflation"],
        "market_interpretation_ko": "전쟁, 제재, 해상로 차질, 대만·중동·한반도 긴장처럼 유가·금·방산·변동성이 동시에 움직이는 이벤트성 충격 장세입니다. 뉴스 overlay는 가격 신호를 보강하는 용도로만 해석합니다.",
        "is_favorable": False,
    },
}


SCENARIO_SOURCE_QUALITY_BY_CODE = {
    "korea_domestic_financial_stress": "seed",
    "geopolitical_escalation_supply_shock": "manual",
}

EVENT_OR_SEED_SOURCE_QUALITIES = {"seed", "manual", "fixture"}


def _scenario_definitions():
    return [
        {
            "scenario_code": "soft_landing_goldilocks",
            "scenario_name": "Soft Landing / Goldilocks",
            "phase": "V1",
            "layer": "macro_regime",
            "description": "Growth holds up while inflation cools.",
            "merged_concepts": "Base, normal market",
            "signals": [
                {"name": "spy_ret_20d", "label": "SPY 20d return", "metric": "ret_z", "ticker": "SPY", "lookback_days": 20, "weight": 0.30, "direction": "positive"},
                {"name": "qqq_ret_20d", "label": "QQQ 20d return", "metric": "ret_z", "ticker": "QQQ", "lookback_days": 20, "weight": 0.25, "direction": "positive"},
                {"name": "tlt_ret_20d", "label": "TLT 20d return", "metric": "ret_z", "ticker": "TLT", "lookback_days": 20, "weight": 0.15, "direction": "positive"},
                {"name": "uup_ret_20d", "label": "UUP 20d return", "metric": "ret_z", "ticker": "UUP", "lookback_days": 20, "weight": 0.15, "direction": "negative"},
                {"name": "usdkrw_ret_20d", "label": "USD/KRW 20d return", "metric": "ret_z", "ticker": FX_TICKER, "lookback_days": 20, "weight": 0.15, "direction": "negative"},
                {"name": "universe_breadth_20d", "label": "70-asset universe 20d breadth", "metric": "level_z", "ticker": BREADTH_ALL_20D, "lookback_days": 252, "weight": 0.10, "direction": "positive"},
                {"name": "us_stock_breadth_20d", "label": "US stock 20d breadth", "metric": "level_z", "ticker": BREADTH_US_STOCK_20D, "lookback_days": 252, "weight": 0.05, "direction": "positive"},
            ],
        },
        {
            "scenario_code": "slowdown_recession_deflation_risk",
            "scenario_name": "Slowdown / Recession / Deflation Risk",
            "phase": "V1",
            "layer": "macro_regime",
            "description": "Demand weakens and recession pressure builds.",
            "merged_concepts": "Growth slowdown, deflation",
            "signals": [
                {"name": "spy_ret_60d", "label": "SPY 60d return", "metric": "ret_z", "ticker": "SPY", "lookback_days": 60, "weight": 0.30, "direction": "negative"},
                {"name": "qqq_ret_60d", "label": "QQQ 60d return", "metric": "ret_z", "ticker": "QQQ", "lookback_days": 60, "weight": 0.15, "direction": "negative"},
                {"name": "tlt_ret_60d", "label": "TLT 60d return", "metric": "ret_z", "ticker": "TLT", "lookback_days": 60, "weight": 0.25, "direction": "positive"},
                {"name": "ief_ret_60d", "label": "IEF 60d return", "metric": "ret_z", "ticker": "IEF", "lookback_days": 60, "weight": 0.10, "direction": "positive"},
                {"name": "uso_ret_20d", "label": "USO 20d return", "metric": "ret_z", "ticker": "USO", "lookback_days": 20, "weight": 0.15, "direction": "negative"},
                {"name": "gld_ret_20d", "label": "GLD 20d return", "metric": "ret_z", "ticker": "GLD", "lookback_days": 20, "weight": 0.15, "direction": "positive"},
                {"name": "universe_breadth_60d", "label": "70-asset universe 60d breadth", "metric": "level_z", "ticker": BREADTH_ALL_60D, "lookback_days": 252, "weight": 0.10, "direction": "negative"},
            ],
        },
        {
            "scenario_code": "higher_for_longer_long_rate_shock",
            "scenario_name": "Higher-for-Longer / Long-Rate Shock",
            "phase": "V1",
            "layer": "market_expression",
            "description": "Long rates and policy burden pressure asset prices.",
            "merged_concepts": "Rate shock, fiscal premium",
            "signals": [
                {"name": "tlt_ret_20d", "label": "TLT 20d return", "metric": "ret_z", "ticker": "TLT", "lookback_days": 20, "weight": 0.35, "direction": "negative"},
                {"name": "tlt_vs_shy_20d", "label": "TLT minus SHY 20d return", "metric": "relative_ret_z", "ticker": "TLT", "reference_ticker": "SHY", "lookback_days": 20, "weight": 0.15, "direction": "negative"},
                {"name": "qqq_ret_20d", "label": "QQQ 20d return", "metric": "ret_z", "ticker": "QQQ", "lookback_days": 20, "weight": 0.20, "direction": "negative"},
                {"name": "hyg_ret_20d", "label": "HYG 20d return", "metric": "ret_z", "ticker": "HYG", "lookback_days": 20, "weight": 0.15, "direction": "negative"},
                {"name": "lqd_ret_20d", "label": "LQD 20d return", "metric": "ret_z", "ticker": "LQD", "lookback_days": 20, "weight": 0.10, "direction": "negative"},
                {"name": "uup_ret_20d", "label": "UUP 20d return", "metric": "ret_z", "ticker": "UUP", "lookback_days": 20, "weight": 0.15, "direction": "positive"},
                {"name": "usdkrw_ret_20d", "label": "USD/KRW 20d return", "metric": "ret_z", "ticker": FX_TICKER, "lookback_days": 20, "weight": 0.15, "direction": "positive"},
            ],
        },
        {
            "scenario_code": "stagflation_reinflation_energy_shock",
            "scenario_name": "Stagflation / Reinflation / Energy Shock",
            "phase": "V1",
            "layer": "macro_regime",
            "description": "Growth is weak while inflation and commodities rise again.",
            "merged_concepts": "Reinflation, oil spike, commodity spike",
            "signals": [
                {"name": "uso_ret_20d", "label": "USO 20d return", "metric": "ret_z", "ticker": "USO", "lookback_days": 20, "weight": 0.30, "direction": "positive"},
                {"name": "dbc_ret_20d", "label": "DBC 20d return", "metric": "ret_z", "ticker": "DBC", "lookback_days": 20, "weight": 0.20, "direction": "positive"},
                {"name": "xle_ret_20d", "label": "XLE 20d return", "metric": "ret_z", "ticker": "XLE", "lookback_days": 20, "weight": 0.10, "direction": "positive"},
                {"name": "tip_ret_20d", "label": "TIP 20d return", "metric": "ret_z", "ticker": "TIP", "lookback_days": 20, "weight": 0.15, "direction": "positive"},
                {"name": "tlt_ret_20d", "label": "TLT 20d return", "metric": "ret_z", "ticker": "TLT", "lookback_days": 20, "weight": 0.20, "direction": "negative"},
                {"name": "spy_ret_20d", "label": "SPY 20d return", "metric": "ret_z", "ticker": "SPY", "lookback_days": 20, "weight": 0.15, "direction": "negative"},
            ],
        },
        {
            "scenario_code": "usd_strength_krw_weakness",
            "scenario_name": "USD Strength / KRW Weakness",
            "phase": "V1",
            "layer": "market_expression",
            "description": "Dollar strength and won weakness dominate the tape.",
            "merged_concepts": "Won weakness, dollar strength",
            "signals": [
                {"name": "usdkrw_level_z", "label": "USD/KRW level", "metric": "level_z", "ticker": FX_TICKER, "lookback_days": 252, "weight": 0.30, "direction": "positive"},
                {"name": "usdkrw_ret_20d", "label": "USD/KRW 20d return", "metric": "ret_z", "ticker": FX_TICKER, "lookback_days": 20, "weight": 0.25, "direction": "positive"},
                {"name": "uup_ret_20d", "label": "UUP 20d return", "metric": "ret_z", "ticker": "UUP", "lookback_days": 20, "weight": 0.15, "direction": "positive"},
                {"name": "ewy_vs_spy_20d", "label": "EWY minus SPY 20d return", "metric": "relative_ret_z", "ticker": "EWY", "reference_ticker": "SPY", "lookback_days": 20, "weight": 0.15, "direction": "negative"},
                {"name": "ks200_ret_20d", "label": "KOSPI 200 20d return", "metric": "ret_z", "ticker": "^KS200", "lookback_days": 20, "weight": 0.10, "direction": "negative"},
                {"name": "kr_stock_breadth_20d", "label": "Korea stock 20d breadth", "metric": "level_z", "ticker": BREADTH_KR_STOCK_20D, "lookback_days": 252, "weight": 0.05, "direction": "negative"},
                {"name": "fxi_ret_20d", "label": "FXI 20d return", "metric": "ret_z", "ticker": "FXI", "lookback_days": 20, "weight": 0.15, "direction": "negative"},
            ],
        },
        {
            "scenario_code": "acute_global_stress_liquidity_crunch",
            "scenario_name": "Acute Global Stress / Liquidity Crunch",
            "phase": "V1",
            "layer": "market_expression",
            "description": "Cross-asset correlations converge during an acute stress event.",
            "merged_concepts": "GFC or COVID type shock",
            "signals": [
                {"name": "vix_level_z", "label": "VIX level", "metric": "level_z", "ticker": "^VIX", "lookback_days": 252, "weight": 0.30, "direction": "positive"},
                {"name": "spy_ret_5d", "label": "SPY 5d return", "metric": "ret_z", "ticker": "SPY", "lookback_days": 5, "weight": 0.20, "direction": "negative"},
                {"name": "qqq_ret_5d", "label": "QQQ 5d return", "metric": "ret_z", "ticker": "QQQ", "lookback_days": 5, "weight": 0.15, "direction": "negative"},
                {"name": "hyg_ret_5d", "label": "HYG 5d return", "metric": "ret_z", "ticker": "HYG", "lookback_days": 5, "weight": 0.15, "direction": "negative"},
                {"name": "lqd_ret_5d", "label": "LQD 5d return", "metric": "ret_z", "ticker": "LQD", "lookback_days": 5, "weight": 0.10, "direction": "negative"},
                {"name": "universe_breadth_20d", "label": "70-asset universe 20d breadth", "metric": "level_z", "ticker": BREADTH_ALL_20D, "lookback_days": 252, "weight": 0.10, "direction": "negative"},
                {"name": "gld_ret_5d", "label": "GLD 5d return", "metric": "ret_z", "ticker": "GLD", "lookback_days": 5, "weight": 0.10, "direction": "positive"},
                {"name": "tlt_ret_5d", "label": "TLT 5d return", "metric": "ret_z", "ticker": "TLT", "lookback_days": 5, "weight": 0.10, "direction": "positive"},
            ],
        },
        {
            "scenario_code": "china_trade_fragmentation_shock",
            "scenario_name": "China / Trade Fragmentation Shock",
            "phase": "V1",
            "layer": "shock_driver",
            "description": "China weakness and trade fragmentation spill into Asia.",
            "merged_concepts": "China slowdown, tariff or fragmentation shock",
            "signals": [
                {"name": "fxi_ret_20d", "label": "FXI 20d return", "metric": "ret_z", "ticker": "FXI", "lookback_days": 20, "weight": 0.30, "direction": "negative"},
                {"name": "ewy_ret_20d", "label": "EWY 20d return", "metric": "ret_z", "ticker": "EWY", "lookback_days": 20, "weight": 0.15, "direction": "negative"},
                {"name": "ks200_ret_20d", "label": "KOSPI 200 20d return", "metric": "ret_z", "ticker": "^KS200", "lookback_days": 20, "weight": 0.10, "direction": "negative"},
                {"name": "kr_stock_breadth_20d", "label": "Korea stock 20d breadth", "metric": "level_z", "ticker": BREADTH_KR_STOCK_20D, "lookback_days": 252, "weight": 0.10, "direction": "negative"},
                {"name": "soxx_ret_20d", "label": "SOXX 20d return", "metric": "ret_z", "ticker": "SOXX", "lookback_days": 20, "weight": 0.20, "direction": "negative"},
                {"name": "usdkrw_ret_20d", "label": "USD/KRW 20d return", "metric": "ret_z", "ticker": FX_TICKER, "lookback_days": 20, "weight": 0.15, "direction": "positive"},
                {"name": "uup_ret_20d", "label": "UUP 20d return", "metric": "ret_z", "ticker": "UUP", "lookback_days": 20, "weight": 0.10, "direction": "positive"},
                {"name": "fxi_vs_spy_20d", "label": "FXI minus SPY 20d return", "metric": "relative_ret_z", "ticker": "FXI", "reference_ticker": "SPY", "lookback_days": 20, "weight": 0.10, "direction": "negative"},
            ],
        },
        {
            "scenario_code": "semiconductor_ai_cycle_shock",
            "scenario_name": "Semiconductor / AI Cycle Shock",
            "phase": "V2",
            "layer": "shock_driver",
            "description": "AI capex and semiconductor momentum roll over together.",
            "merged_concepts": "AI capex disappointment, semiconductor de-rating, Korea growth shock",
            "signals": [
                {"name": "soxx_ret_20d", "label": "SOXX 20d return", "metric": "ret_z", "ticker": "SOXX", "lookback_days": 20, "weight": 0.25, "direction": "negative"},
                {"name": "soxx_vs_spy_20d", "label": "SOXX minus SPY 20d return", "metric": "relative_ret_z", "ticker": "SOXX", "reference_ticker": "SPY", "lookback_days": 20, "weight": 0.20, "direction": "negative"},
                {"name": "ai_leader_basket_ret_20d", "label": "AI leaders basket 20d return", "metric": "ret_z", "ticker": AI_BASKET, "lookback_days": 20, "weight": 0.15, "direction": "negative"},
                {"name": "kr_semis_basket_ret_20d", "label": "Korea semis basket 20d return", "metric": "ret_z", "ticker": KR_SEMIS_BASKET, "lookback_days": 20, "weight": 0.15, "direction": "negative"},
                {"name": "kr_semis_vs_ks200_20d", "label": "Korea semis basket minus KOSPI 200 20d return", "metric": "relative_ret_z", "ticker": KR_SEMIS_BASKET, "reference_ticker": "^KS200", "lookback_days": 20, "weight": 0.10, "direction": "negative"},
                {"name": "usdkrw_ret_20d", "label": "USD/KRW 20d return", "metric": "ret_z", "ticker": FX_TICKER, "lookback_days": 20, "weight": 0.10, "direction": "positive"},
                {"name": "vix_level_z", "label": "VIX level", "metric": "level_z", "ticker": "^VIX", "lookback_days": 252, "weight": 0.05, "direction": "positive"},
            ],
        },
        {
            "scenario_code": "korea_domestic_financial_stress",
            "scenario_name": "Korea Domestic Financial Stress",
            "phase": "V2",
            "layer": "shock_driver",
            "description": "Korea household debt, real estate PF, non-bank, financial, and construction stress rise together.",
            "merged_concepts": "Korea credit spread, PF stress, construction stress, won weakness",
            "signals": [
                {"name": "kr_financial_basket_ret_20d", "label": "Korea financials basket 20d return", "metric": "ret_z", "ticker": KR_FINANCIAL_BASKET, "lookback_days": 20, "weight": 0.20, "direction": "negative"},
                {"name": "kr_construction_basket_ret_20d", "label": "Korea construction basket 20d return", "metric": "ret_z", "ticker": KR_CONSTRUCTION_BASKET, "lookback_days": 20, "weight": 0.15, "direction": "negative"},
                {"name": "kr_credit_spread_level_z", "label": "Korea AA- 3Y credit spread", "metric": "level_z", "ticker": KR_CREDIT_SPREAD, "lookback_days": 252, "weight": 0.20, "direction": "positive"},
                {"name": "kr_cp_cd_spread_level_z", "label": "Korea CP-CD 91D spread", "metric": "level_z", "ticker": KR_CP_CD_SPREAD, "lookback_days": 252, "weight": 0.10, "direction": "positive"},
                {"name": "ks200_ret_20d", "label": "KOSPI 200 20d return", "metric": "ret_z", "ticker": "^KS200", "lookback_days": 20, "weight": 0.10, "direction": "negative"},
                {"name": "ewy_vs_spy_20d", "label": "EWY minus SPY 20d return", "metric": "relative_ret_z", "ticker": "EWY", "reference_ticker": "SPY", "lookback_days": 20, "weight": 0.10, "direction": "negative"},
                {"name": "usdkrw_ret_20d", "label": "USD/KRW 20d return", "metric": "ret_z", "ticker": FX_TICKER, "lookback_days": 20, "weight": 0.10, "direction": "positive"},
                {"name": "household_loan_yoy_z", "label": "Korea household loan YoY growth", "metric": "level_z", "ticker": KR_HOUSEHOLD_LOAN_YOY, "lookback_days": 252, "weight": 0.05, "direction": "positive"},
            ],
        },
        {
            "scenario_code": "geopolitical_escalation_supply_shock",
            "scenario_name": "Geopolitical Escalation / Supply Shock",
            "phase": "V2",
            "layer": "event_shock",
            "description": "War, sanctions, shipping disruption, or regional escalation lift oil, gold, defense, volatility, and the dollar.",
            "merged_concepts": "Geopolitical escalation, supply shock, oil/gold/defense bid",
            "signals": [
                {"name": "uso_ret_5d", "label": "USO 5d return", "metric": "ret_z", "ticker": "USO", "lookback_days": 5, "weight": 0.20, "direction": "positive"},
                {"name": "dbc_ret_20d", "label": "DBC 20d return", "metric": "ret_z", "ticker": "DBC", "lookback_days": 20, "weight": 0.10, "direction": "positive"},
                {"name": "gld_ret_5d", "label": "GLD 5d return", "metric": "ret_z", "ticker": "GLD", "lookback_days": 5, "weight": 0.15, "direction": "positive"},
                {"name": "ppa_vs_spy_20d", "label": "PPA minus SPY 20d return", "metric": "relative_ret_z", "ticker": "PPA", "reference_ticker": "SPY", "lookback_days": 20, "weight": 0.15, "direction": "positive"},
                {"name": "vix_level_z", "label": "VIX level", "metric": "level_z", "ticker": "^VIX", "lookback_days": 252, "weight": 0.15, "direction": "positive"},
                {"name": "usdkrw_ret_20d", "label": "USD/KRW 20d return", "metric": "ret_z", "ticker": FX_TICKER, "lookback_days": 20, "weight": 0.10, "direction": "positive"},
                {"name": "spy_ret_5d", "label": "SPY 5d return", "metric": "ret_z", "ticker": "SPY", "lookback_days": 5, "weight": 0.10, "direction": "negative"},
                {"name": "event_overlay_score", "label": "Geopolitical event overlay score", "metric": "bounded_score", "ticker": GEOPOLITICAL_EVENT_OVERLAY, "lookback_days": 252, "weight": 0.05, "direction": "positive"},
            ],
        },
    ]


def build_scenario_registry_rows():
    rows = []
    for scenario in _scenario_definitions():
        metadata = _scenario_metadata(scenario["scenario_code"])
        source_quality = _scenario_source_quality(scenario["scenario_code"], metadata)
        rows.append(
            {
                "scenario_code": scenario["scenario_code"],
                "scenario_name": scenario["scenario_name"],
                "scenario_name_ko": metadata.get("scenario_name_ko", ""),
                "lens": metadata.get("lens", "us_global"),
                "related_lenses": _scenario_related_lenses_text(metadata),
                "source_quality": source_quality,
                "event_or_seed_dependent": _scenario_event_or_seed_dependent(source_quality),
                "phase": scenario["phase"],
                "layer": scenario["layer"],
                "description": scenario["description"],
                "market_interpretation_ko": metadata.get("market_interpretation_ko", ""),
                "merged_concepts": scenario["merged_concepts"],
                "signal_count": len(scenario["signals"]),
                "status_model": "OFF/WATCH/ACTIVE/STRESS",
                "is_favorable": "Y" if metadata.get("is_favorable") else "N",
            }
        )
    return rows


def _market_factor_definitions():
    return [
        {
            "factor_code": "growth_risk_appetite",
            "factor_name": "Growth / Risk Appetite",
            "factor_group": "risk_sentiment",
            "factor_polarity": "positive",
            "interpretation": "주식·신용·시장 breadth가 함께 좋아지는지 확인합니다.",
            "signals": [
                {"name": "spy_ret_20d", "label": "SPY 20d return", "metric": "ret_z", "ticker": "SPY", "lookback_days": 20, "weight": 0.20, "direction": "positive"},
                {"name": "qqq_ret_20d", "label": "QQQ 20d return", "metric": "ret_z", "ticker": "QQQ", "lookback_days": 20, "weight": 0.15, "direction": "positive"},
                {"name": "hyg_ret_20d", "label": "HYG 20d return", "metric": "ret_z", "ticker": "HYG", "lookback_days": 20, "weight": 0.15, "direction": "positive"},
                {"name": "vix_level_z", "label": "VIX level", "metric": "level_z", "ticker": "^VIX", "lookback_days": 252, "weight": 0.15, "direction": "negative"},
                {"name": "universe_breadth_20d", "label": "70-asset universe 20d breadth", "metric": "level_z", "ticker": BREADTH_ALL_20D, "lookback_days": 252, "weight": 0.20, "direction": "positive"},
                {"name": "us_stock_breadth_20d", "label": "US stock 20d breadth", "metric": "level_z", "ticker": BREADTH_US_STOCK_20D, "lookback_days": 252, "weight": 0.15, "direction": "positive"},
            ],
        },
        {
            "factor_code": "rates_pressure",
            "factor_name": "Rates Pressure",
            "factor_group": "rates",
            "factor_polarity": "risk",
            "interpretation": "장기채·중기채 가격 하락과 장단기 구간 부담을 통해 금리 압박을 봅니다.",
            "signals": [
                {"name": "tlt_ret_20d", "label": "TLT 20d return", "metric": "ret_z", "ticker": "TLT", "lookback_days": 20, "weight": 0.30, "direction": "negative"},
                {"name": "ief_ret_20d", "label": "IEF 20d return", "metric": "ret_z", "ticker": "IEF", "lookback_days": 20, "weight": 0.25, "direction": "negative"},
                {"name": "tlt_vs_shy_20d", "label": "TLT minus SHY 20d return", "metric": "relative_ret_z", "ticker": "TLT", "reference_ticker": "SHY", "lookback_days": 20, "weight": 0.25, "direction": "negative"},
                {"name": "qqq_ret_20d", "label": "QQQ 20d return", "metric": "ret_z", "ticker": "QQQ", "lookback_days": 20, "weight": 0.20, "direction": "negative"},
            ],
        },
        {
            "factor_code": "credit_stress",
            "factor_name": "Credit Stress",
            "factor_group": "credit",
            "factor_polarity": "risk",
            "interpretation": "하이일드·투자등급 신용자산과 변동성으로 스트레스 확산 여부를 봅니다.",
            "signals": [
                {"name": "hyg_ret_20d", "label": "HYG 20d return", "metric": "ret_z", "ticker": "HYG", "lookback_days": 20, "weight": 0.30, "direction": "negative"},
                {"name": "lqd_ret_20d", "label": "LQD 20d return", "metric": "ret_z", "ticker": "LQD", "lookback_days": 20, "weight": 0.25, "direction": "negative"},
                {"name": "hyg_vs_shy_20d", "label": "HYG minus SHY 20d return", "metric": "relative_ret_z", "ticker": "HYG", "reference_ticker": "SHY", "lookback_days": 20, "weight": 0.25, "direction": "negative"},
                {"name": "vix_level_z", "label": "VIX level", "metric": "level_z", "ticker": "^VIX", "lookback_days": 252, "weight": 0.20, "direction": "positive"},
            ],
        },
        {
            "factor_code": "inflation_commodity_pressure",
            "factor_name": "Inflation / Commodity Pressure",
            "factor_group": "inflation",
            "factor_polarity": "risk",
            "interpretation": "유가·원자재·에너지 섹터와 물가연동채 반응으로 재인플레 압력을 봅니다.",
            "signals": [
                {"name": "uso_ret_20d", "label": "USO 20d return", "metric": "ret_z", "ticker": "USO", "lookback_days": 20, "weight": 0.25, "direction": "positive"},
                {"name": "dbc_ret_20d", "label": "DBC 20d return", "metric": "ret_z", "ticker": "DBC", "lookback_days": 20, "weight": 0.25, "direction": "positive"},
                {"name": "xle_ret_20d", "label": "XLE 20d return", "metric": "ret_z", "ticker": "XLE", "lookback_days": 20, "weight": 0.20, "direction": "positive"},
                {"name": "tip_ret_20d", "label": "TIP 20d return", "metric": "ret_z", "ticker": "TIP", "lookback_days": 20, "weight": 0.15, "direction": "positive"},
                {"name": "tlt_ret_20d", "label": "TLT 20d return", "metric": "ret_z", "ticker": "TLT", "lookback_days": 20, "weight": 0.15, "direction": "negative"},
            ],
        },
        {
            "factor_code": "usd_krw_pressure",
            "factor_name": "USD / KRW Pressure",
            "factor_group": "fx",
            "factor_polarity": "risk",
            "interpretation": "달러 강세와 원화 약세가 한국 투자자 관점의 리스크로 작동하는지 봅니다.",
            "signals": [
                {"name": "usdkrw_level_z", "label": "USD/KRW level", "metric": "level_z", "ticker": FX_TICKER, "lookback_days": 252, "weight": 0.25, "direction": "positive"},
                {"name": "usdkrw_ret_20d", "label": "USD/KRW 20d return", "metric": "ret_z", "ticker": FX_TICKER, "lookback_days": 20, "weight": 0.25, "direction": "positive"},
                {"name": "uup_ret_20d", "label": "UUP 20d return", "metric": "ret_z", "ticker": "UUP", "lookback_days": 20, "weight": 0.20, "direction": "positive"},
                {"name": "ewy_vs_spy_20d", "label": "EWY minus SPY 20d return", "metric": "relative_ret_z", "ticker": "EWY", "reference_ticker": "SPY", "lookback_days": 20, "weight": 0.15, "direction": "negative"},
                {"name": "ks200_ret_20d", "label": "KOSPI 200 20d return", "metric": "ret_z", "ticker": "^KS200", "lookback_days": 20, "weight": 0.15, "direction": "negative"},
            ],
        },
        {
            "factor_code": "korea_market_health",
            "factor_name": "Korea Market Health",
            "factor_group": "korea",
            "factor_polarity": "positive",
            "interpretation": "한국 지수·EWY·국내 종목 breadth가 글로벌 위험선호와 같이 개선되는지 봅니다.",
            "signals": [
                {"name": "ewy_ret_20d", "label": "EWY 20d return", "metric": "ret_z", "ticker": "EWY", "lookback_days": 20, "weight": 0.25, "direction": "positive"},
                {"name": "ks200_ret_20d", "label": "KOSPI 200 20d return", "metric": "ret_z", "ticker": "^KS200", "lookback_days": 20, "weight": 0.25, "direction": "positive"},
                {"name": "kr_stock_breadth_20d", "label": "Korea stock 20d breadth", "metric": "level_z", "ticker": BREADTH_KR_STOCK_20D, "lookback_days": 252, "weight": 0.25, "direction": "positive"},
                {"name": "ewy_vs_spy_20d", "label": "EWY minus SPY 20d return", "metric": "relative_ret_z", "ticker": "EWY", "reference_ticker": "SPY", "lookback_days": 20, "weight": 0.15, "direction": "positive"},
                {"name": "usdkrw_ret_20d", "label": "USD/KRW 20d return", "metric": "ret_z", "ticker": FX_TICKER, "lookback_days": 20, "weight": 0.10, "direction": "negative"},
            ],
        },
        {
            "factor_code": "global_breadth_health",
            "factor_name": "Global Breadth Health",
            "factor_group": "breadth",
            "factor_polarity": "positive",
            "interpretation": "70개 자산 상승 확산도와 중기 추세 확산도로 랠리의 폭을 확인합니다.",
            "signals": [
                {"name": "universe_breadth_20d", "label": "70-asset universe 20d breadth", "metric": "level_z", "ticker": BREADTH_ALL_20D, "lookback_days": 252, "weight": 0.30, "direction": "positive"},
                {"name": "universe_breadth_60d", "label": "70-asset universe 60d breadth", "metric": "level_z", "ticker": BREADTH_ALL_60D, "lookback_days": 252, "weight": 0.25, "direction": "positive"},
                {"name": "universe_above_200d", "label": "70-asset universe above 200d average", "metric": "level_z", "ticker": BREADTH_ALL_ABOVE_200D, "lookback_days": 252, "weight": 0.20, "direction": "positive"},
                {"name": "us_stock_breadth_20d", "label": "US stock 20d breadth", "metric": "level_z", "ticker": BREADTH_US_STOCK_20D, "lookback_days": 252, "weight": 0.15, "direction": "positive"},
                {"name": "kr_stock_breadth_20d", "label": "Korea stock 20d breadth", "metric": "level_z", "ticker": BREADTH_KR_STOCK_20D, "lookback_days": 252, "weight": 0.10, "direction": "positive"},
            ],
        },
        {
            "factor_code": "defensive_rotation",
            "factor_name": "Defensive Rotation",
            "factor_group": "style_rotation",
            "factor_polarity": "risk",
            "interpretation": "방어 섹터 상대강도와 소형주/breadth 약세로 방어적 회전을 확인합니다.",
            "signals": [
                {"name": "xlp_vs_spy_20d", "label": "XLP minus SPY 20d return", "metric": "relative_ret_z", "ticker": "XLP", "reference_ticker": "SPY", "lookback_days": 20, "weight": 0.25, "direction": "positive"},
                {"name": "xlu_vs_spy_20d", "label": "XLU minus SPY 20d return", "metric": "relative_ret_z", "ticker": "XLU", "reference_ticker": "SPY", "lookback_days": 20, "weight": 0.20, "direction": "positive"},
                {"name": "xlv_vs_spy_20d", "label": "XLV minus SPY 20d return", "metric": "relative_ret_z", "ticker": "XLV", "reference_ticker": "SPY", "lookback_days": 20, "weight": 0.20, "direction": "positive"},
                {"name": "iwm_ret_20d", "label": "IWM 20d return", "metric": "ret_z", "ticker": "IWM", "lookback_days": 20, "weight": 0.20, "direction": "negative"},
                {"name": "universe_breadth_20d", "label": "70-asset universe 20d breadth", "metric": "level_z", "ticker": BREADTH_ALL_20D, "lookback_days": 252, "weight": 0.15, "direction": "negative"},
            ],
        },
    ]


def _mean(values):
    return sum(values) / len(values) if values else None


def _stdev(values):
    if len(values) < 2:
        return None
    return statistics.stdev(values)


def _clip01(value):
    return max(0.0, min(1.0, value))


def _scenario_metadata(scenario_code):
    return SCENARIO_METADATA.get(
        scenario_code,
        {
            "scenario_name_ko": "",
            "lens": "us_global",
            "related_lenses": [],
            "market_interpretation_ko": "",
            "is_favorable": False,
            "source_quality": "market",
        },
    )


def _scenario_source_quality(scenario_code, metadata=None):
    metadata = metadata or _scenario_metadata(scenario_code)
    return (
        metadata.get("source_quality")
        or SCENARIO_SOURCE_QUALITY_BY_CODE.get(scenario_code)
        or "market"
    )


def _scenario_event_or_seed_dependent(source_quality):
    return "Y" if str(source_quality or "").lower() in EVENT_OR_SEED_SOURCE_QUALITIES else "N"


def _scenario_related_lenses_text(metadata):
    return "|".join(metadata.get("related_lenses") or [])


def _is_trusted_state(row):
    return (
        row.get("coverage_ratio", 0.0) >= MIN_TRUSTED_COVERAGE
        and row.get("confidence", 0.0) >= MIN_TRUSTED_CONFIDENCE
    )


def scenario_display_state(row):
    """Return user-facing scenario state without mutating the raw model label."""
    raw_state = row.get("raw_state") or row.get("state_label") or "OFF"
    if raw_state == "OFF":
        return "OFF"
    if not _is_trusted_state(row):
        return "PROVISIONAL"
    metadata = _scenario_metadata(row.get("scenario_code"))
    if metadata.get("is_favorable") and raw_state == "STRESS":
        return "STRONG"
    return raw_state


def _enrich_scenario_row(row, scenario_code):
    metadata = _scenario_metadata(scenario_code)
    source_quality = _scenario_source_quality(scenario_code, metadata)
    row["scenario_name_ko"] = metadata.get("scenario_name_ko", "")
    row["lens"] = metadata.get("lens", "us_global")
    row["related_lenses"] = _scenario_related_lenses_text(metadata)
    row["source_quality"] = source_quality
    row["event_or_seed_dependent"] = _scenario_event_or_seed_dependent(source_quality)
    row["market_interpretation_ko"] = metadata.get("market_interpretation_ko", "")
    return row


def _rolling_zscore_map(raw_map, window=252, min_obs=60):
    dates = sorted(raw_map.keys())
    values = []
    out = {}
    for date_str in dates:
        value = raw_map[date_str]
        history = values[-window:]
        if len(history) < min_obs:
            values.append(value)
            continue
        sigma = _stdev(history)
        if sigma in (None, 0):
            out[date_str] = 0.0
            values.append(value)
            continue
        out[date_str] = (value - _mean(history)) / sigma
        values.append(value)
    return out


def _horizon_return_map(series, horizon):
    out = {}
    for idx in range(horizon, len(series)):
        date_str, price = series[idx]
        _, prev = series[idx - horizon]
        if prev is None or prev <= 0 or price is None or price <= 0:
            continue
        out[date_str] = price / prev - 1.0
    return out


def _level_map(series):
    return {date_str: price for date_str, price in series if price is not None and price > 0}


def _relative_return_map(left_series, right_series, horizon):
    left_ret = _horizon_return_map(left_series, horizon)
    right_ret = _horizon_return_map(right_series, horizon)
    common_dates = sorted(set(left_ret.keys()) & set(right_ret.keys()))
    return {date_str: left_ret[date_str] - right_ret[date_str] for date_str in common_dates}


def _aligned_unit(normalized_value, direction):
    if normalized_value is None:
        return None, None
    if direction not in {"positive", "negative"}:
        raise ValueError(f"Unsupported signal direction: {direction}")
    sign = 1.0 if direction == "positive" else -1.0
    aligned_value = normalized_value * sign
    unit_score = _clip01((aligned_value + 2.0) / 4.0)
    return aligned_value, unit_score


def _confidence_label(confidence):
    if confidence >= 70:
        return "높음"
    if confidence >= 50:
        return "중간"
    if confidence >= 35:
        return "낮음"
    return "매우 낮음"


def _coverage_label(coverage_ratio):
    if coverage_ratio >= 0.85:
        return "충분"
    if coverage_ratio >= 0.65:
        return "보통"
    return "부족"


def _state_explanation(state_label):
    return {
        "STRONG": "신뢰 가능한 강한 우호 구간입니다. 다만 방어 필요성이 완전히 사라졌다는 뜻은 아닙니다.",
        "PROVISIONAL": "데이터 coverage/confidence가 충분하지 않아 임시 신호로만 봐야 합니다.",
        "STRESS": "강한 스트레스 구간입니다. 단기 리스크 해석을 보수적으로 봐야 합니다.",
        "ACTIVE": "활성 구간입니다. 현재 시장을 설명하는 주요 상태로 볼 수 있습니다.",
        "WATCH": "관찰 구간입니다. 아직 강한 상태는 아니지만 변화 가능성이 있습니다.",
        "OFF": "비활성 구간입니다. 현재 핵심 설명 상태로 보기는 어렵습니다.",
    }.get(state_label, "상태 해석이 정의되지 않았습니다.")


def _scenario_user_implication(scenario_code):
    implications = {
        "soft_landing_goldilocks": "위험자산과 성장자산이 우호적으로 해석될 수 있지만, 방어 필요성이 완전히 사라졌다는 의미는 아닙니다.",
        "slowdown_recession_deflation_risk": "성장 둔화와 방어자산 선호를 함께 점검해야 하는 환경입니다.",
        "higher_for_longer_long_rate_shock": "장기채와 성장주처럼 금리에 민감한 자산의 해석을 보수적으로 봐야 합니다.",
        "stagflation_reinflation_energy_shock": "원자재·물가 압력과 성장 부담이 동시에 나타나는지 확인해야 합니다.",
        "usd_strength_krw_weakness": "KRW 기준 투자자는 환율 노출과 USD 방어력을 함께 점검해야 합니다.",
        "acute_global_stress_liquidity_crunch": "상관관계가 급격히 높아질 수 있어 분산효과와 유동성 리스크를 함께 봐야 합니다.",
        "china_trade_fragmentation_shock": "중국·무역·반도체 경로가 한국/아시아 자산에 주는 영향을 확인해야 합니다.",
        "semiconductor_ai_cycle_shock": "AI·반도체 성장 노출이 큰 포트폴리오는 SOXX와 한국 반도체 beta를 기준으로 손실 집중 가능성을 점검해야 합니다.",
        "korea_domestic_financial_stress": "한국 금융·건설·원화 노출이 큰 투자자는 내수 신용 spread와 PF/부동산 경로를 방어 후보와 함께 봐야 합니다.",
        "geopolitical_escalation_supply_shock": "유가·금·방산·달러가 동시에 움직이는 이벤트 리스크이므로 가격 신호와 뉴스 overlay를 분리해 과신을 피해야 합니다.",
    }
    return implications.get(scenario_code, "이 시나리오가 현재 포트폴리오 해석에 주는 영향을 추가 점검해야 합니다.")


def _driver_effect(contribution):
    return "supporting" if contribution >= 0 else "offsetting"


def _driver_line(driver):
    contribution = driver["contribution"]
    normalized_value = driver["normalized_value"]
    effect = driver.get("driver_effect") or _driver_effect(contribution)
    effect_label = "지지" if effect == "supporting" else "완화/반대"
    return (
        f"`{driver['signal_label']}` — {effect_label} "
        f"(contribution={contribution:+.4f}, normalized={normalized_value:+.4f})"
    )


def _summary_caveat(row):
    caveats = []
    confidence = row["confidence"]
    coverage_ratio = row["coverage_ratio"]
    if confidence < 50:
        caveats.append("confidence가 중간 미만이므로 상태 해석을 보조 신호로 보는 편이 안전합니다")
    if coverage_ratio < 0.75:
        caveats.append("사용 가능한 proxy coverage가 낮아 일부 핵심 지표가 빠졌을 가능성이 있습니다")
    if not caveats:
        return "현재 정형 proxy 기준으로 큰 결측 caveat는 없습니다."
    return "; ".join(caveats) + "."


def _signal_raw_map(signal, market_series_map):
    metric = signal["metric"]
    ticker = signal["ticker"]
    reference_ticker = signal.get("reference_ticker")
    lookback_days = signal["lookback_days"]

    if metric == "level_z":
        series = market_series_map.get(ticker, [])
        return _level_map(series) if series else {}
    if metric == "ret_z":
        series = market_series_map.get(ticker, [])
        return _horizon_return_map(series, lookback_days) if series else {}
    if metric == "relative_ret_z":
        left_series = market_series_map.get(ticker, [])
        right_series = market_series_map.get(reference_ticker, [])
        return _relative_return_map(left_series, right_series, lookback_days) if left_series and right_series else {}
    if metric == "bounded_score":
        series = market_series_map.get(ticker, [])
        return _level_map(series) if series else {}
    raise ValueError(f"Unsupported signal metric: {metric}")


def _bounded_score_map(raw_map):
    return {
        date_str: max(-2.0, min(2.0, (value - 50.0) / 25.0))
        for date_str, value in raw_map.items()
        if value is not None
    }


def _normalize_signal_map(signal, raw_map):
    if signal["metric"] == "bounded_score":
        return _bounded_score_map(raw_map)
    return _rolling_zscore_map(raw_map)


def _factor_state_label(score):
    if score >= 65:
        return "ELEVATED"
    if score >= 45:
        return "NEUTRAL"
    return "LOW"


def _build_factor_rows(market_series_map):
    rows = []
    for factor in _market_factor_definitions():
        signal_data = {}
        total_weight = sum(signal["weight"] for signal in factor["signals"])
        date_union = set()

        for signal in factor["signals"]:
            raw_map = _signal_raw_map(signal, market_series_map)
            normalized_map = _normalize_signal_map(signal, raw_map)
            signal_data[signal["name"]] = {
                "signal": signal,
                "raw_map": raw_map,
                "normalized_map": normalized_map,
            }
            date_union.update(normalized_map.keys())

        for date_str in sorted(date_union):
            weighted_unit_sum = 0.0
            used_weight = 0.0
            breadth_numerator = 0.0
            for signal in factor["signals"]:
                payload = signal_data.get(signal["name"], {})
                normalized_value = payload.get("normalized_map", {}).get(date_str)
                _, unit_score = _aligned_unit(normalized_value, signal["direction"])
                if unit_score is None:
                    continue
                weighted_unit_sum += signal["weight"] * unit_score
                used_weight += signal["weight"]
                breadth_numerator += signal["weight"] * abs(unit_score - 0.5) * 2.0

            if used_weight == 0:
                continue

            coverage_ratio = used_weight / total_weight if total_weight else 0.0
            breadth_score = breadth_numerator / used_weight if used_weight else 0.0
            factor_score = 100.0 * (weighted_unit_sum / used_weight)
            confidence = 100.0 * coverage_ratio * (0.4 + 0.6 * breadth_score)
            rows.append(
                {
                    "date": date_str,
                    "factor_code": factor["factor_code"],
                    "factor_name": factor["factor_name"],
                    "factor_group": factor["factor_group"],
                    "factor_polarity": factor["factor_polarity"],
                    "factor_score": factor_score,
                    "coverage_ratio": coverage_ratio,
                    "breadth_score": breadth_score,
                    "confidence": confidence,
                    "factor_state": _factor_state_label(factor_score),
                    "interpretation": factor["interpretation"],
                }
            )
    return rows


def _score_to_state(scores_by_date):
    rows = []
    previous_state = "OFF"
    for row in scores_by_date:
        score = row["structured_score"]
        state = "OFF"
        if previous_state == "STRESS":
            if score >= 65:
                state = "STRESS"
            elif score >= 60:
                state = "ACTIVE"
            elif score >= 45:
                state = "WATCH"
        elif previous_state == "ACTIVE":
            if score >= 75:
                state = "STRESS"
            elif score >= 50:
                state = "ACTIVE"
            elif score >= 45:
                state = "WATCH"
        elif previous_state == "WATCH":
            if score >= 75:
                state = "STRESS"
            elif score >= 60:
                state = "ACTIVE"
            elif score >= 40:
                state = "WATCH"
        else:
            if score >= 75:
                state = "STRESS"
            elif score >= 60:
                state = "ACTIVE"
            elif score >= 45:
                state = "WATCH"
        row["raw_state"] = state
        row["state_label"] = state
        row["display_state"] = scenario_display_state(row)
        rows.append(row)
        previous_state = state
    return rows


def _build_summary(score_rows, driver_rows, factor_rows=None):
    if not score_rows:
        return "# Daily Market State Summary\n\n- No scenario scores were generated.\n"
    factor_rows = factor_rows or []

    scenario_count = len({row["scenario_code"] for row in score_rows})
    rows_by_date = defaultdict(list)
    for row in score_rows:
        rows_by_date[row["date"]].append(row)

    candidate_dates = []
    min_scenario_count = max(3, math.ceil(scenario_count * 0.75))
    for date_str, rows in rows_by_date.items():
        scenario_present = len({row["scenario_code"] for row in rows})
        avg_coverage = sum(row["coverage_ratio"] for row in rows) / len(rows)
        if scenario_present >= min_scenario_count and avg_coverage >= 0.50:
            candidate_dates.append(date_str)

    if candidate_dates:
        latest_date = max(candidate_dates)
    else:
        latest_date = max(
            rows_by_date.keys(),
            key=lambda date_str: (
                len({row["scenario_code"] for row in rows_by_date[date_str]}),
                sum(row["coverage_ratio"] for row in rows_by_date[date_str]) / len(rows_by_date[date_str]),
                date_str,
            ),
        )
    latest_scores = [row for row in score_rows if row["date"] == latest_date]
    latest_scores.sort(key=lambda row: (-row["structured_score"], row["scenario_name"]))

    selected = [row for row in latest_scores if row["state_label"] in {"STRESS", "ACTIVE"}][:3]
    selected_keys = {row["scenario_code"] for row in selected}
    for row in latest_scores:
        if len(selected) >= 3:
            break
        if row["scenario_code"] not in selected_keys:
            selected.append(row)
            selected_keys.add(row["scenario_code"])
    if not selected:
        selected = latest_scores[:3]

    drivers_by_key = defaultdict(list)
    for row in driver_rows:
        drivers_by_key[(row["date"], row["scenario_code"])].append(row)

    state_counts = defaultdict(int)
    for row in latest_scores:
        state_counts[row["state_label"]] += 1

    lines = [
        "# Daily Market State Summary",
        "",
        f"- 기준일: `{latest_date}`",
        f"- 상태 분포: STRESS {state_counts['STRESS']} / ACTIVE {state_counts['ACTIVE']} / WATCH {state_counts['WATCH']} / OFF {state_counts['OFF']}",
        "- contract note: this scenario vector is diagnostic-only market-state evidence, not a buy/sell, hedge, or portfolio recommendation.",
        "- 해석 범위: Phase 4 정형 데이터 기반 설명 요약입니다. 포트폴리오 자동 변경 신호가 아니라 시장 상태 해석 보조 신호입니다.",
        "- confidence 읽는 법: 현재 값은 데이터 coverage와 신호 breadth 기반의 임시 confidence proxy입니다. 뉴스/정책문 병합 confidence는 Phase 6 범위입니다.",
        "",
    ]

    latest_factors = [row for row in factor_rows if row["date"] == latest_date]
    if latest_factors:
        latest_factors.sort(key=lambda row: (-row["factor_score"], row["factor_name"]))
        lines.append("## 팩터 압축 요약")
        lines.append("- 추가 지표는 개별 신호를 그대로 나열하지 않고 8개 팩터로 압축해 시나리오 판단을 보조합니다.")
        for row in latest_factors[:4]:
            polarity = "우호 팩터" if row["factor_polarity"] == "positive" else "리스크 팩터"
            lines.append(
                f"- `{row['factor_name']}` — {polarity}, {row['factor_state']} "
                f"(score={row['factor_score']:.2f}, confidence={row['confidence']:.2f}, coverage={row['coverage_ratio']:.2f})"
            )
            lines.append(f"  - 해석: {row['interpretation']}")
        lines.append("")

    lines.append("## 전체 시나리오 스냅샷")
    lines.append("- 모든 시나리오의 최신 상태와 대표 driver를 함께 표시합니다.")
    for row in latest_scores:
        scenario_drivers = drivers_by_key.get((row["date"], row["scenario_code"]), [])
        top_supporting = _driver_summary_text(scenario_drivers, "supporting") or "-"
        top_offsetting = _driver_summary_text(scenario_drivers, "offsetting") or "-"
        shown_state = row.get("display_state") or row["state_label"]
        lines.append(
            f"- `{row['scenario_code']}` {row['scenario_name']} · {row.get('scenario_name_ko', '')}: "
            f"{shown_state}, score={row['structured_score']:.2f}, confidence={row['confidence']:.2f}, coverage={row['coverage_ratio']:.2f}"
        )
        lines.append(f"  - supporting: {top_supporting}")
        lines.append(f"  - offsetting: {top_offsetting}")
    lines.append("")

    for index, row in enumerate(selected, start=1):
        scenario_drivers = drivers_by_key.get((row["date"], row["scenario_code"]), [])
        supporting = [driver for driver in scenario_drivers if driver.get("driver_effect") == "supporting"]
        offsetting = [driver for driver in scenario_drivers if driver.get("driver_effect") == "offsetting"]

        shown_state = row.get("display_state") or row["state_label"]
        lines.append(f"## {index}. {row['scenario_name']} · {row.get('scenario_name_ko', '')}")
        lines.append(f"- 관점 lens: `{row.get('lens', 'us_global')}` (관련: `{row.get('related_lenses', '') or '-'}`)")
        lines.append(f"- 상태 해석: `{shown_state}` (raw: `{row['state_label']}`) — {_state_explanation(shown_state)}")
        lines.append(
            f"- 수치: score={row['structured_score']:.2f} | confidence={row['confidence']:.2f}({_confidence_label(row['confidence'])}) | "
            f"coverage={row['coverage_ratio']:.2f}({_coverage_label(row['coverage_ratio'])})"
        )
        if row.get("market_interpretation_ko"):
            lines.append(f"- 장세 설명: {row['market_interpretation_ko']}")
        lines.append(f"- 사용자 관점: {_scenario_user_implication(row['scenario_code'])}")
        lines.append("- 주요 지지 근거:")
        if supporting:
            for driver in supporting[:3]:
                lines.append(f"  - {_driver_line(driver)}")
        else:
            lines.append("  - 상위 영향 지표 중 이 시나리오를 뚜렷하게 지지하는 신호가 제한적입니다.")
        lines.append("- 반대/완화 근거:")
        if offsetting:
            for driver in offsetting[:3]:
                lines.append(f"  - {_driver_line(driver)}")
        else:
            lines.append("  - 상위 영향 지표 기준 뚜렷한 반대 신호는 제한적입니다.")
        lines.append(f"- 주의점: {_summary_caveat(row)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _driver_summary_text(rows, effect):
    selected = [row for row in rows if row.get("driver_effect") == effect]
    selected.sort(key=lambda row: (-abs(row.get("contribution") or 0.0), row.get("signal_name", "")))
    parts = []
    for row in selected[:3]:
        contribution = row.get("contribution")
        normalized_value = row.get("normalized_value")
        contribution_text = f"{contribution:+.4f}" if contribution is not None else ""
        normalized_text = f", z={normalized_value:+.2f}" if normalized_value is not None else ""
        parts.append(f"{row.get('signal_label', row.get('signal_name', ''))} ({contribution_text}{normalized_text})")
    return " | ".join(parts)


def _select_scenario_vector_date(state_rows, as_of_date=None):
    if not state_rows:
        return None
    dates = sorted({row["date"] for row in state_rows})
    if as_of_date is not None:
        eligible = [date_str for date_str in dates if date_str <= as_of_date]
        return eligible[-1] if eligible else None
    scenario_count = len({row["scenario_code"] for row in state_rows})
    rows_by_date = defaultdict(list)
    for row in state_rows:
        rows_by_date[row["date"]].append(row)
    full_dates = [
        date_str
        for date_str, rows in rows_by_date.items()
        if len({row["scenario_code"] for row in rows}) == scenario_count
    ]
    return max(full_dates or dates)


def build_current_scenario_vector_rows(state_rows, driver_rows, as_of_date=None, engine_version=ENGINE_VERSION):
    """Build the machine-readable Phase 4 -> HedgeMate scenario contract rows."""
    vector_date = _select_scenario_vector_date(state_rows, as_of_date=as_of_date)
    if vector_date is None:
        return []

    drivers_by_key = defaultdict(list)
    for row in driver_rows:
        drivers_by_key[(row["date"], row["scenario_code"])].append(row)

    rows = []
    for state_row in sorted(
        [row for row in state_rows if row["date"] == vector_date],
        key=lambda row: (-row["structured_score"], row["scenario_code"]),
    ):
        metadata = _scenario_metadata(state_row["scenario_code"])
        row = dict(state_row)
        if "raw_state" not in row:
            row["raw_state"] = row.get("state_label", "")
        if "display_state" not in row:
            row["display_state"] = scenario_display_state(row)
        row = _enrich_scenario_row(row, state_row["scenario_code"])
        scenario_drivers = drivers_by_key.get((row["date"], row["scenario_code"]), [])
        rows.append(
            {
                "as_of_date": vector_date,
                "date": row["date"],
                "scenario_code": row["scenario_code"],
                "scenario_name": row["scenario_name"],
                "scenario_name_ko": row.get("scenario_name_ko") or metadata.get("scenario_name_ko", ""),
                "lens": row.get("lens") or metadata.get("lens", "us_global"),
                "related_lenses": row.get("related_lenses") or _scenario_related_lenses_text(metadata),
                "source_quality": row.get("source_quality") or _scenario_source_quality(row["scenario_code"], metadata),
                "event_or_seed_dependent": row.get("event_or_seed_dependent") or _scenario_event_or_seed_dependent(
                    row.get("source_quality") or _scenario_source_quality(row["scenario_code"], metadata)
                ),
                "score": row["structured_score"],
                "raw_state": row.get("raw_state") or row.get("state_label", ""),
                "display_state": row.get("display_state") or scenario_display_state(row),
                "confidence": row.get("confidence"),
                "coverage": row.get("coverage_ratio"),
                "top_positive_drivers": _driver_summary_text(scenario_drivers, "supporting"),
                "top_negative_drivers": _driver_summary_text(scenario_drivers, "offsetting"),
                "market_interpretation_ko": row.get("market_interpretation_ko") or metadata.get("market_interpretation_ko", ""),
                "engine_version": engine_version,
            }
        )
    return rows


def attach_driver_summaries_to_state_rows(state_rows, driver_rows):
    drivers_by_key = defaultdict(list)
    for row in driver_rows:
        drivers_by_key[(row["date"], row["scenario_code"])].append(row)
    for row in state_rows:
        scenario_drivers = drivers_by_key.get((row["date"], row["scenario_code"]), [])
        row["top_positive_drivers"] = _driver_summary_text(scenario_drivers, "supporting")
        row["top_negative_drivers"] = _driver_summary_text(scenario_drivers, "offsetting")
    return state_rows


def build_market_state_phase1_to4(market_series_map):
    feature_rows = []
    state_rows = []
    driver_rows = []

    scenario_definitions = _scenario_definitions()
    for scenario in scenario_definitions:
        signal_data = {}
        total_weight = sum(signal["weight"] for signal in scenario["signals"])
        date_union = set()

        for signal in scenario["signals"]:
            raw_map = _signal_raw_map(signal, market_series_map)
            normalized_map = _normalize_signal_map(signal, raw_map)
            signal_data[signal["name"]] = {
                "signal": signal,
                "raw_map": raw_map,
                "normalized_map": normalized_map,
            }
            date_union.update(normalized_map.keys())

        scenario_state_history = []
        for date_str in sorted(date_union):
            weighted_unit_sum = 0.0
            used_weight = 0.0
            breadth_numerator = 0.0
            local_feature_rows = []

            for signal in scenario["signals"]:
                payload = signal_data.get(signal["name"], {})
                normalized_value = payload.get("normalized_map", {}).get(date_str)
                raw_value = payload.get("raw_map", {}).get(date_str)
                aligned_value, unit_score = _aligned_unit(normalized_value, signal["direction"])
                if unit_score is None:
                    continue

                contribution = signal["weight"] * (unit_score - 0.5) * 2.0
                weighted_unit_sum += signal["weight"] * unit_score
                used_weight += signal["weight"]
                breadth_numerator += signal["weight"] * abs(unit_score - 0.5) * 2.0
                local_feature_rows.append(
                    {
                        "date": date_str,
                        "scenario_code": scenario["scenario_code"],
                        "scenario_name": scenario["scenario_name"],
                        "signal_name": signal["name"],
                        "signal_label": signal["label"],
                        "metric_type": signal["metric"],
                        "ticker": signal["ticker"],
                        "reference_ticker": signal.get("reference_ticker", ""),
                        "lookback_days": signal["lookback_days"],
                        "weight": signal["weight"],
                        "direction": signal["direction"],
                        "raw_value": raw_value,
                        "normalized_value": normalized_value,
                        "aligned_value": aligned_value,
                        "unit_score": unit_score,
                        "contribution": contribution,
                    }
                )

            if used_weight == 0:
                continue

            coverage_ratio = used_weight / total_weight if total_weight else 0.0
            breadth_score = breadth_numerator / used_weight if used_weight else 0.0
            structured_score = 100.0 * (weighted_unit_sum / used_weight)
            confidence = 100.0 * coverage_ratio * (0.4 + 0.6 * breadth_score)

            feature_rows.extend(local_feature_rows)
            state_row = {
                "date": date_str,
                "scenario_code": scenario["scenario_code"],
                "scenario_name": scenario["scenario_name"],
                "phase": scenario["phase"],
                "layer": scenario["layer"],
                "structured_score": structured_score,
                "coverage_ratio": coverage_ratio,
                "breadth_score": breadth_score,
                "confidence": confidence,
            }
            scenario_state_history.append(_enrich_scenario_row(state_row, scenario["scenario_code"]))

            top_drivers = sorted(local_feature_rows, key=lambda row: (-abs(row["contribution"]), row["signal_name"]))[:3]
            if scenario["scenario_code"] == "geopolitical_escalation_supply_shock":
                event_driver = next(
                    (row for row in local_feature_rows if row.get("signal_name") == "event_overlay_score"),
                    None,
                )
                if event_driver is not None and event_driver not in top_drivers:
                    top_drivers.append(event_driver)
            for rank, driver in enumerate(top_drivers, start=1):
                driver_rows.append(
                    {
                        "date": driver["date"],
                        "scenario_code": driver["scenario_code"],
                        "scenario_name": driver["scenario_name"],
                        "driver_rank": rank,
                        "signal_name": driver["signal_name"],
                        "signal_label": driver["signal_label"],
                        "metric_type": driver["metric_type"],
                        "driver_effect": _driver_effect(driver["contribution"]),
                        "contribution": driver["contribution"],
                        "raw_value": driver["raw_value"],
                        "normalized_value": driver["normalized_value"],
                        "aligned_value": driver["aligned_value"],
                        "unit_score": driver["unit_score"],
                    }
                )

        state_rows.extend(_score_to_state(sorted(scenario_state_history, key=lambda row: row["date"])))

    attach_driver_summaries_to_state_rows(state_rows, driver_rows)
    factor_rows = _build_factor_rows(market_series_map)
    summary_md = _build_summary(state_rows, driver_rows, factor_rows)
    return {
        "registry_rows": build_scenario_registry_rows(),
        "feature_rows": feature_rows,
        "state_rows": state_rows,
        "driver_rows": driver_rows,
        "factor_rows": factor_rows,
        "summary_md": summary_md,
    }
