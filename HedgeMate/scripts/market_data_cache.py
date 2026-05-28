#!/usr/bin/env python3
"""Incremental raw market data cache utilities for HedgeMate.

This module is intentionally narrower than the product refresh pipeline. It
updates only raw market prices and writes a small manifest so UI freshness can
be judged from the latest available market date.
"""

import csv
import json
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date, datetime, time as dt_time, timedelta, timezone
from pathlib import Path


RAW_MARKET_COLUMNS = [
    "date",
    "ticker",
    "asset_class",
    "source",
    "open",
    "high",
    "low",
    "close",
    "adj_close",
    "volume",
    "currency",
    "ingested_at",
]


def parse_float(value):
    if value in (None, ""):
        return None
    try:
        if isinstance(value, str):
            value = value.replace(",", "")
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_number(value):
    if value is None:
        return ""
    return value


def yyyymmdd(value):
    if isinstance(value, datetime):
        return value.strftime("%Y%m%d")
    if isinstance(value, date):
        return value.strftime("%Y%m%d")
    text = str(value or "").strip()
    return text if text else datetime.now().strftime("%Y%m%d")


def latest_raw_market_snapshot(output_dir, exclude_data_version=None):
    output_dir = Path(output_dir)
    excluded = f"raw_market_daily_{exclude_data_version}.csv" if exclude_data_version else None
    paths = [
        path
        for path in output_dir.glob("raw_market_daily_*.csv")
        if path.is_file() and path.name != excluded
    ]
    if not paths:
        return None
    return max(paths, key=lambda path: (path.stat().st_mtime, path.name))


def raw_market_manifest_path(output_dir, data_version):
    return Path(output_dir) / f"raw_market_daily_{data_version}_manifest.json"


def latest_raw_market_manifest(output_dir):
    output_dir = Path(output_dir)
    paths = [
        path
        for path in output_dir.glob("raw_market_daily_*_manifest.json")
        if path.is_file()
    ]
    if not paths:
        return None, {}
    path = max(paths, key=lambda item: (item.stat().st_mtime, item.name))
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = {}
    return path, payload if isinstance(payload, dict) else {}


def expected_latest_market_date(reference_dt=None):
    """Return the latest completed global trading date for a Korea-local UI.

    The dashboard often runs before the current US session has closed, so the
    previous weekday is the conservative default freshness anchor.
    """

    if reference_dt is None:
        reference = datetime.now().date()
    elif isinstance(reference_dt, datetime):
        reference = reference_dt.date()
    else:
        reference = reference_dt
    expected = reference - timedelta(days=1)
    while expected.weekday() >= 5:
        expected -= timedelta(days=1)
    return expected.isoformat()


def fetch_yahoo_chart(ticker, start_date, end_date, retries=3):
    start_dt = datetime.combine(start_date, dt_time.min, tzinfo=timezone.utc)
    # Yahoo's period2 is exclusive.
    end_dt = datetime.combine(end_date + timedelta(days=1), dt_time.min, tzinfo=timezone.utc)
    period1 = int(start_dt.timestamp())
    period2 = int(end_dt.timestamp())
    encoded_ticker = urllib.parse.quote(str(ticker), safe="")
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded_ticker}"
        f"?period1={period1}&period2={period2}&interval=1d&events=div%2Csplits"
    )
    for attempt in range(1, retries + 1):
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                result = payload.get("chart", {}).get("result", [])
                if not result:
                    return []
                r0 = result[0]
                timestamps = r0.get("timestamp", [])
                quote = r0.get("indicators", {}).get("quote", [{}])[0]
                adj_close_list = (
                    r0.get("indicators", {}).get("adjclose", [{}])[0].get("adjclose", [])
                )
                opens = quote.get("open", [])
                highs = quote.get("high", [])
                lows = quote.get("low", [])
                closes = quote.get("close", [])
                volumes = quote.get("volume", [])
                rows = []
                for idx, ts in enumerate(timestamps):
                    row_date = datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
                    close = closes[idx] if idx < len(closes) else None
                    if close is None:
                        continue
                    adj_close = adj_close_list[idx] if idx < len(adj_close_list) else None
                    rows.append(
                        {
                            "date": row_date,
                            "open": opens[idx] if idx < len(opens) else None,
                            "high": highs[idx] if idx < len(highs) else None,
                            "low": lows[idx] if idx < len(lows) else None,
                            "close": close,
                            "adj_close": adj_close if adj_close is not None else close,
                            "volume": volumes[idx] if idx < len(volumes) else None,
                        }
                    )
                return rows
        except Exception:
            if attempt == retries:
                return []
            time.sleep(min(2**attempt, 10))
    return []


def read_raw_market_rows(path):
    rows = []
    latest_by_ticker = {}
    if not path or not Path(path).exists():
        return rows, latest_by_ticker
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ticker = str(row.get("ticker") or "").strip()
            row_date = str(row.get("date") or "").strip()
            if not ticker or not row_date:
                continue
            parsed = {
                "date": row_date,
                "ticker": ticker,
                "asset_class": row.get("asset_class") or "",
                "source": row.get("source") or "yahoo",
                "open": parse_float(row.get("open")),
                "high": parse_float(row.get("high")),
                "low": parse_float(row.get("low")),
                "close": parse_float(row.get("close")),
                "adj_close": parse_float(row.get("adj_close")),
                "volume": parse_float(row.get("volume")),
                "currency": row.get("currency") or "",
                "ingested_at": row.get("ingested_at") or "",
            }
            rows.append(parsed)
            if row_date > latest_by_ticker.get(ticker, ""):
                latest_by_ticker[ticker] = row_date
    return rows, latest_by_ticker


def write_raw_market_rows(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=RAW_MARKET_COLUMNS)
        writer.writeheader()
        for row in sorted(rows, key=lambda item: (item.get("ticker", ""), item.get("date", ""))):
            writer.writerow({column: safe_number(row.get(column)) for column in RAW_MARKET_COLUMNS})


def build_market_cache_summary(rows, universe_tickers, expected_date):
    latest_by_ticker = {}
    for row in rows:
        ticker = str(row.get("ticker") or "").strip()
        row_date = str(row.get("date") or "").strip()
        if ticker and row_date and row_date > latest_by_ticker.get(ticker, ""):
            latest_by_ticker[ticker] = row_date
    covered_dates = [
        latest_by_ticker[ticker]
        for ticker in universe_tickers
        if latest_by_ticker.get(ticker)
    ]
    stale_tickers = [
        ticker
        for ticker in universe_tickers
        if latest_by_ticker.get(ticker, "") < expected_date
    ]
    latest_market_date = min(covered_dates) if covered_dates else None
    max_market_date = max(covered_dates) if covered_dates else None
    coverage_ratio = (len(universe_tickers) - len(stale_tickers)) / len(universe_tickers) if universe_tickers else 0.0
    return {
        "latestMarketDate": latest_market_date,
        "maxMarketDate": max_market_date,
        "latestByTicker": latest_by_ticker,
        "staleTickers": stale_tickers,
        "tickerCoverageRatio": coverage_ratio,
    }


def incremental_update_raw_market_data(
    universe_rows,
    output_dir,
    data_version=None,
    source_snapshot=None,
    target_latest_date=None,
    ingested_at=None,
    progress_callback=None,
    fetcher=None,
):
    started = time.perf_counter()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    data_version = yyyymmdd(data_version or datetime.now())
    target_latest_date = target_latest_date or expected_latest_market_date()
    target_date_obj = datetime.strptime(target_latest_date, "%Y-%m-%d").date()
    ingested_at = ingested_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    fetcher = fetcher or fetch_yahoo_chart

    universe = [
        row
        for row in universe_rows
        if str(row.get("ticker") or "").strip() and str(row.get("ticker") or "").strip() != "__CASH__"
    ]
    universe_by_ticker = {str(row.get("ticker") or "").strip(): row for row in universe}
    universe_tickers = list(universe_by_ticker.keys())

    target_snapshot = output_dir / f"raw_market_daily_{data_version}.csv"
    if source_snapshot is None:
        if target_snapshot.exists():
            source_snapshot = target_snapshot
        else:
            source_snapshot = latest_raw_market_snapshot(output_dir)
    source_snapshot = Path(source_snapshot) if source_snapshot else None
    if not source_snapshot or not source_snapshot.exists():
        raise FileNotFoundError("No existing raw_market_daily snapshot is available for incremental update.")

    if progress_callback:
        progress_callback(
            {
                "stage": "cache loading",
                "currentStep": f"reading {source_snapshot.name}",
                "totalTickers": len(universe_tickers),
                "latestMarketDate": target_latest_date,
            }
        )

    existing_rows, latest_by_ticker = read_raw_market_rows(source_snapshot)
    merged = {(row["date"], row["ticker"]): row for row in existing_rows}
    rows_added = 0
    fetched_tickers = 0
    skipped_tickers = 0
    failed_tickers = []

    if progress_callback:
        progress_callback(
            {
                "stage": "latest market date check",
                "currentStep": f"target latest market date {target_latest_date}",
                "totalTickers": len(universe_tickers),
                "latestMarketDate": target_latest_date,
            }
        )

    for idx, ticker in enumerate(universe_tickers, start=1):
        last_date = latest_by_ticker.get(ticker)
        if not last_date:
            failed_tickers.append({"ticker": ticker, "reason": "missing_existing_history"})
            continue
        try:
            last_date_obj = datetime.strptime(last_date, "%Y-%m-%d").date()
        except ValueError:
            failed_tickers.append({"ticker": ticker, "reason": f"invalid_last_date:{last_date}"})
            continue
        if last_date_obj >= target_date_obj:
            skipped_tickers += 1
            continue

        start_date = last_date_obj + timedelta(days=1)
        if progress_callback:
            progress_callback(
                {
                    "stage": "fetching incremental prices",
                    "currentStep": f"fetching {idx}/{len(universe_tickers)} {ticker}",
                    "fetchedTickers": fetched_tickers,
                    "totalTickers": len(universe_tickers),
                    "ticker": ticker,
                    "fromDate": start_date.isoformat(),
                    "toDate": target_latest_date,
                }
            )
        try:
            fetched_rows = fetcher(ticker, start_date, target_date_obj)
        except TypeError:
            fetched_rows = fetcher(ticker, start_date, target_date_obj, retries=3)
        except Exception as exc:
            failed_tickers.append({"ticker": ticker, "reason": str(exc) or "fetch_error"})
            continue
        fetched_tickers += 1
        if not fetched_rows:
            failed_tickers.append({"ticker": ticker, "reason": "no_new_rows_returned"})
            continue
        meta = universe_by_ticker[ticker]
        for raw in fetched_rows:
            row_date = str(raw.get("date") or "").strip()
            if not row_date or row_date <= last_date or row_date > target_latest_date:
                continue
            row = {
                "date": row_date,
                "ticker": ticker,
                "asset_class": meta.get("asset_class") or "",
                "source": "yahoo_incremental",
                "open": raw.get("open"),
                "high": raw.get("high"),
                "low": raw.get("low"),
                "close": raw.get("close"),
                "adj_close": raw.get("adj_close"),
                "volume": raw.get("volume"),
                "currency": meta.get("currency") or "",
                "ingested_at": ingested_at,
            }
            key = (row["date"], ticker)
            if key not in merged:
                rows_added += 1
            merged[key] = row

    if progress_callback:
        progress_callback(
            {
                "stage": "merging cache",
                "currentStep": "deduping and writing raw market cache",
                "fetchedTickers": fetched_tickers,
                "totalTickers": len(universe_tickers),
            }
        )

    merged_rows = list(merged.values())
    same_snapshot = source_snapshot.resolve() == target_snapshot.resolve()
    if not (rows_added == 0 and same_snapshot):
        write_raw_market_rows(target_snapshot, merged_rows)
    summary = build_market_cache_summary(merged_rows, universe_tickers, target_latest_date)
    manifest = {
        "manifestVersion": "raw_market_incremental_v1",
        "dataVersion": data_version,
        "sourceSnapshot": str(source_snapshot),
        "outputSnapshot": str(target_snapshot),
        "targetLatestMarketDate": target_latest_date,
        "latestMarketDate": summary["latestMarketDate"],
        "maxMarketDate": summary["maxMarketDate"],
        "rowsAdded": rows_added,
        "existingRows": len(existing_rows),
        "outputRows": len(merged_rows),
        "totalTickers": len(universe_tickers),
        "fetchedTickers": fetched_tickers,
        "skippedTickers": skipped_tickers,
        "failedTickers": failed_tickers,
        "staleTickers": summary["staleTickers"],
        "tickerCoverageRatio": summary["tickerCoverageRatio"],
        "durationSeconds": round(time.perf_counter() - started, 3),
        "generatedAtUtc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    manifest_path = raw_market_manifest_path(output_dir, data_version)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    if progress_callback:
        progress_callback(
            {
                "stage": "complete",
                "currentStep": "raw market cache updated",
                "fetchedTickers": fetched_tickers,
                "totalTickers": len(universe_tickers),
                "latestMarketDate": manifest["latestMarketDate"],
                "rowsAdded": rows_added,
            }
        )

    return {
        "ok": True,
        "rawPath": target_snapshot,
        "manifestPath": manifest_path,
        "manifest": manifest,
    }
