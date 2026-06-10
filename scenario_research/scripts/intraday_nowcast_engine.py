"""Intraday 1-hour nowcast engine for Korea-focused market-state overlays.

This module is intentionally dependency-free.  The daily Phase 4 engine remains
the slower, confirmed global regime layer.  This engine produces a provisional
same-day overlay from 1-hour bars so HedgeMate can later distinguish:

    confirmed daily regime != today's Korea-market reaction.
"""
from __future__ import annotations

import csv
import html
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from zoneinfo import ZoneInfo


NOWCAST_ENGINE_VERSION = "intraday_nowcast_1h_v1"
KST = ZoneInfo("Asia/Seoul")

INTRADAY_RAW_FIELDS = [
    "timestamp_utc",
    "timestamp_kst",
    "date_kst",
    "hour_kst",
    "ticker",
    "label",
    "asset_class",
    "lens",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "currency",
    "source",
    "ingested_at",
]

INTRADAY_TICKER_FEATURE_FIELDS = [
    "as_of_utc",
    "as_of_kst",
    "ticker",
    "label",
    "asset_class",
    "lens",
    "latest_timestamp_utc",
    "latest_timestamp_kst",
    "latest_close",
    "bars_loaded",
    "bars_today",
    "return_1h",
    "return_3h",
    "return_session",
    "return_24h",
    "volume_z",
    "data_lag_minutes",
    "freshness_score",
    "quality",
]

NOWCAST_SIGNAL_FIELDS = [
    "as_of_utc",
    "as_of_kst",
    "nowcast_code",
    "signal_name",
    "signal_label",
    "metric_type",
    "ticker",
    "tickers",
    "direction",
    "weight",
    "threshold",
    "raw_value",
    "normalized_value",
    "aligned_value",
    "unit_score",
    "contribution",
    "freshness_score",
    "is_available",
]

NOWCAST_VECTOR_FIELDS = [
    "as_of_utc",
    "as_of_kst",
    "date_kst",
    "nowcast_code",
    "nowcast_name_ko",
    "lens",
    "score",
    "status",
    "confidence",
    "coverage",
    "top_positive_drivers",
    "top_negative_drivers",
    "interpretation_ko",
    "engine_version",
]

NOWCAST_TICKER_SPECS = [
    {"ticker": "^KS200", "label": "KOSPI 200", "asset_class": "kr_index", "lens": "korea_market", "currency": "KRW"},
    {"ticker": "069500.KS", "label": "KODEX 200 ETF", "asset_class": "kr_etf", "lens": "korea_market", "currency": "KRW"},
    {"ticker": "005930.KS", "label": "Samsung Electronics", "asset_class": "kr_stock", "lens": "korea_semiconductor", "currency": "KRW"},
    {"ticker": "000660.KS", "label": "SK Hynix", "asset_class": "kr_stock", "lens": "korea_semiconductor", "currency": "KRW"},
    {"ticker": "035420.KS", "label": "NAVER", "asset_class": "kr_stock", "lens": "korea_growth", "currency": "KRW"},
    {"ticker": "035720.KS", "label": "Kakao", "asset_class": "kr_stock", "lens": "korea_growth", "currency": "KRW"},
    {"ticker": "051910.KS", "label": "LG Chem", "asset_class": "kr_stock", "lens": "korea_battery", "currency": "KRW"},
    {"ticker": "006400.KS", "label": "Samsung SDI", "asset_class": "kr_stock", "lens": "korea_battery", "currency": "KRW"},
    {"ticker": "373220.KS", "label": "LG Energy Solution", "asset_class": "kr_stock", "lens": "korea_battery", "currency": "KRW"},
    {"ticker": "005380.KS", "label": "Hyundai Motor", "asset_class": "kr_stock", "lens": "korea_exporter", "currency": "KRW"},
    {"ticker": "000270.KS", "label": "Kia", "asset_class": "kr_stock", "lens": "korea_exporter", "currency": "KRW"},
    {"ticker": "068270.KS", "label": "Celltrion", "asset_class": "kr_stock", "lens": "korea_defensive", "currency": "KRW"},
    {"ticker": "207940.KS", "label": "Samsung Biologics", "asset_class": "kr_stock", "lens": "korea_defensive", "currency": "KRW"},
    {"ticker": "105560.KS", "label": "KB Financial", "asset_class": "kr_stock", "lens": "korea_financial", "currency": "KRW"},
    {"ticker": "KRW=X", "label": "USD/KRW", "asset_class": "fx", "lens": "fx_krw", "currency": "KRW"},
    {"ticker": "EWY", "label": "iShares MSCI South Korea ETF", "asset_class": "us_etf", "lens": "korea_adr_proxy", "currency": "USD"},
    {"ticker": "SOXX", "label": "US Semiconductor ETF", "asset_class": "us_etf", "lens": "global_semiconductor", "currency": "USD"},
    {"ticker": "QQQ", "label": "Nasdaq 100 ETF", "asset_class": "us_etf", "lens": "global_growth", "currency": "USD"},
    {"ticker": "SPY", "label": "S&P 500 ETF", "asset_class": "us_etf", "lens": "global_risk", "currency": "USD"},
    {"ticker": "TLT", "label": "US Long Treasury ETF", "asset_class": "us_etf", "lens": "global_rates", "currency": "USD"},
]

TICKER_SPEC_BY_TICKER = {spec["ticker"]: spec for spec in NOWCAST_TICKER_SPECS}
KR_STOCK_TICKERS = [
    spec["ticker"]
    for spec in NOWCAST_TICKER_SPECS
    if spec["asset_class"] in {"kr_stock", "kr_etf", "kr_index"}
]
KR_SEMICONDUCTOR_TICKERS = ["005930.KS", "000660.KS"]
KR_DEFENSIVE_TICKERS = ["068270.KS", "207940.KS", "105560.KS"]
KR_GROWTH_TICKERS = ["035420.KS", "035720.KS", "051910.KS", "006400.KS", "373220.KS"]
GLOBAL_RISK_TICKERS = ["EWY", "SOXX", "QQQ", "SPY"]

NOWCAST_DEFINITIONS = [
    {
        "code": "kr_risk_on_intraday",
        "name_ko": "한국장 장중 위험선호",
        "lens": "korea_market",
        "interpretation_ko": "KOSPI200, 대형주 breadth, 반도체, 원화 흐름이 같은 방향으로 개선되는지 보는 오늘 한국장 위험선호 nowcast입니다.",
        "strong_status": "RISK_ON",
        "signals": [
            {"name": "ks200_3h", "label": "KOSPI200 3h return", "type": "ticker", "ticker": "^KS200", "metric": "return_3h", "direction": "positive", "threshold": 0.012, "weight": 0.25},
            {"name": "kr_breadth_session", "label": "KR large-cap session breadth", "type": "breadth", "tickers": KR_STOCK_TICKERS, "metric": "return_session", "direction": "positive", "threshold": 0.25, "weight": 0.25},
            {"name": "semis_3h", "label": "Samsung/SK Hynix 3h basket", "type": "basket", "tickers": KR_SEMICONDUCTOR_TICKERS, "metric": "return_3h", "direction": "positive", "threshold": 0.015, "weight": 0.25},
            {"name": "krw_3h", "label": "USD/KRW 3h return", "type": "ticker", "ticker": "KRW=X", "metric": "return_3h", "direction": "negative", "threshold": 0.004, "weight": 0.15},
            {"name": "global_risk_3h", "label": "EWY/SOXX/QQQ/SPY 3h basket", "type": "basket", "tickers": GLOBAL_RISK_TICKERS, "metric": "return_3h", "direction": "positive", "threshold": 0.012, "weight": 0.10},
        ],
    },
    {
        "code": "kr_semiconductor_pressure_intraday",
        "name_ko": "한국 반도체 장중 부담",
        "lens": "korea_semiconductor",
        "interpretation_ko": "삼성전자·SK하이닉스가 장중 약하고 글로벌 반도체 proxy도 약할 때 한국 포트폴리오의 반도체 쏠림을 경고합니다.",
        "strong_status": "PRESSURE",
        "signals": [
            {"name": "samsung_3h", "label": "Samsung Electronics 3h return", "type": "ticker", "ticker": "005930.KS", "metric": "return_3h", "direction": "negative", "threshold": 0.015, "weight": 0.30},
            {"name": "hynix_3h", "label": "SK Hynix 3h return", "type": "ticker", "ticker": "000660.KS", "metric": "return_3h", "direction": "negative", "threshold": 0.018, "weight": 0.30},
            {"name": "soxx_3h", "label": "SOXX 3h return", "type": "ticker", "ticker": "SOXX", "metric": "return_3h", "direction": "negative", "threshold": 0.015, "weight": 0.15},
            {"name": "ks200_3h", "label": "KOSPI200 3h return", "type": "ticker", "ticker": "^KS200", "metric": "return_3h", "direction": "negative", "threshold": 0.012, "weight": 0.15},
            {"name": "krw_3h", "label": "USD/KRW 3h return", "type": "ticker", "ticker": "KRW=X", "metric": "return_3h", "direction": "positive", "threshold": 0.004, "weight": 0.10},
        ],
    },
    {
        "code": "krw_weakness_intraday",
        "name_ko": "원화약세 장중 압력",
        "lens": "fx_krw",
        "interpretation_ko": "USD/KRW가 장중 상승하고 한국 위험자산이 약할 때 KRW 기준 포트폴리오의 환율/외국인 수급 부담을 경고합니다.",
        "strong_status": "FX_PRESSURE",
        "signals": [
            {"name": "krw_1h", "label": "USD/KRW 1h return", "type": "ticker", "ticker": "KRW=X", "metric": "return_1h", "direction": "positive", "threshold": 0.0025, "weight": 0.30},
            {"name": "krw_3h", "label": "USD/KRW 3h return", "type": "ticker", "ticker": "KRW=X", "metric": "return_3h", "direction": "positive", "threshold": 0.004, "weight": 0.35},
            {"name": "ks200_3h", "label": "KOSPI200 3h return", "type": "ticker", "ticker": "^KS200", "metric": "return_3h", "direction": "negative", "threshold": 0.012, "weight": 0.20},
            {"name": "ewy_3h", "label": "EWY 3h return", "type": "ticker", "ticker": "EWY", "metric": "return_3h", "direction": "negative", "threshold": 0.012, "weight": 0.15},
        ],
    },
    {
        "code": "kr_defensive_rotation_intraday",
        "name_ko": "한국장 방어주 상대강세",
        "lens": "korea_market",
        "interpretation_ko": "바이오/금융 등 방어 성격 basket이 지수·성장주보다 상대적으로 강한지 확인해 장중 방어적 rotation을 표시합니다.",
        "strong_status": "DEFENSIVE_ROTATION",
        "signals": [
            {"name": "defensive_relative_session", "label": "Defensive basket vs KOSPI200 session", "type": "relative", "long_tickers": KR_DEFENSIVE_TICKERS, "short_tickers": ["^KS200"], "metric": "return_session", "direction": "positive", "threshold": 0.010, "weight": 0.35},
            {"name": "growth_3h", "label": "KR growth/battery 3h basket", "type": "basket", "tickers": KR_GROWTH_TICKERS, "metric": "return_3h", "direction": "negative", "threshold": 0.015, "weight": 0.25},
            {"name": "semis_3h", "label": "Samsung/SK Hynix 3h basket", "type": "basket", "tickers": KR_SEMICONDUCTOR_TICKERS, "metric": "return_3h", "direction": "negative", "threshold": 0.015, "weight": 0.20},
            {"name": "kr_breadth_session", "label": "KR large-cap session breadth", "type": "breadth", "tickers": KR_STOCK_TICKERS, "metric": "return_session", "direction": "negative", "threshold": 0.25, "weight": 0.20},
        ],
    },
    {
        "code": "global_risk_spillover_intraday",
        "name_ko": "글로벌 위험회피 한국 전이",
        "lens": "us_global_to_korea",
        "interpretation_ko": "EWY, SOXX, QQQ, SPY가 약하고 원화가 약해질 때 글로벌 risk-off가 한국장으로 전이될 위험을 표시합니다.",
        "strong_status": "RISK_OFF_SPILLOVER",
        "signals": [
            {"name": "global_risk_3h", "label": "EWY/SOXX/QQQ/SPY 3h basket", "type": "basket", "tickers": GLOBAL_RISK_TICKERS, "metric": "return_3h", "direction": "negative", "threshold": 0.012, "weight": 0.40},
            {"name": "soxx_3h", "label": "SOXX 3h return", "type": "ticker", "ticker": "SOXX", "metric": "return_3h", "direction": "negative", "threshold": 0.015, "weight": 0.20},
            {"name": "krw_3h", "label": "USD/KRW 3h return", "type": "ticker", "ticker": "KRW=X", "metric": "return_3h", "direction": "positive", "threshold": 0.004, "weight": 0.20},
            {"name": "ks200_3h", "label": "KOSPI200 3h return", "type": "ticker", "ticker": "^KS200", "metric": "return_3h", "direction": "negative", "threshold": 0.012, "weight": 0.20},
        ],
    },
]


def parse_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(parsed) or math.isinf(parsed):
        return None
    return parsed


def safe_round(value: object, digits: int = 6) -> object:
    parsed = parse_float(value)
    if parsed is None:
        return "" if value is None else value
    return round(parsed, digits)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: safe_round(row.get(key)) for key in fieldnames})


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def iso_to_dt(value: str) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def trailing_return(closes: list[float], bars: int) -> float | None:
    if len(closes) <= bars:
        return None
    base = closes[-1 - bars]
    latest = closes[-1]
    if base <= 0:
        return None
    return latest / base - 1.0


def zscore_latest(values: list[float], window: int = 20) -> float | None:
    clean = [value for value in values if value is not None]
    if len(clean) < 5:
        return None
    sample = clean[-window:]
    if len(sample) < 5:
        return None
    avg = mean(sample)
    variance = sum((value - avg) ** 2 for value in sample) / len(sample)
    std = math.sqrt(variance)
    if std == 0:
        return 0.0
    return (sample[-1] - avg) / std


def freshness_from_lag_minutes(lag_minutes: float | None) -> float:
    if lag_minutes is None:
        return 0.0
    if lag_minutes <= 180:
        return 1.0
    if lag_minutes <= 360:
        return 0.75
    if lag_minutes <= 900:
        return 0.45
    return 0.15


def quality_from_lag_and_bars(lag_minutes: float | None, bars_loaded: int) -> str:
    if bars_loaded < 4:
        return "INSUFFICIENT_BARS"
    if lag_minutes is None:
        return "UNKNOWN"
    if lag_minutes <= 180:
        return "OK"
    if lag_minutes <= 360:
        return "LAGGING"
    return "STALE"


def build_ticker_features(raw_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    rows_by_ticker: dict[str, list[dict[str, object]]] = defaultdict(list)
    latest_dt: datetime | None = None
    for row in raw_rows:
        ticker = str(row.get("ticker", ""))
        close = parse_float(row.get("close"))
        ts = iso_to_dt(str(row.get("timestamp_utc", "")))
        if not ticker or close is None or close <= 0 or ts is None:
            continue
        normalized = dict(row)
        normalized["_dt"] = ts
        normalized["_close"] = close
        rows_by_ticker[ticker].append(normalized)
        if latest_dt is None or ts > latest_dt:
            latest_dt = ts

    if latest_dt is None:
        return []

    as_of_utc = latest_dt.isoformat()
    as_of_kst = latest_dt.astimezone(KST).isoformat()
    feature_rows: list[dict[str, object]] = []
    for ticker, rows in sorted(rows_by_ticker.items()):
        rows.sort(key=lambda row: row["_dt"])
        closes = [float(row["_close"]) for row in rows]
        volumes = [parse_float(row.get("volume")) or 0.0 for row in rows]
        latest = rows[-1]
        latest_ts = latest["_dt"]
        date_kst = str(latest.get("date_kst") or latest_ts.astimezone(KST).date().isoformat())
        today_rows = [row for row in rows if str(row.get("date_kst")) == date_kst]
        today_closes = [float(row["_close"]) for row in today_rows]
        session_return = None
        if len(today_closes) >= 2 and today_closes[0] > 0:
            session_return = today_closes[-1] / today_closes[0] - 1.0
        lag_minutes = max(0.0, (latest_dt - latest_ts).total_seconds() / 60.0)
        spec = TICKER_SPEC_BY_TICKER.get(ticker, {})
        freshness = freshness_from_lag_minutes(lag_minutes)
        feature_rows.append(
            {
                "as_of_utc": as_of_utc,
                "as_of_kst": as_of_kst,
                "ticker": ticker,
                "label": latest.get("label") or spec.get("label", ticker),
                "asset_class": latest.get("asset_class") or spec.get("asset_class", ""),
                "lens": latest.get("lens") or spec.get("lens", ""),
                "latest_timestamp_utc": latest_ts.isoformat(),
                "latest_timestamp_kst": latest_ts.astimezone(KST).isoformat(),
                "latest_close": closes[-1],
                "bars_loaded": len(rows),
                "bars_today": len(today_rows),
                "return_1h": trailing_return(closes, 1),
                "return_3h": trailing_return(closes, 3),
                "return_session": session_return,
                "return_24h": trailing_return(closes, 24),
                "volume_z": zscore_latest(volumes),
                "data_lag_minutes": lag_minutes,
                "freshness_score": freshness,
                "quality": quality_from_lag_and_bars(lag_minutes, len(rows)),
            }
        )
    return feature_rows


def mean_available(values: list[float | None]) -> float | None:
    clean = [value for value in values if value is not None]
    if not clean:
        return None
    return mean(clean)


def feature_map(feature_rows: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    return {str(row["ticker"]): row for row in feature_rows}


def ticker_metric(features: dict[str, dict[str, object]], ticker: str, metric: str) -> tuple[float | None, float]:
    row = features.get(ticker)
    if not row:
        return None, 0.0
    return parse_float(row.get(metric)), parse_float(row.get("freshness_score")) or 0.0


def basket_metric(features: dict[str, dict[str, object]], tickers: list[str], metric: str) -> tuple[float | None, float]:
    values = []
    freshness_values = []
    for ticker in tickers:
        value, freshness = ticker_metric(features, ticker, metric)
        if value is None:
            continue
        values.append(value)
        freshness_values.append(freshness)
    if not values:
        return None, 0.0
    return mean(values), mean(freshness_values) if freshness_values else 0.0


def breadth_metric(features: dict[str, dict[str, object]], tickers: list[str], metric: str) -> tuple[float | None, float]:
    available = []
    freshness_values = []
    for ticker in tickers:
        value, freshness = ticker_metric(features, ticker, metric)
        if value is None:
            continue
        available.append(1.0 if value > 0 else 0.0)
        freshness_values.append(freshness)
    if not available:
        return None, 0.0
    return sum(available) / len(available), mean(freshness_values) if freshness_values else 0.0


def relative_metric(
    features: dict[str, dict[str, object]],
    long_tickers: list[str],
    short_tickers: list[str],
    metric: str,
) -> tuple[float | None, float]:
    long_value, long_fresh = basket_metric(features, long_tickers, metric)
    short_value, short_fresh = basket_metric(features, short_tickers, metric)
    if long_value is None or short_value is None:
        return None, 0.0
    return long_value - short_value, mean([long_fresh, short_fresh])


def resolve_signal(signal: dict[str, object], features: dict[str, dict[str, object]]) -> tuple[float | None, float]:
    signal_type = signal["type"]
    metric = str(signal["metric"])
    if signal_type == "ticker":
        return ticker_metric(features, str(signal["ticker"]), metric)
    if signal_type == "basket":
        return basket_metric(features, list(signal["tickers"]), metric)
    if signal_type == "breadth":
        return breadth_metric(features, list(signal["tickers"]), metric)
    if signal_type == "relative":
        return relative_metric(features, list(signal["long_tickers"]), list(signal["short_tickers"]), metric)
    return None, 0.0


def normalize_signal_value(raw_value: float, signal: dict[str, object]) -> tuple[float, float, float]:
    direction = str(signal.get("direction", "positive"))
    threshold = float(signal.get("threshold", 0.01))
    if str(signal.get("type")) == "breadth":
        normalized = (raw_value - 0.5) / threshold
    else:
        normalized = raw_value / threshold
    aligned = normalized if direction == "positive" else -normalized
    aligned_clipped = max(-1.0, min(1.0, aligned))
    unit_score = (aligned_clipped + 1.0) * 50.0
    return normalized, aligned, unit_score


def signal_tickers(signal: dict[str, object]) -> list[str]:
    if signal["type"] == "ticker":
        return [str(signal["ticker"])]
    if signal["type"] in {"basket", "breadth"}:
        return list(signal["tickers"])
    if signal["type"] == "relative":
        return list(signal["long_tickers"]) + list(signal["short_tickers"])
    return []


def status_from_score(score: float, coverage: float, confidence: float, strong_status: str) -> str:
    if coverage < 0.45:
        return "INSUFFICIENT"
    if confidence < 40:
        return "PROVISIONAL"
    if score >= 72:
        return strong_status
    if score >= 58:
        return "WATCH"
    return "OFF"


def build_nowcast_outputs(
    raw_rows: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    ticker_features = build_ticker_features(raw_rows)
    features = feature_map(ticker_features)
    if not ticker_features:
        return [], [], []

    as_of_utc = str(ticker_features[0]["as_of_utc"])
    as_of_kst = str(ticker_features[0]["as_of_kst"])
    date_kst = datetime.fromisoformat(as_of_kst).date().isoformat()

    signal_rows: list[dict[str, object]] = []
    vector_rows: list[dict[str, object]] = []
    for definition in NOWCAST_DEFINITIONS:
        total_weight = sum(float(signal["weight"]) for signal in definition["signals"])
        used_weight = 0.0
        weighted_score = 0.0
        freshness_values = []
        available_signal_rows = []
        for signal in definition["signals"]:
            raw_value, freshness = resolve_signal(signal, features)
            weight = float(signal["weight"])
            row = {
                "as_of_utc": as_of_utc,
                "as_of_kst": as_of_kst,
                "nowcast_code": definition["code"],
                "signal_name": signal["name"],
                "signal_label": signal["label"],
                "metric_type": signal["type"],
                "ticker": signal.get("ticker", ""),
                "tickers": ",".join(signal_tickers(signal)),
                "direction": signal.get("direction"),
                "weight": weight,
                "threshold": signal.get("threshold"),
                "freshness_score": freshness,
                "is_available": raw_value is not None,
            }
            if raw_value is None:
                row.update(
                    {
                        "raw_value": "",
                        "normalized_value": "",
                        "aligned_value": "",
                        "unit_score": "",
                        "contribution": "",
                    }
                )
                signal_rows.append(row)
                continue

            normalized, aligned, unit_score = normalize_signal_value(raw_value, signal)
            contribution = unit_score * weight
            row.update(
                {
                    "raw_value": raw_value,
                    "normalized_value": normalized,
                    "aligned_value": aligned,
                    "unit_score": unit_score,
                    "contribution": contribution,
                }
            )
            signal_rows.append(row)
            available_signal_rows.append(row)
            used_weight += weight
            weighted_score += contribution
            freshness_values.append(freshness)

        coverage = used_weight / total_weight if total_weight else 0.0
        score = weighted_score / used_weight if used_weight else 0.0
        avg_freshness = mean(freshness_values) if freshness_values else 0.0
        confidence = max(0.0, min(100.0, coverage * 75.0 + avg_freshness * 25.0))
        status = status_from_score(score, coverage, confidence, str(definition["strong_status"]))

        positive_drivers = sorted(
            available_signal_rows,
            key=lambda row: parse_float(row.get("contribution")) or 0.0,
            reverse=True,
        )[:3]
        negative_drivers = sorted(
            available_signal_rows,
            key=lambda row: parse_float(row.get("contribution")) or 0.0,
        )[:3]

        vector_rows.append(
            {
                "as_of_utc": as_of_utc,
                "as_of_kst": as_of_kst,
                "date_kst": date_kst,
                "nowcast_code": definition["code"],
                "nowcast_name_ko": definition["name_ko"],
                "lens": definition["lens"],
                "score": score,
                "status": status,
                "confidence": confidence,
                "coverage": coverage,
                "top_positive_drivers": " | ".join(str(row["signal_label"]) for row in positive_drivers),
                "top_negative_drivers": " | ".join(str(row["signal_label"]) for row in negative_drivers),
                "interpretation_ko": definition["interpretation_ko"],
                "engine_version": NOWCAST_ENGINE_VERSION,
            }
        )

    vector_rows.sort(key=lambda row: parse_float(row.get("score")) or 0.0, reverse=True)
    return ticker_features, signal_rows, vector_rows


def esc(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def fmt(value: object, digits: int = 2) -> str:
    parsed = parse_float(value)
    if parsed is None:
        return "-"
    return f"{parsed:.{digits}f}"


def pct(value: object, digits: int = 2) -> str:
    parsed = parse_float(value)
    if parsed is None:
        return "-"
    return f"{parsed * 100:.{digits}f}%"


def status_pill(status: str) -> str:
    cls = "good" if status in {"RISK_ON"} else "bad" if status in {"PRESSURE", "FX_PRESSURE", "RISK_OFF_SPILLOVER"} else "warn" if status in {"WATCH", "DEFENSIVE_ROTATION", "PROVISIONAL"} else "off"
    return f"<span class='pill {cls}'>{esc(status)}</span>"


def bar(score: object, status: str | None = None) -> str:
    parsed = parse_float(score) or 0.0
    adverse = {"PRESSURE", "FX_PRESSURE", "RISK_OFF_SPILLOVER"}
    if status in adverse and parsed >= 72:
        color = "#ff5c72"
    elif status == "RISK_ON" and parsed >= 72:
        color = "#00d49a"
    else:
        color = "#ffb454" if parsed >= 58 else "#73809b"
    return f"<div class='bar'><span style='width:{max(0,min(100,parsed)):.1f}%;background:{color}'></span></div><small>{parsed:.1f}</small>"


def render_intraday_dashboard(
    output_path: Path,
    *,
    run_id: str,
    raw_path: Path,
    ticker_feature_path: Path,
    signal_path: Path,
    vector_path: Path,
    metadata_path: Path,
    ticker_features: list[dict[str, object]],
    signal_rows: list[dict[str, object]],
    vector_rows: list[dict[str, object]],
    metadata: dict[str, object],
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    as_of_kst = vector_rows[0].get("as_of_kst") if vector_rows else "-"
    raw_count = metadata.get("raw_row_count", 0)
    fetched = metadata.get("fetched_ticker_count", 0)
    requested = metadata.get("requested_ticker_count", 0)
    top = vector_rows[0] if vector_rows else {}

    vector_table = []
    for row in vector_rows:
        vector_table.append(
            f"<tr><td><b>{esc(row.get('nowcast_name_ko'))}</b><br><small>{esc(row.get('nowcast_code'))} · {esc(row.get('lens'))}</small></td>"
            f"<td>{status_pill(str(row.get('status')))}</td>"
            f"<td>{bar(row.get('score'), str(row.get('status')))}</td>"
            f"<td>{pct(row.get('coverage'), 0)}<br><small>confidence {fmt(row.get('confidence'), 1)}</small></td>"
            f"<td><small><b>+</b> {esc(row.get('top_positive_drivers'))}<br><b>-</b> {esc(row.get('top_negative_drivers'))}</small></td>"
            f"<td><small>{esc(row.get('interpretation_ko'))}</small></td></tr>"
        )

    ticker_table = []
    for row in sorted(ticker_features, key=lambda item: (str(item.get("lens")), str(item.get("ticker")))):
        ticker_table.append(
            f"<tr><td><b>{esc(row.get('ticker'))}</b><br><small>{esc(row.get('label'))}</small></td>"
            f"<td>{esc(row.get('lens'))}</td><td>{esc(row.get('quality'))}</td>"
            f"<td>{pct(row.get('return_1h'))}</td><td>{pct(row.get('return_3h'))}</td><td>{pct(row.get('return_session'))}</td>"
            f"<td>{fmt(row.get('data_lag_minutes'), 0)}분</td></tr>"
        )

    html_doc = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>1H Intraday Nowcast · {esc(run_id)}</title>
  <style>
    :root {{ color-scheme:dark; --bg:#07111f; --panel:#111d31; --line:#263852; --text:#eef5ff; --muted:#9badc7; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; padding:28px; background:linear-gradient(135deg,#102544,#07111f 55%,#040812); color:var(--text); font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
    h1 {{ margin:0 0 8px; letter-spacing:-.03em; }}
    h2 {{ margin:28px 0 12px; }}
    p,small {{ color:var(--muted); line-height:1.5; }}
    .hero,.section,.card {{ border:1px solid var(--line); border-radius:20px; background:rgba(17,29,49,.82); }}
    .hero {{ padding:24px; box-shadow:0 20px 80px rgba(0,0,0,.28); }}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:12px; margin-top:16px; }}
    .card {{ padding:16px; }}
    .metric {{ font-size:23px; font-weight:800; margin:4px 0; }}
    .section {{ margin-top:18px; padding:18px; }}
    table {{ width:100%; border-collapse:collapse; background:rgba(5,10,18,.45); border-radius:14px; overflow:hidden; }}
    th,td {{ padding:11px 12px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }}
    th {{ color:#cfe0f7; background:rgba(255,255,255,.04); font-size:12px; text-transform:uppercase; letter-spacing:.05em; }}
    tr:last-child td {{ border-bottom:0; }}
    .pill {{ display:inline-block; padding:4px 9px; border-radius:999px; border:1px solid var(--line); font-size:12px; font-weight:800; }}
    .pill.good {{ border-color:rgba(0,212,154,.45); background:rgba(0,212,154,.12); color:#8dffd9; }}
    .pill.warn {{ border-color:rgba(255,180,84,.45); background:rgba(255,180,84,.12); color:#ffd7a5; }}
    .pill.bad {{ border-color:rgba(255,92,114,.45); background:rgba(255,92,114,.12); color:#ffb5c1; }}
    .pill.off {{ color:#b8c7dd; }}
    .bar {{ width:130px; height:9px; border-radius:999px; background:#26364f; overflow:hidden; margin:4px 0; }}
    .bar span {{ display:block; height:100%; border-radius:999px; }}
    .path {{ font-family:ui-monospace,SFMono-Regular,Consolas,monospace; word-break:break-all; color:#b9c9df; }}
  </style>
</head>
<body>
  <section class="hero">
    <h1>1시간봉 한국장 Nowcast</h1>
    <p>확정 일봉 장세와 별도로, 오늘 한국장/원화/반도체 반응을 1시간봉으로 빠르게 감지하는 임시 레이어입니다. 이 값은 확정 장세가 아니라 장중 보조 신호입니다.</p>
    <div class="grid">
      <div class="card"><small>as of KST</small><div class="metric">{esc(as_of_kst)}</div><small>latest bar timestamp</small></div>
      <div class="card"><small>Top nowcast</small><div class="metric">{esc(top.get('nowcast_name_ko', '-'))}</div><small>{esc(top.get('status', '-'))}</small></div>
      <div class="card"><small>raw bars</small><div class="metric">{esc(raw_count)}</div><small>fetched tickers {esc(fetched)}/{esc(requested)}</small></div>
      <div class="card"><small>engine</small><div class="metric">{NOWCAST_ENGINE_VERSION}</div><small>1h provisional overlay</small></div>
    </div>
  </section>

  <section class="section">
    <h2>Nowcast Vector</h2>
    <table><thead><tr><th>Nowcast</th><th>Status</th><th>Score</th><th>신뢰도</th><th>Drivers</th><th>해석</th></tr></thead><tbody>
      {''.join(vector_table)}
    </tbody></table>
  </section>

  <section class="section">
    <h2>Ticker 1H Features</h2>
    <table><thead><tr><th>Ticker</th><th>Lens</th><th>Quality</th><th>1H</th><th>3H</th><th>Session</th><th>Lag</th></tr></thead><tbody>
      {''.join(ticker_table)}
    </tbody></table>
  </section>

  <section class="section">
    <h2>Output paths</h2>
    <p class="path">raw: {esc(raw_path)}</p>
    <p class="path">ticker features: {esc(ticker_feature_path)}</p>
    <p class="path">signals: {esc(signal_path)}</p>
    <p class="path">nowcast vector: {esc(vector_path)}</p>
    <p class="path">metadata: {esc(metadata_path)}</p>
  </section>
</body>
</html>
"""
    output_path.write_text(html_doc, encoding="utf-8")
    return output_path


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
