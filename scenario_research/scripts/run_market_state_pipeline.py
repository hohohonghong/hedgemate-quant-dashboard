#!/usr/bin/env python3
import argparse
import csv
import json
import math
import time
import urllib.parse
import urllib.request
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from .manifest_sync import sync_active_hedgemate_from_product_manifest
except ImportError:
    from manifest_sync import sync_active_hedgemate_from_product_manifest

try:
    from .market_state_engine import (
        ENGINE_VERSION,
        FX_TICKER,
        GEOPOLITICAL_EVENT_OVERLAY,
        LOW_FREQUENCY_INDICATOR_SPECS,
        MARKET_BREADTH_SERIES_SPECS,
        MARKET_FACTOR_FIELDS,
        MARKET_STATE_TICKER_SPECS,
        SCENARIO_DRIVER_FIELDS,
        SCENARIO_FEATURE_FIELDS,
        SCENARIO_REGISTRY_FIELDS,
        SCENARIO_STATE_FIELDS,
        SCENARIO_VECTOR_FIELDS,
        SYNTHETIC_BASKET_SPECS,
        build_current_scenario_vector_rows,
        build_market_state_phase1_to4,
    )
except ImportError:
    from market_state_engine import (
        ENGINE_VERSION,
        FX_TICKER,
        GEOPOLITICAL_EVENT_OVERLAY,
        LOW_FREQUENCY_INDICATOR_SPECS,
        MARKET_BREADTH_SERIES_SPECS,
        MARKET_FACTOR_FIELDS,
        MARKET_STATE_TICKER_SPECS,
        SCENARIO_DRIVER_FIELDS,
        SCENARIO_FEATURE_FIELDS,
        SCENARIO_REGISTRY_FIELDS,
        SCENARIO_STATE_FIELDS,
        SCENARIO_VECTOR_FIELDS,
        SYNTHETIC_BASKET_SPECS,
        build_current_scenario_vector_rows,
        build_market_state_phase1_to4,
    )


REPO_ROOT = Path(__file__).resolve().parents[2]
SCENARIO_ROOT = REPO_ROOT / "scenario_research"
HEDGEMATE_ROOT = REPO_ROOT / "HedgeMate"
SHARED_RAW_DIR = HEDGEMATE_ROOT / "outputs" / "raw"
OUTPUT_RAW_DIR = SCENARIO_ROOT / "outputs" / "raw"
OUTPUT_PROCESSED_DIR = SCENARIO_ROOT / "outputs" / "processed"
OUTPUT_REPORT_DIR = SCENARIO_ROOT / "outputs" / "reports"
OUTPUT_SCENARIO_VECTOR_DIR = SCENARIO_ROOT / "outputs" / "scenario_vectors"
OUTPUT_MANIFEST_JSON = SCENARIO_ROOT / "outputs" / "latest_manifest.json"
MIN_TICKER_COVERAGE_RATIO = 0.75
ANCHOR_FORWARD_FILL_SPECS = {
    FX_TICKER: {"max_gap_days": 3, "strategy": "previous_close_forward_fill"},
}
EXTERNAL_INDICATOR_INPUTS = [
    SCENARIO_ROOT / "inputs" / "market_state_external_indicators.csv",
    HEDGEMATE_ROOT / "inputs" / "market_state_external_indicators.csv",
]
EVENT_OVERLAY_DIR = SCENARIO_ROOT / "outputs" / "events"


def now_utc():
    return datetime.now(timezone.utc)


def build_run_id(run_ts=None):
    ts = run_ts or now_utc()
    return f"{ts.strftime('%Y%m%dT%H%M%S%f')}-{uuid.uuid4().hex[:8]}"


def parse_float(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


SOURCE_QUALITY_PRIORITY = {
    "seed": 0,
    "fixture": 1,
    "manual": 2,
    "unknown": 3,
    "official": 4,
    "market": 4,
}


def infer_source_quality(source):
    raw = str(source or "").strip().lower()
    if not raw:
        return "unknown"
    if "seed" in raw:
        return "seed"
    if "fixture" in raw or "sample" in raw:
        return "fixture"
    if "manual" in raw:
        return "manual"
    if "official" in raw or "ecos" in raw or "fsc" in raw or "reb" in raw:
        return "official"
    return "manual"


def combine_source_quality(values):
    normalized = [str(value or "unknown").lower() for value in values if value]
    if not normalized:
        return "unknown"
    return min(normalized, key=lambda value: SOURCE_QUALITY_PRIORITY.get(value, 3))


def safe_round(value, digits=6):
    if value is None:
        return ""
    if isinstance(value, float):
        return round(value, digits)
    return value


def write_csv(path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: safe_round(row.get(key)) for key in fieldnames})


def update_latest_manifest(updates):
    existing = {}
    if OUTPUT_MANIFEST_JSON.exists():
        try:
            existing = json.loads(OUTPUT_MANIFEST_JSON.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = {}
    existing.update({key: value for key, value in updates.items() if value is not None})
    existing = sync_active_hedgemate_from_product_manifest(existing)
    OUTPUT_MANIFEST_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MANIFEST_JSON.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")


def find_shared_raw_file(prefix, data_version):
    exact = SHARED_RAW_DIR / f"{prefix}{data_version}.csv"
    if exact.exists():
        return exact, "exact"

    candidates = sorted(SHARED_RAW_DIR.glob(f"{prefix}*.csv"))
    if not candidates:
        return exact, "missing"

    def version_key(path):
        version = path.stem.removeprefix(prefix)
        date_part = version[:8]
        return date_part, version

    target_date = (data_version or "")[:8]
    prior = [path for path in candidates if version_key(path)[0] <= target_date]
    if prior:
        return max(prior, key=version_key), "fallback_prior"
    return max(candidates, key=version_key), "fallback_latest"


def fetch_yahoo_chart(ticker, period1, period2, retries=5):
    encoded_ticker = urllib.parse.quote(ticker, safe="")
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded_ticker}"
        f"?period1={period1}&period2={period2}&interval=1d&events=div%2Csplits"
    )
    for attempt in range(1, retries + 1):
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception:
            if attempt == retries:
                return []
            time.sleep(min(2**attempt, 20))
            continue

        result = payload.get("chart", {}).get("result", [])
        if not result:
            return []
        root = result[0]
        timestamps = root.get("timestamp", [])
        quote = root.get("indicators", {}).get("quote", [{}])[0]
        adj_close_list = root.get("indicators", {}).get("adjclose", [{}])[0].get("adjclose", [])
        closes = quote.get("close", [])

        rows = []
        for index, ts in enumerate(timestamps):
            close = closes[index] if index < len(closes) else None
            adj_close = adj_close_list[index] if index < len(adj_close_list) else close
            if close is None:
                continue
            rows.append(
                {
                    "date": datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat(),
                    "close": close,
                    "adj_close": adj_close if adj_close is not None else close,
                }
            )
        return rows
    return []


def load_shared_market_series(raw_file, allowed_tickers):
    series_map = defaultdict(list)
    if not raw_file.exists():
        return series_map

    with raw_file.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            ticker = row.get("ticker")
            if ticker not in allowed_tickers:
                continue
            adj_close = parse_float(row.get("adj_close"))
            if adj_close is None or adj_close <= 0:
                continue
            series_map[ticker].append((row["date"], adj_close))

    for ticker in series_map:
        series_map[ticker].sort(key=lambda item: item[0])
    return series_map


def load_shared_market_universe(raw_file):
    series_map = defaultdict(list)
    asset_class_by_ticker = {}
    if not raw_file.exists():
        return series_map, asset_class_by_ticker

    with raw_file.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            ticker = row.get("ticker")
            adj_close = parse_float(row.get("adj_close"))
            if not ticker or adj_close is None or adj_close <= 0:
                continue
            series_map[ticker].append((row["date"], adj_close))
            asset_class_by_ticker[ticker] = row.get("asset_class", "")

    for ticker in series_map:
        series_map[ticker].sort(key=lambda item: item[0])
    return series_map, asset_class_by_ticker


def load_shared_benchmark_series(raw_file, allowed_tickers):
    series_map = defaultdict(list)
    if not raw_file.exists():
        return series_map

    with raw_file.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            ticker = row.get("ticker")
            if ticker not in allowed_tickers:
                continue
            adj_close = parse_float(row.get("adj_close"))
            if adj_close is None or adj_close <= 0:
                continue
            series_map[ticker].append((row["date"], adj_close))

    for ticker in series_map:
        series_map[ticker].sort(key=lambda item: item[0])
    return series_map


def load_shared_fx_map(raw_file):
    fx_map = {}
    if not raw_file.exists():
        return fx_map

    with raw_file.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("ticker") != FX_TICKER:
                continue
            close = parse_float(row.get("close"))
            if close is None or close <= 0:
                continue
            fx_map[row["date"]] = close
    return fx_map


def load_cached_market_state_raw(raw_file):
    raw_rows = []
    ticker_series = defaultdict(list)
    if not raw_file.exists():
        return raw_rows, ticker_series

    with raw_file.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            parsed = {
                "date": row["date"],
                "ticker": row["ticker"],
                "label": row.get("label", ""),
                "close": parse_float(row.get("close")),
                "source": row.get("source", "scenario_cache"),
                "currency": row.get("currency", ""),
                "ingested_at": row.get("ingested_at", ""),
            }
            raw_rows.append(parsed)
            if parsed["close"] is not None and parsed["close"] > 0:
                ticker_series[parsed["ticker"]].append((parsed["date"], parsed["close"]))

    for ticker in ticker_series:
        ticker_series[ticker].sort(key=lambda item: item[0])
    return raw_rows, ticker_series


def _iso_to_date(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def _fill_anchor_gap_for_series(ticker, series, anchor_date, max_gap_days, strategy):
    if not anchor_date or not series:
        return list(series), []
    if any(date_str == anchor_date for date_str, _, _ in series):
        return list(series), []

    earlier = [(date_str, close, source) for date_str, close, source in series if date_str < anchor_date]
    later = [(date_str, close, source) for date_str, close, source in series if date_str > anchor_date]
    if not earlier or not later:
        return list(series), []

    previous_date, previous_close, previous_source = max(earlier, key=lambda item: item[0])
    next_date, _, _ = min(later, key=lambda item: item[0])
    gap_days = (_iso_to_date(anchor_date) - _iso_to_date(previous_date)).days
    if gap_days <= 0 or gap_days > max_gap_days:
        return list(series), []

    filled_series = list(series)
    filled_series.append((anchor_date, previous_close, "anchor_forward_fill"))
    filled_series.sort(key=lambda item: item[0])
    fill_rows = [
        {
            "ticker": ticker,
            "filled_date": anchor_date,
            "source_date": previous_date,
            "next_observation_date": next_date,
            "strategy": strategy,
            "source": previous_source,
        }
    ]
    return filled_series, fill_rows


def apply_anchor_forward_fills(series_map, anchor_date):
    if not anchor_date:
        return dict(series_map), []

    updated_map = {}
    fill_rows = []
    for ticker, series in series_map.items():
        spec = ANCHOR_FORWARD_FILL_SPECS.get(ticker)
        if not spec:
            updated_map[ticker] = list(series)
            continue
        filled_series, local_fills = _fill_anchor_gap_for_series(
            ticker=ticker,
            series=series,
            anchor_date=anchor_date,
            max_gap_days=spec["max_gap_days"],
            strategy=spec["strategy"],
        )
        updated_map[ticker] = filled_series
        fill_rows.extend(local_fills)
    return updated_map, fill_rows


def _tickers_for_breadth_group(series_map, asset_class_by_ticker, group):
    if group == "all":
        return sorted(series_map.keys())
    return sorted(ticker for ticker in series_map if asset_class_by_ticker.get(ticker) == group)


def _positive_return_breadth(series_map, tickers, horizon, min_count, anchor_date=None):
    values_by_date = defaultdict(list)
    for ticker in tickers:
        series = [(date_str, close) for date_str, close in series_map.get(ticker, []) if anchor_date is None or date_str <= anchor_date]
        for idx in range(horizon, len(series)):
            date_str, price = series[idx]
            _, previous = series[idx - horizon]
            if previous is None or previous <= 0 or price is None or price <= 0:
                continue
            values_by_date[date_str].append(1.0 if price / previous - 1.0 > 0 else 0.0)
    return [
        (date_str, sum(values) / len(values))
        for date_str, values in sorted(values_by_date.items())
        if len(values) >= min_count
    ]


def _above_moving_average_breadth(series_map, tickers, window, min_count, anchor_date=None):
    values_by_date = defaultdict(list)
    for ticker in tickers:
        series = [(date_str, close) for date_str, close in series_map.get(ticker, []) if anchor_date is None or date_str <= anchor_date]
        history = []
        for date_str, price in series:
            if price is None or price <= 0:
                continue
            history.append(price)
            if len(history) < window:
                continue
            moving_average = sum(history[-window:]) / window
            values_by_date[date_str].append(1.0 if price >= moving_average else 0.0)
    return [
        (date_str, sum(values) / len(values))
        for date_str, values in sorted(values_by_date.items())
        if len(values) >= min_count
    ]


def build_market_breadth_series(universe_series_map, asset_class_by_ticker, anchor_date=None):
    breadth_series = {}
    metadata_rows = []
    for spec in MARKET_BREADTH_SERIES_SPECS:
        tickers = _tickers_for_breadth_group(universe_series_map, asset_class_by_ticker, spec["group"])
        if spec["kind"] == "positive_return":
            series = _positive_return_breadth(
                universe_series_map,
                tickers,
                horizon=spec["horizon"],
                min_count=spec["min_count"],
                anchor_date=anchor_date,
            )
        elif spec["kind"] == "above_moving_average":
            series = _above_moving_average_breadth(
                universe_series_map,
                tickers,
                window=spec["horizon"],
                min_count=spec["min_count"],
                anchor_date=anchor_date,
            )
        else:
            series = []
        if series:
            breadth_series[spec["ticker"]] = series
        metadata_rows.append(
            {
                "ticker": spec["ticker"],
                "label": spec["label"],
                "group": spec["group"],
                "kind": spec["kind"],
                "horizon": spec["horizon"],
                "source_ticker_count": len(tickers),
                "observation_count": len(series),
                "latest_date": series[-1][0] if series else None,
                "latest_value": series[-1][1] if series else None,
            }
        )
    return breadth_series, metadata_rows


def _return_map_from_series(series):
    returns = {}
    clean = [(date_str, close) for date_str, close in sorted(series, key=lambda item: item[0]) if close is not None and close > 0]
    for idx in range(1, len(clean)):
        date_str, close = clean[idx]
        _, previous = clean[idx - 1]
        if previous > 0 and close > 0:
            returns[date_str] = close / previous - 1.0
    return returns


def build_synthetic_basket_series(series_map, basket_specs=SYNTHETIC_BASKET_SPECS, anchor_date=None):
    basket_series = {}
    metadata_rows = []
    for spec in basket_specs:
        members = list(spec.get("members") or [])
        min_count = spec.get("min_count") or max(1, math.ceil(len(members) / 2))
        member_return_maps = {
            member: _return_map_from_series(
                [(date_str, close) for date_str, close in series_map.get(member, []) if anchor_date is None or date_str <= anchor_date]
            )
            for member in members
            if series_map.get(member)
        }
        all_dates = sorted({date_str for ret_map in member_return_maps.values() for date_str in ret_map})
        price = 100.0
        synthetic = []
        for date_str in all_dates:
            returns = [ret_map[date_str] for ret_map in member_return_maps.values() if date_str in ret_map]
            if len(returns) < min_count:
                continue
            price *= 1.0 + sum(returns) / len(returns)
            synthetic.append((date_str, price))
        if synthetic:
            basket_series[spec["ticker"]] = synthetic
        metadata_rows.append(
            {
                "ticker": spec["ticker"],
                "label": spec["label"],
                "members": "|".join(members),
                "loaded_members": "|".join(sorted(member_return_maps.keys())),
                "min_count": min_count,
                "observation_count": len(synthetic),
                "latest_date": synthetic[-1][0] if synthetic else None,
                "latest_value": synthetic[-1][1] if synthetic else None,
            }
        )
    return basket_series, metadata_rows


def load_external_indicator_observations(input_paths=EXTERNAL_INDICATOR_INPUTS, event_overlay_dir=EVENT_OVERLAY_DIR):
    observations = defaultdict(list)
    loaded_sources = []
    for path in input_paths:
        if not path.exists():
            continue
        loaded_sources.append(str(path))
        with path.open("r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                ticker = row.get("ticker") or row.get("indicator_code") or row.get("series_code")
                value = parse_float(row.get("value") or row.get("close") or row.get("level"))
                date_str = row.get("date") or row.get("observation_date")
                if not ticker or not date_str or value is None:
                    continue
                observations[ticker].append(
                    {
                        "date": date_str,
                        "value": value,
                        "source": row.get("source") or str(path),
                        "source_quality": row.get("source_quality")
                        or infer_source_quality(row.get("source") or str(path)),
                    }
                )

    for path in sorted(event_overlay_dir.glob("event_overlay_daily_*.csv")):
        loaded_any = False
        with path.open("r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if row.get("scenario_code") != "geopolitical_escalation_supply_shock":
                    continue
                value = parse_float(row.get("event_overlay_score"))
                date_str = row.get("date")
                if not date_str or value is None:
                    continue
                observations[GEOPOLITICAL_EVENT_OVERLAY].append(
                    {
                        "date": date_str,
                        "value": value,
                        "source": str(path),
                        "source_quality": "manual",
                    }
                )
                loaded_any = True
        if loaded_any:
            loaded_sources.append(str(path))

    for ticker in observations:
        deduped = {}
        for row in observations[ticker]:
            deduped[row["date"]] = row
        observations[ticker] = [deduped[date_str] for date_str in sorted(deduped)]
    return observations, loaded_sources


def build_low_frequency_indicator_series(calendar_dates, anchor_date=None, observations_by_ticker=None):
    observations_by_ticker = observations_by_ticker or {}
    if anchor_date is not None:
        calendar_dates = [date_str for date_str in calendar_dates if date_str <= anchor_date]
    calendar_dates = sorted(calendar_dates)
    indicator_series = {}
    metadata_rows = []
    for spec in LOW_FREQUENCY_INDICATOR_SPECS:
        ticker = spec["ticker"]
        max_staleness_days = spec.get("max_staleness_days", 120)
        raw_observations = [
            row for row in observations_by_ticker.get(ticker, [])
            if not anchor_date or row["date"] <= anchor_date
        ]
        filled = []
        obs_index = -1
        last_observed = None
        for date_str in calendar_dates:
            while obs_index + 1 < len(raw_observations) and raw_observations[obs_index + 1]["date"] <= date_str:
                obs_index += 1
                last_observed = raw_observations[obs_index]
            if not last_observed:
                continue
            staleness_days = (_iso_to_date(date_str) - _iso_to_date(last_observed["date"])).days
            if staleness_days < 0 or staleness_days > max_staleness_days:
                continue
            filled.append((date_str, last_observed["value"]))
        if filled:
            indicator_series[ticker] = filled

        latest_observation = raw_observations[-1] if raw_observations else None
        source_qualities = sorted(
            {
                row.get("source_quality") or infer_source_quality(row.get("source"))
                for row in raw_observations
            }
        )
        source_quality = combine_source_quality(source_qualities)
        if latest_observation and anchor_date:
            latest_staleness = (_iso_to_date(anchor_date) - _iso_to_date(latest_observation["date"])).days
        else:
            latest_staleness = None
        metadata_rows.append(
            {
                "ticker": ticker,
                "label": spec["label"],
                "frequency": spec.get("frequency", ""),
                "max_staleness_days": max_staleness_days,
                "raw_observation_count": len(raw_observations),
                "forward_filled_count": len(filled),
                "last_observed_date": latest_observation["date"] if latest_observation else None,
                "staleness_days": latest_staleness,
                "latest_value": latest_observation["value"] if latest_observation else None,
                "source": latest_observation["source"] if latest_observation else None,
                "source_quality": source_quality,
                "source_qualities": "|".join(source_qualities),
                "status": "OK" if filled else "MISSING",
            }
        )
    return indicator_series, metadata_rows


def save_market_state_raw(raw_file, raw_rows):
    columns = ["date", "ticker", "label", "close", "source", "currency", "ingested_at"]
    write_csv(raw_file, columns, sorted(raw_rows, key=lambda row: (row["ticker"], row["date"])))


def choose_aligned_market_anchor(series_map, min_coverage_ratio=MIN_TICKER_COVERAGE_RATIO):
    dates_to_tickers = defaultdict(set)
    last_date_by_ticker = {}

    for ticker, series in series_map.items():
        if not series:
            continue
        last_date_by_ticker[ticker] = series[-1][0]
        for date_str, _ in series:
            dates_to_tickers[date_str].add(ticker)

    total_tickers = len(last_date_by_ticker)
    if total_tickers == 0:
        return None, {
            "alignment_mode": "latest_date_with_min_ticker_coverage",
            "min_ticker_coverage_ratio": min_coverage_ratio,
            "total_tickers": 0,
            "anchor_date": None,
            "anchor_ticker_count": 0,
            "anchor_ticker_coverage_ratio": 0.0,
            "tickers_on_anchor_date": [],
            "last_date_by_ticker": {},
        }

    min_ticker_count = max(3, math.ceil(total_tickers * min_coverage_ratio))
    candidate_dates = sorted(
        date_str
        for date_str, tickers in dates_to_tickers.items()
        if len(tickers) >= min_ticker_count
    )

    if candidate_dates:
        anchor_date = candidate_dates[-1]
    else:
        anchor_date = max(
            dates_to_tickers.keys(),
            key=lambda date_str: (len(dates_to_tickers[date_str]), date_str),
        )

    anchor_tickers = sorted(dates_to_tickers.get(anchor_date, set()))
    anchor_missing_tickers = sorted(set(last_date_by_ticker) - set(anchor_tickers))
    tickers_after_anchor_date = {
        ticker: last_date
        for ticker, last_date in sorted(last_date_by_ticker.items())
        if anchor_date is not None and last_date > anchor_date
    }
    metadata = {
        "alignment_mode": "latest_date_with_min_ticker_coverage",
        "min_ticker_coverage_ratio": min_coverage_ratio,
        "min_ticker_count": min_ticker_count,
        "total_tickers": total_tickers,
        "anchor_date": anchor_date,
        "anchor_ticker_count": len(anchor_tickers),
        "anchor_ticker_coverage_ratio": (len(anchor_tickers) / total_tickers) if total_tickers else 0.0,
        "tickers_on_anchor_date": anchor_tickers,
        "tickers_missing_on_anchor_date": anchor_missing_tickers,
        "tickers_after_anchor_date": tickers_after_anchor_date,
        "last_date_by_ticker": dict(sorted(last_date_by_ticker.items())),
    }
    return anchor_date, metadata


def build_market_state_raw(period1, period2, data_version, ingested_at, reuse_shared_cache=True):
    raw_file = OUTPUT_RAW_DIR / f"raw_market_state_daily_{data_version}.csv"
    _, cached_series = load_cached_market_state_raw(raw_file)

    spec_map = {spec["ticker"]: spec for spec in MARKET_STATE_TICKER_SPECS}
    shared_tickers = {spec["ticker"] for spec in MARKET_STATE_TICKER_SPECS if spec["ticker"] != FX_TICKER}

    shared_market_file, shared_market_file_mode = find_shared_raw_file("raw_market_daily_", data_version)
    shared_benchmark_file, shared_benchmark_file_mode = find_shared_raw_file("raw_benchmark_daily_", data_version)
    shared_fx_file, shared_fx_file_mode = find_shared_raw_file("raw_fx_daily_", data_version)
    shared_market_series = load_shared_market_series(shared_market_file, shared_tickers) if reuse_shared_cache else {}
    shared_benchmark_series = load_shared_benchmark_series(shared_benchmark_file, shared_tickers) if reuse_shared_cache else {}
    universe_series_map, universe_asset_class_by_ticker = (
        load_shared_market_universe(shared_market_file) if reuse_shared_cache else ({}, {})
    )
    shared_fx_map = load_shared_fx_map(shared_fx_file) if reuse_shared_cache else {}

    unaligned_series_map = {}
    for spec in MARKET_STATE_TICKER_SPECS:
        ticker = spec["ticker"]
        source = "scenario_cache"

        if ticker == FX_TICKER:
            series = sorted(
                [(date_str, close) for date_str, close in shared_fx_map.items() if close is not None and close > 0],
                key=lambda item: item[0],
            )
            if series:
                source = "hedgemate_fx_raw"
            else:
                fetched = fetch_yahoo_chart(ticker, period1, period2)
                time.sleep(0.4)
                series = [(row["date"], row["adj_close"]) for row in fetched if row.get("adj_close") is not None and row.get("adj_close") > 0]
                source = "yahoo"
        elif ticker in shared_market_series:
            series = list(shared_market_series[ticker])
            source = "hedgemate_market_raw"
        elif ticker in shared_benchmark_series:
            series = list(shared_benchmark_series[ticker])
            source = "hedgemate_benchmark_raw"
        else:
            series = list(cached_series.get(ticker, []))
            if not series:
                fetched = fetch_yahoo_chart(ticker, period1, period2)
                time.sleep(0.4)
                series = [(row["date"], row["adj_close"]) for row in fetched if row.get("adj_close") is not None and row.get("adj_close") > 0]
                source = "yahoo"

        if not series:
            continue

        unaligned_series_map[ticker] = [(date_str, close, source) for date_str, close in series]

    anchor_date, anchor_metadata = choose_aligned_market_anchor(
        {ticker: [(date_str, close) for date_str, close, _ in series] for ticker, series in unaligned_series_map.items()}
    )
    unaligned_series_map, anchor_forward_fills = apply_anchor_forward_fills(unaligned_series_map, anchor_date)
    anchor_date, anchor_metadata = choose_aligned_market_anchor(
        {ticker: [(date_str, close) for date_str, close, _ in series] for ticker, series in unaligned_series_map.items()}
    )
    expected_tickers = sorted(spec_map.keys())
    loaded_tickers = sorted(unaligned_series_map.keys())
    missing_tickers_total = sorted(set(expected_tickers) - set(loaded_tickers))
    anchor_missing_tickers = anchor_metadata.get("tickers_missing_on_anchor_date", [])
    data_quality_status = "OK" if not missing_tickers_total and not anchor_missing_tickers else "DEGRADED"
    anchor_metadata.update(
        {
            "expected_ticker_count": len(expected_tickers),
            "expected_tickers": expected_tickers,
            "loaded_ticker_count": len(loaded_tickers),
            "loaded_tickers": loaded_tickers,
            "missing_tickers_total": missing_tickers_total,
            "anchor_forward_fills": anchor_forward_fills,
            "data_quality_status": data_quality_status,
            "universe_breadth_source_ticker_count": len(universe_series_map),
            "universe_breadth_asset_class_counts": {
                asset_class: sum(1 for ticker in universe_series_map if universe_asset_class_by_ticker.get(ticker) == asset_class)
                for asset_class in sorted(set(universe_asset_class_by_ticker.values()))
            },
            "shared_raw_files": {
                "market": str(shared_market_file),
                "market_mode": shared_market_file_mode,
                "benchmark": str(shared_benchmark_file),
                "benchmark_mode": shared_benchmark_file_mode,
                "fx": str(shared_fx_file),
                "fx_mode": shared_fx_file_mode,
            },
        }
    )

    rows = []
    series_map = {}
    for ticker, series in unaligned_series_map.items():
        aligned_series = [(date_str, close) for date_str, close, _ in series if anchor_date is None or date_str <= anchor_date]
        if not aligned_series:
            continue
        series_map[ticker] = aligned_series
        for date_str, close, row_source in series:
            if anchor_date is not None and date_str > anchor_date:
                continue
            rows.append(
                {
                    "date": date_str,
                    "ticker": ticker,
                    "label": spec_map[ticker]["label"],
                    "close": close,
                    "source": row_source,
                    "currency": spec_map[ticker]["currency"],
                    "ingested_at": ingested_at,
                }
            )

    breadth_series_map, breadth_metadata = build_market_breadth_series(
        universe_series_map,
        universe_asset_class_by_ticker,
        anchor_date=anchor_date,
    )
    series_map.update(breadth_series_map)
    anchor_metadata["synthetic_breadth_series"] = breadth_metadata

    synthetic_basket_map, synthetic_basket_metadata = build_synthetic_basket_series(
        series_map,
        anchor_date=anchor_date,
    )
    series_map.update(synthetic_basket_map)
    anchor_metadata["synthetic_basket_series"] = synthetic_basket_metadata

    indicator_observations, external_sources = load_external_indicator_observations()
    market_calendar_dates = sorted({date_str for series in series_map.values() for date_str, _ in series})
    external_indicator_map, external_indicator_metadata = build_low_frequency_indicator_series(
        market_calendar_dates,
        anchor_date=anchor_date,
        observations_by_ticker=indicator_observations,
    )
    series_map.update(external_indicator_map)
    anchor_metadata["low_frequency_indicator_series"] = external_indicator_metadata
    anchor_metadata["low_frequency_indicator_sources"] = external_sources

    save_market_state_raw(raw_file, rows)
    return raw_file, series_map, anchor_metadata


def build_data_quality_note(anchor_metadata):
    anchor_date = anchor_metadata.get("anchor_date")
    coverage_ratio = anchor_metadata.get("anchor_ticker_coverage_ratio", 0.0)
    anchor_count = anchor_metadata.get("anchor_ticker_count", 0)
    total_tickers = anchor_metadata.get("total_tickers", 0)
    expected_count = anchor_metadata.get("expected_ticker_count", total_tickers)
    loaded_count = anchor_metadata.get("loaded_ticker_count", total_tickers)
    missing_total = anchor_metadata.get("missing_tickers_total", [])
    missing_on_anchor = anchor_metadata.get("tickers_missing_on_anchor_date", [])
    after_anchor = anchor_metadata.get("tickers_after_anchor_date", {})
    anchor_forward_fills = anchor_metadata.get("anchor_forward_fills", [])
    data_quality_status = anchor_metadata.get("data_quality_status", "UNKNOWN")
    universe_count = anchor_metadata.get("universe_breadth_source_ticker_count", 0)
    breadth_series = anchor_metadata.get("synthetic_breadth_series", [])
    basket_series = anchor_metadata.get("synthetic_basket_series", [])
    low_frequency_indicators = anchor_metadata.get("low_frequency_indicator_series", [])
    low_frequency_sources = anchor_metadata.get("low_frequency_indicator_sources", [])
    shared_raw_files = anchor_metadata.get("shared_raw_files", {})

    lines = [
        "",
        "## 데이터 커버리지 메모",
        f"- quality status: `{data_quality_status}`",
        f"- 정렬 기준일: `{anchor_date}`",
        f"- anchor coverage: {anchor_count}/{total_tickers} ({coverage_ratio * 100:.1f}%)",
        f"- expected/loaded tickers: {loaded_count}/{expected_count}",
        f"- 70개 자산 breadth 원천 ticker 수: {universe_count}",
    ]
    if shared_raw_files:
        fallback_modes = [
            f"{name}:{shared_raw_files.get(name + '_mode')}"
            for name in ("market", "benchmark", "fx")
            if shared_raw_files.get(name + "_mode") not in (None, "exact")
        ]
        if fallback_modes:
            lines.append(f"- shared raw fallback 사용: `{', '.join(fallback_modes)}`")
    if breadth_series:
        latest_parts = []
        for item in breadth_series:
            latest_value = item.get("latest_value")
            if latest_value is None:
                continue
            latest_parts.append(f"{item.get('ticker')}={latest_value * 100:.1f}%")
        if latest_parts:
            lines.append(f"- synthetic breadth latest: `{', '.join(latest_parts)}`")
    if basket_series:
        latest_parts = []
        for item in basket_series:
            latest_value = item.get("latest_value")
            if latest_value is None:
                continue
            latest_parts.append(f"{item.get('ticker')}={latest_value:.2f} ({item.get('loaded_members') or '-'})")
        if latest_parts:
            lines.append(f"- synthetic basket latest: `{', '.join(latest_parts)}`")
    if low_frequency_indicators:
        indicator_parts = []
        for item in low_frequency_indicators:
            if item.get("status") != "OK":
                continue
            indicator_parts.append(
                f"{item.get('ticker')}:last={item.get('last_observed_date')}, stale={item.get('staleness_days')}d, source_quality={item.get('source_quality') or 'unknown'}"
            )
        if indicator_parts:
            lines.append(f"- low-frequency indicators forward-filled: `{', '.join(indicator_parts)}`")
        missing_indicators = [item.get("ticker") for item in low_frequency_indicators if item.get("status") != "OK"]
        if missing_indicators:
            lines.append(f"- low-frequency indicators missing: `{', '.join(missing_indicators)}`")
    if low_frequency_sources:
        lines.append(f"- low-frequency/event sources: `{', '.join(low_frequency_sources)}`")
    if missing_total:
        lines.append(f"- 전체 기간에서 로드되지 않은 ticker: `{', '.join(missing_total)}`")
    if missing_on_anchor:
        lines.append(f"- anchor date에 없어 제외된 ticker: `{', '.join(missing_on_anchor)}`")
    if anchor_forward_fills:
        fill_text = ", ".join(
            f"{row.get('ticker')}:{row.get('filled_date')}<={row.get('source_date')}"
            for row in anchor_forward_fills
        )
        lines.append(f"- anchor gap 보정 ticker: `{fill_text}`")
    if after_anchor:
        formatted = ", ".join(f"{ticker}:{date}" for ticker, date in after_anchor.items())
        lines.append(f"- anchor date보다 최신 관측치가 별도로 있는 ticker: `{formatted}`")
    lines.append("- 이 summary는 데이터 coverage가 낮거나 특정 핵심 ticker가 빠진 경우 보수적으로 해석해야 합니다.")
    return "\n".join(lines) + "\n"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Run the standalone market-state scenario pipeline.")
    parser.add_argument("--run-id", default=None, help="Optional run id for output file names.")
    parser.add_argument("--data-version", default=None, help="Data snapshot date in YYYYMMDD. Defaults to today.")
    parser.add_argument("--lookback-years", type=int, default=5, help="Historical lookback window for Yahoo fetches.")
    parser.add_argument(
        "--skip-shared-cache",
        action="store_true",
        help="Do not reuse HedgeMate raw/FX snapshots even if they exist.",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    run_ts = now_utc()
    run_id = args.run_id or build_run_id(run_ts)
    data_version = args.data_version or run_ts.strftime("%Y%m%d")
    ingested_at = run_ts.isoformat()

    OUTPUT_RAW_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_SCENARIO_VECTOR_DIR.mkdir(parents=True, exist_ok=True)

    start_dt = (run_ts - timedelta(days=365 * max(1, args.lookback_years) + 10)).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    end_dt = run_ts + timedelta(days=1)
    period1 = int(start_dt.timestamp())
    period2 = int(end_dt.timestamp())

    raw_file, market_series_map, anchor_metadata = build_market_state_raw(
        period1=period1,
        period2=period2,
        data_version=data_version,
        ingested_at=ingested_at,
        reuse_shared_cache=not args.skip_shared_cache,
    )
    outputs = build_market_state_phase1_to4(market_series_map)
    summary_md = outputs["summary_md"] + build_data_quality_note(anchor_metadata)

    scenario_registry_csv = OUTPUT_PROCESSED_DIR / f"scenario_registry_{run_id}.csv"
    scenario_feature_csv = OUTPUT_PROCESSED_DIR / f"scenario_feature_daily_{run_id}.csv"
    scenario_state_csv = OUTPUT_PROCESSED_DIR / f"scenario_state_daily_{run_id}.csv"
    market_factor_csv = OUTPUT_PROCESSED_DIR / f"market_factor_daily_{run_id}.csv"
    scenario_driver_csv = OUTPUT_REPORT_DIR / f"scenario_driver_table_{run_id}.csv"
    scenario_summary_md = OUTPUT_REPORT_DIR / f"daily_market_state_summary_{run_id}.md"
    snapshot_metadata_json = OUTPUT_REPORT_DIR / f"scenario_snapshot_metadata_{run_id}.json"
    scenario_vector_csv = OUTPUT_SCENARIO_VECTOR_DIR / f"current_scenario_vector_{run_id}.csv"
    scenario_vector_json = OUTPUT_SCENARIO_VECTOR_DIR / f"current_scenario_vector_{run_id}.json"
    expected_scenario_count = len({row["scenario_code"] for row in outputs["registry_rows"]})

    write_csv(scenario_registry_csv, SCENARIO_REGISTRY_FIELDS, outputs["registry_rows"])
    write_csv(scenario_feature_csv, SCENARIO_FEATURE_FIELDS, outputs["feature_rows"])
    write_csv(scenario_state_csv, SCENARIO_STATE_FIELDS, outputs["state_rows"])
    write_csv(market_factor_csv, MARKET_FACTOR_FIELDS, outputs["factor_rows"])
    write_csv(scenario_driver_csv, SCENARIO_DRIVER_FIELDS, outputs["driver_rows"])
    scenario_vector_rows = build_current_scenario_vector_rows(outputs["state_rows"], outputs["driver_rows"])
    scenario_vector_as_of_date = max((row["as_of_date"] for row in scenario_vector_rows), default="")
    latest_vector_rows = [
        row for row in scenario_vector_rows if row.get("as_of_date") == scenario_vector_as_of_date
    ]
    scenario_count = len({row["scenario_code"] for row in latest_vector_rows})
    write_csv(scenario_vector_csv, SCENARIO_VECTOR_FIELDS, scenario_vector_rows)
    scenario_vector_json.write_text(json.dumps(scenario_vector_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    scenario_summary_md.write_text(summary_md, encoding="utf-8")
    snapshot_metadata_json.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "pipeline_phase": "phase4_structured_scenario_vector",
                "api_free": True,
                "diagnostic_only": True,
                "engine_version": ENGINE_VERSION,
                "data_version": data_version,
                "generated_at": ingested_at,
                "created_at": ingested_at,
                "expected_scenario_count": expected_scenario_count,
                "scenario_count": scenario_count,
                "scenario_vector_row_count": len(scenario_vector_rows),
                "scenario_vector_latest_row_count": len(latest_vector_rows),
                "scenario_vector_as_of_date": scenario_vector_as_of_date,
                "scenario_codes": sorted({row["scenario_code"] for row in latest_vector_rows}),
                "scenario_state_csv": str(scenario_state_csv),
                "scenario_feature_csv": str(scenario_feature_csv),
                "market_factor_csv": str(market_factor_csv),
                "scenario_driver_csv": str(scenario_driver_csv),
                "scenario_summary_md": str(scenario_summary_md),
                "scenario_vector_csv": str(scenario_vector_csv),
                "scenario_vector_json": str(scenario_vector_json),
                **anchor_metadata,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    update_latest_manifest(
        {
            "active_scenario_run": run_id,
            "active_scenario_vector": scenario_vector_csv.name,
            "active_scenario_vector_path": f"scenario_vectors/{scenario_vector_csv.name}",
            "active_scenario_vector_json": scenario_vector_json.name,
            "active_scenario_vector_json_path": f"scenario_vectors/{scenario_vector_json.name}",
            "scenario_version": "v2" if scenario_count >= 10 else "v1",
            "scenario_count": scenario_count,
            "scenario_vector_as_of_date": scenario_vector_as_of_date,
        }
    )

    print("DONE")
    print(f"RAW={raw_file}")
    print(f"SCENARIO_REGISTRY={scenario_registry_csv}")
    print(f"SCENARIO_FEATURE={scenario_feature_csv}")
    print(f"SCENARIO_STATE={scenario_state_csv}")
    print(f"MARKET_FACTOR={market_factor_csv}")
    print(f"SCENARIO_DRIVER={scenario_driver_csv}")
    print(f"SCENARIO_VECTOR_CSV={scenario_vector_csv}")
    print(f"SCENARIO_VECTOR_JSON={scenario_vector_json}")
    print(f"SCENARIO_SUMMARY={scenario_summary_md}")
    print(f"SNAPSHOT_METADATA={snapshot_metadata_json}")


if __name__ == "__main__":
    main()
