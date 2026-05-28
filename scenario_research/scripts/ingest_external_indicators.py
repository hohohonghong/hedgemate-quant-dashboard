#!/usr/bin/env python3
"""Normalize official/seed external indicator exports for market-state inputs."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "inputs" / "market_state_external_indicators.csv"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Normalize BOK/FSC/KR-REB CSV exports into the scenario external indicator input schema."
    )
    parser.add_argument("--input", required=True, help="CSV export containing date, ticker/series code, and value.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Normalized output CSV path.")
    parser.add_argument("--source", default=None, help="Override source label, e.g. BOK_ECOS_OFFICIAL.")
    parser.add_argument(
        "--source-quality",
        default=None,
        choices=["official", "seed", "manual", "fixture", "unknown"],
        help="Override source quality. If omitted, it is inferred from source text.",
    )
    return parser.parse_args(argv)


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


def parse_float(value):
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def normalize_rows(input_path, source_override=None, source_quality_override=None):
    rows = []
    with Path(input_path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            date_str = raw.get("date") or raw.get("observation_date") or raw.get("TIME") or raw.get("time")
            ticker = raw.get("ticker") or raw.get("indicator_code") or raw.get("series_code") or raw.get("STAT_CODE")
            value = parse_float(raw.get("value") or raw.get("close") or raw.get("level") or raw.get("DATA_VALUE"))
            if not date_str or not ticker or value is None:
                continue
            source = source_override or raw.get("source") or raw.get("SOURCE") or "MANUAL_CSV"
            source_quality = source_quality_override or raw.get("source_quality") or infer_source_quality(source)
            rows.append(
                {
                    "date": str(date_str).strip(),
                    "ticker": str(ticker).strip(),
                    "value": value,
                    "source": str(source).strip(),
                    "source_quality": str(source_quality).strip().lower(),
                }
            )
    return sorted(rows, key=lambda row: (row["ticker"], row["date"]))


def main(argv=None):
    args = parse_args(argv)
    rows = normalize_rows(args.input, args.source, args.source_quality)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["date", "ticker", "value", "source", "source_quality"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"ROWS={len(rows)}")
    print(f"OUTPUT={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
