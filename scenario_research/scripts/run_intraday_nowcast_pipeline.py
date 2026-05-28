#!/usr/bin/env python3
"""Run the 1-hour intraday nowcast pipeline.

This is a Korea-focused, provisional overlay for same-day market reading.  It is
not a replacement for the daily confirmed Scenario Research regime.  Outputs are
separate so HedgeMate can later consume both:

    daily confirmed scenario vector + intraday nowcast vector
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from intraday_nowcast_engine import (
    INTRADAY_RAW_FIELDS,
    INTRADAY_TICKER_FEATURE_FIELDS,
    KST,
    NOWCAST_ENGINE_VERSION,
    NOWCAST_SIGNAL_FIELDS,
    NOWCAST_TICKER_SPECS,
    NOWCAST_VECTOR_FIELDS,
    build_nowcast_outputs,
    load_csv,
    render_intraday_dashboard,
    write_csv,
    write_json,
)


SCENARIO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_RAW_DIR = SCENARIO_ROOT / "outputs" / "raw"
OUTPUT_PROCESSED_DIR = SCENARIO_ROOT / "outputs" / "processed"
OUTPUT_REPORT_DIR = SCENARIO_ROOT / "outputs" / "reports"
OUTPUT_NOWCAST_VECTOR_DIR = SCENARIO_ROOT / "outputs" / "nowcast_vectors"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def build_run_id(run_ts: datetime | None = None) -> str:
    ts = run_ts or now_utc()
    return f"{ts.strftime('%Y%m%dT%H%M%S%f')}-{uuid.uuid4().hex[:8]}"


def parse_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def fetch_yahoo_intraday_chart(
    ticker: str,
    period1: int,
    period2: int,
    *,
    interval: str = "1h",
    retries: int = 5,
    sleep_base: float = 0.5,
) -> list[dict[str, object]]:
    encoded_ticker = urllib.parse.quote(ticker, safe="")
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded_ticker}"
        f"?period1={period1}&period2={period2}&interval={urllib.parse.quote(interval)}"
        "&includePrePost=false&events=div%2Csplits"
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
            time.sleep(min(sleep_base * (2**attempt), 10.0))
            continue

        result = payload.get("chart", {}).get("result", [])
        if not result:
            return []
        root = result[0]
        timestamps = root.get("timestamp", []) or []
        quote = root.get("indicators", {}).get("quote", [{}])[0]
        opens = quote.get("open", []) or []
        highs = quote.get("high", []) or []
        lows = quote.get("low", []) or []
        closes = quote.get("close", []) or []
        volumes = quote.get("volume", []) or []

        rows: list[dict[str, object]] = []
        for index, ts in enumerate(timestamps):
            close = closes[index] if index < len(closes) else None
            if close is None:
                continue
            dt_utc = datetime.fromtimestamp(ts, tz=timezone.utc)
            dt_kst = dt_utc.astimezone(KST)
            rows.append(
                {
                    "timestamp_utc": dt_utc.isoformat(),
                    "timestamp_kst": dt_kst.isoformat(),
                    "date_kst": dt_kst.date().isoformat(),
                    "hour_kst": dt_kst.strftime("%H:%M"),
                    "open": opens[index] if index < len(opens) else "",
                    "high": highs[index] if index < len(highs) else "",
                    "low": lows[index] if index < len(lows) else "",
                    "close": close,
                    "volume": volumes[index] if index < len(volumes) else "",
                }
            )
        return rows
    return []


def enrich_rows(
    ticker: str,
    rows: list[dict[str, object]],
    *,
    source: str,
    ingested_at: str,
) -> list[dict[str, object]]:
    spec = next((item for item in NOWCAST_TICKER_SPECS if item["ticker"] == ticker), {})
    out = []
    for row in rows:
        enriched = {
            "timestamp_utc": row.get("timestamp_utc"),
            "timestamp_kst": row.get("timestamp_kst"),
            "date_kst": row.get("date_kst"),
            "hour_kst": row.get("hour_kst"),
            "ticker": ticker,
            "label": spec.get("label", ticker),
            "asset_class": spec.get("asset_class", ""),
            "lens": spec.get("lens", ""),
            "open": row.get("open", ""),
            "high": row.get("high", ""),
            "low": row.get("low", ""),
            "close": row.get("close", ""),
            "volume": row.get("volume", ""),
            "currency": spec.get("currency", ""),
            "source": source,
            "ingested_at": ingested_at,
        }
        out.append(enriched)
    return out


def filter_recent_rows(rows: list[dict[str, object]], lookback_days: int) -> list[dict[str, object]]:
    if not rows:
        return []
    latest = max(str(row.get("timestamp_utc", "")) for row in rows)
    try:
        latest_dt = datetime.fromisoformat(latest.replace("Z", "+00:00"))
    except ValueError:
        return rows
    cutoff = latest_dt - timedelta(days=lookback_days)
    out = []
    for row in rows:
        try:
            ts = datetime.fromisoformat(str(row.get("timestamp_utc", "")).replace("Z", "+00:00"))
        except ValueError:
            continue
        if ts >= cutoff:
            out.append(row)
    return out


def read_input_raw(path: Path, lookback_days: int) -> list[dict[str, object]]:
    rows = load_csv(path)
    return filter_recent_rows(rows, lookback_days)


def collect_intraday_raw(
    *,
    data_version: str,
    run_ts: datetime,
    lookback_days: int,
    interval: str,
    tickers: list[str],
    reuse_raw: bool,
) -> tuple[Path, list[dict[str, object]], dict[str, object]]:
    raw_path = OUTPUT_RAW_DIR / f"raw_intraday_market_state_{interval}_{data_version}.csv"
    if reuse_raw and raw_path.exists():
        rows = read_input_raw(raw_path, lookback_days)
        return raw_path, rows, {"collection_mode": "reuse_raw", "fetched_tickers": sorted({row.get("ticker") for row in rows})}

    period2 = int((run_ts + timedelta(hours=2)).timestamp())
    period1 = int((run_ts - timedelta(days=max(2, lookback_days))).timestamp())
    ingested_at = run_ts.isoformat()
    all_rows: list[dict[str, object]] = []
    fetched_tickers: list[str] = []
    failed_tickers: list[str] = []
    for ticker in tickers:
        fetched = fetch_yahoo_intraday_chart(ticker, period1, period2, interval=interval)
        if fetched:
            fetched_tickers.append(ticker)
            all_rows.extend(enrich_rows(ticker, fetched, source="yahoo_intraday", ingested_at=ingested_at))
        else:
            failed_tickers.append(ticker)
        time.sleep(0.25)

    all_rows.sort(key=lambda row: (str(row.get("ticker")), str(row.get("timestamp_utc"))))
    write_csv(raw_path, INTRADAY_RAW_FIELDS, all_rows)
    return (
        raw_path,
        all_rows,
        {
            "collection_mode": "fetch_yahoo_intraday",
            "interval": interval,
            "period1": period1,
            "period2": period2,
            "fetched_tickers": fetched_tickers,
            "failed_tickers": failed_tickers,
        },
    )


def parse_tickers(value: str | None) -> list[str]:
    if not value:
        return [spec["ticker"] for spec in NOWCAST_TICKER_SPECS]
    requested = [item.strip() for item in value.split(",") if item.strip()]
    known = {spec["ticker"] for spec in NOWCAST_TICKER_SPECS}
    return [ticker for ticker in requested if ticker in known]


def run_pipeline(args: argparse.Namespace) -> dict[str, Path]:
    run_ts = now_utc()
    run_id = args.run_id or build_run_id(run_ts)
    data_version = args.data_version or run_ts.astimezone(KST).strftime("%Y%m%d")
    interval = args.interval
    tickers = parse_tickers(args.tickers)

    OUTPUT_RAW_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_NOWCAST_VECTOR_DIR.mkdir(parents=True, exist_ok=True)

    if args.input_raw:
        raw_path = args.input_raw
        raw_rows = read_input_raw(raw_path, args.lookback_days)
        collection_metadata = {"collection_mode": "input_raw", "input_raw": str(raw_path)}
    else:
        raw_path, raw_rows, collection_metadata = collect_intraday_raw(
            data_version=data_version,
            run_ts=run_ts,
            lookback_days=args.lookback_days,
            interval=interval,
            tickers=tickers,
            reuse_raw=args.reuse_raw,
        )

    ticker_feature_rows, signal_rows, vector_rows = build_nowcast_outputs(raw_rows)

    suffix = f"{interval}_{run_id}"
    ticker_feature_path = OUTPUT_PROCESSED_DIR / f"intraday_ticker_feature_{suffix}.csv"
    signal_path = OUTPUT_PROCESSED_DIR / f"intraday_nowcast_signal_{suffix}.csv"
    vector_csv_path = OUTPUT_NOWCAST_VECTOR_DIR / f"current_intraday_nowcast_{suffix}.csv"
    vector_json_path = OUTPUT_NOWCAST_VECTOR_DIR / f"current_intraday_nowcast_{suffix}.json"
    metadata_path = OUTPUT_REPORT_DIR / f"intraday_nowcast_metadata_{suffix}.json"
    dashboard_path = OUTPUT_REPORT_DIR / f"intraday_nowcast_dashboard_{suffix}.html"

    write_csv(ticker_feature_path, INTRADAY_TICKER_FEATURE_FIELDS, ticker_feature_rows)
    write_csv(signal_path, NOWCAST_SIGNAL_FIELDS, signal_rows)
    write_csv(vector_csv_path, NOWCAST_VECTOR_FIELDS, vector_rows)
    write_json(vector_json_path, vector_rows)

    metadata = {
        "data_version": data_version,
        "run_id": run_id,
        "generated_at": run_ts.isoformat(),
        "interval": interval,
        "lookback_days": args.lookback_days,
        "engine_version": NOWCAST_ENGINE_VERSION,
        "requested_ticker_count": len(tickers),
        "requested_tickers": tickers,
        "raw_row_count": len(raw_rows),
        "ticker_feature_count": len(ticker_feature_rows),
        "nowcast_count": len(vector_rows),
        "fetched_ticker_count": len({row.get("ticker") for row in raw_rows}),
        "fetched_tickers": sorted({str(row.get("ticker")) for row in raw_rows}),
        "latest_timestamp_kst": vector_rows[0]["as_of_kst"] if vector_rows else None,
        "raw_path": str(raw_path),
        "ticker_feature_path": str(ticker_feature_path),
        "signal_path": str(signal_path),
        "vector_csv_path": str(vector_csv_path),
        "vector_json_path": str(vector_json_path),
        "dashboard_path": str(dashboard_path),
        **collection_metadata,
    }
    write_json(metadata_path, metadata)

    render_intraday_dashboard(
        dashboard_path,
        run_id=run_id,
        raw_path=raw_path,
        ticker_feature_path=ticker_feature_path,
        signal_path=signal_path,
        vector_path=vector_csv_path,
        metadata_path=metadata_path,
        ticker_features=ticker_feature_rows,
        signal_rows=signal_rows,
        vector_rows=vector_rows,
        metadata=metadata,
    )

    return {
        "raw": raw_path,
        "ticker_feature": ticker_feature_path,
        "signal": signal_path,
        "vector_csv": vector_csv_path,
        "vector_json": vector_json_path,
        "metadata": metadata_path,
        "dashboard": dashboard_path,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--data-version", default=None, help="YYYYMMDD snapshot date. Defaults to today's KST date.")
    parser.add_argument("--lookback-days", type=int, default=7)
    parser.add_argument("--interval", default="1h", choices=["1h"], help="Intraday bar interval. Currently only 1h is supported.")
    parser.add_argument("--tickers", default=None, help="Optional comma-separated subset from the nowcast ticker universe.")
    parser.add_argument("--input-raw", type=Path, default=None, help="Build outputs from an existing raw_intraday CSV instead of fetching.")
    parser.add_argument("--reuse-raw", action="store_true", help="Reuse outputs/raw/raw_intraday_market_state_<interval>_<data_version>.csv if present.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    outputs = run_pipeline(args)
    print("DONE")
    for key, value in outputs.items():
        print(f"{key.upper()}={value}")


if __name__ == "__main__":
    main()
