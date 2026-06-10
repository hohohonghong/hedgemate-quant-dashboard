#!/usr/bin/env python3
"""Validate Phase 4 scenario/factor output invariants.

This is intentionally dependency-free so it can be run after every local smoke
pipeline without installing the presentation/dashboard stack.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from market_state_engine import ENGINE_VERSION, SCENARIO_VECTOR_FIELDS, build_scenario_registry_rows

EXPECTED_SCENARIO_CODES = {row["scenario_code"] for row in build_scenario_registry_rows()}
EXPECTED_SCENARIO_COUNT = len(EXPECTED_SCENARIO_CODES)
EXPECTED_FACTOR_COUNT = 8


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise AssertionError(f"missing file: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_csv_with_fields(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        raise AssertionError(f"missing file: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def as_float(row: dict[str, str], key: str) -> float:
    try:
        return float(row.get(key, ""))
    except (TypeError, ValueError) as exc:
        raise AssertionError(f"non-numeric {key}: {row.get(key)!r}") from exc


def require_range(rows: list[dict[str, str]], keys: list[str], low: float, high: float) -> None:
    for row in rows:
        for key in keys:
            value = as_float(row, key)
            if not low <= value <= high:
                raise AssertionError(f"{key} out of range [{low}, {high}]: {value} in {row}")


def validate(run_id: str) -> list[str]:
    processed = ROOT / "outputs" / "processed"
    reports = ROOT / "outputs" / "reports"
    scenario_vectors = ROOT / "outputs" / "scenario_vectors"
    state_path = processed / f"scenario_state_daily_{run_id}.csv"
    feature_path = processed / f"scenario_feature_daily_{run_id}.csv"
    factor_path = processed / f"market_factor_daily_{run_id}.csv"
    driver_path = reports / f"scenario_driver_table_{run_id}.csv"
    metadata_path = reports / f"scenario_snapshot_metadata_{run_id}.json"
    vector_path = scenario_vectors / f"current_scenario_vector_{run_id}.csv"
    summary_path = reports / f"daily_market_state_summary_{run_id}.md"

    state_rows = load_csv(state_path)
    feature_rows = load_csv(feature_path)
    factor_rows = load_csv(factor_path)
    driver_rows = load_csv(driver_path)
    vector_fields, vector_rows = load_csv_with_fields(vector_path)
    if not metadata_path.exists():
        raise AssertionError(f"missing file: {metadata_path}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not summary_path.exists():
        raise AssertionError(f"missing file: {summary_path}")
    summary_text = summary_path.read_text(encoding="utf-8")

    if not state_rows:
        raise AssertionError("scenario_state has no rows")
    if not feature_rows:
        raise AssertionError("scenario_feature has no rows")
    if not factor_rows:
        raise AssertionError("market_factor has no rows")
    if not driver_rows:
        raise AssertionError("scenario_driver has no rows")
    if not vector_rows:
        raise AssertionError("current_scenario_vector has no rows")

    require_range(state_rows, ["structured_score", "confidence"], 0.0, 100.0)
    require_range(state_rows, ["coverage_ratio", "breadth_score"], 0.0, 1.0)
    require_range(factor_rows, ["factor_score", "confidence"], 0.0, 100.0)
    require_range(factor_rows, ["coverage_ratio", "breadth_score"], 0.0, 1.0)

    latest_date = max(row["date"] for row in state_rows)
    latest_state_rows = [row for row in state_rows if row["date"] == latest_date]
    scenario_count = len({row["scenario_code"] for row in latest_state_rows})
    if scenario_count != EXPECTED_SCENARIO_COUNT:
        raise AssertionError(f"latest scenario count is {scenario_count}, expected {EXPECTED_SCENARIO_COUNT}")
    latest_state_codes = {row["scenario_code"] for row in latest_state_rows}
    if latest_state_codes != EXPECTED_SCENARIO_CODES:
        missing = sorted(EXPECTED_SCENARIO_CODES - latest_state_codes)
        extra = sorted(latest_state_codes - EXPECTED_SCENARIO_CODES)
        raise AssertionError(f"latest scenario codes mismatch; missing={missing}, extra={extra}")

    latest_factor_rows = [row for row in factor_rows if row["date"] == latest_date]
    factor_count = len({row["factor_code"] for row in latest_factor_rows})
    if factor_count != EXPECTED_FACTOR_COUNT:
        raise AssertionError(f"latest factor count is {factor_count}, expected {EXPECTED_FACTOR_COUNT}")

    latest_feature_rows = [row for row in feature_rows if row["date"] == latest_date]
    if not any(row.get("ticker", "").startswith("__BREADTH_") for row in latest_feature_rows):
        raise AssertionError("latest features do not include synthetic 70-asset breadth signals")

    driver_effects = {row.get("driver_effect") for row in driver_rows if row["date"] == latest_date}
    if not driver_effects <= {"supporting", "offsetting"}:
        raise AssertionError(f"unexpected driver_effect values: {sorted(driver_effects)}")

    if vector_fields != SCENARIO_VECTOR_FIELDS:
        raise AssertionError(
            f"scenario vector fields mismatch: actual={vector_fields}, expected={SCENARIO_VECTOR_FIELDS}"
        )
    require_range(vector_rows, ["score", "confidence"], 0.0, 100.0)
    require_range(vector_rows, ["coverage"], 0.0, 1.0)

    latest_vector_as_of_date = max(row["as_of_date"] for row in vector_rows)
    if latest_vector_as_of_date != latest_date:
        raise AssertionError(
            f"scenario vector latest as_of_date {latest_vector_as_of_date} does not match latest full state date {latest_date}"
        )
    latest_vector_rows = [row for row in vector_rows if row["as_of_date"] == latest_vector_as_of_date]
    latest_vector_codes = {row["scenario_code"] for row in latest_vector_rows}
    if latest_vector_codes != EXPECTED_SCENARIO_CODES:
        missing = sorted(EXPECTED_SCENARIO_CODES - latest_vector_codes)
        extra = sorted(latest_vector_codes - EXPECTED_SCENARIO_CODES)
        raise AssertionError(f"scenario vector codes mismatch; missing={missing}, extra={extra}")
    if len(latest_vector_codes) != EXPECTED_SCENARIO_COUNT:
        raise AssertionError("scenario vector does not include all expected scenarios on latest date")
    required_vector_fields = {
        "lens",
        "raw_state",
        "display_state",
        "confidence",
        "coverage",
        "market_interpretation_ko",
        "top_positive_drivers",
        "engine_version",
    }
    missing_vector_fields = required_vector_fields - set(vector_rows[0])
    if missing_vector_fields:
        raise AssertionError(f"scenario vector missing required fields: {sorted(missing_vector_fields)}")
    if not all(row.get("lens") for row in latest_vector_rows):
        raise AssertionError("scenario vector lens must be populated")
    off_promotions = [
        row["scenario_code"]
        for row in latest_vector_rows
        if row.get("raw_state") == "OFF" and row.get("display_state") != "OFF"
    ]
    if off_promotions:
        raise AssertionError(f"raw OFF scenarios promoted in display_state: {off_promotions}")
    wrong_engine_versions = {
        row.get("engine_version")
        for row in latest_vector_rows
        if row.get("engine_version") != ENGINE_VERSION
    }
    if wrong_engine_versions:
        raise AssertionError(f"unexpected scenario vector engine versions: {sorted(wrong_engine_versions)}")
    if "diagnostic-only market-state evidence" not in summary_text:
        raise AssertionError("daily summary must state that the scenario vector is diagnostic-only")

    required_metadata = {
        "run_id",
        "pipeline_phase",
        "api_free",
        "diagnostic_only",
        "engine_version",
        "expected_scenario_count",
        "scenario_count",
        "scenario_vector_row_count",
        "scenario_vector_latest_row_count",
        "scenario_vector_as_of_date",
        "scenario_codes",
    }
    missing_metadata = required_metadata - set(metadata)
    if missing_metadata:
        raise AssertionError(f"scenario metadata missing required fields: {sorted(missing_metadata)}")
    if metadata.get("run_id") != run_id:
        raise AssertionError(f"metadata run_id mismatch: {metadata.get('run_id')!r}")
    if metadata.get("pipeline_phase") != "phase4_structured_scenario_vector":
        raise AssertionError(f"unexpected pipeline_phase: {metadata.get('pipeline_phase')!r}")
    if metadata.get("api_free") is not True:
        raise AssertionError("metadata api_free must be true")
    if metadata.get("diagnostic_only") is not True:
        raise AssertionError("metadata diagnostic_only must be true")
    if metadata.get("engine_version") != ENGINE_VERSION:
        raise AssertionError(f"metadata engine_version mismatch: {metadata.get('engine_version')!r}")
    if metadata.get("expected_scenario_count") != EXPECTED_SCENARIO_COUNT:
        raise AssertionError("metadata expected_scenario_count mismatch")
    if metadata.get("scenario_count") != EXPECTED_SCENARIO_COUNT:
        raise AssertionError("metadata scenario_count mismatch")
    if metadata.get("scenario_vector_latest_row_count") != EXPECTED_SCENARIO_COUNT:
        raise AssertionError("metadata scenario_vector_latest_row_count mismatch")
    if metadata.get("scenario_vector_as_of_date") != latest_vector_as_of_date:
        raise AssertionError("metadata scenario_vector_as_of_date mismatch")

    if metadata.get("loaded_ticker_count", 0) < 20:
        raise AssertionError("loaded_ticker_count should reflect expanded proxy set")
    expected_ticker_count = metadata.get("expected_ticker_count", 0)
    loaded_ticker_count = metadata.get("loaded_ticker_count", 0)
    if expected_ticker_count and loaded_ticker_count != expected_ticker_count:
        raise AssertionError(
            f"loaded_ticker_count is {loaded_ticker_count}, expected full coverage of {expected_ticker_count}"
        )
    missing_total = metadata.get("missing_tickers_total", [])
    if missing_total:
        raise AssertionError(f"expected proxy tickers missing from load: {missing_total}")
    missing_on_anchor = metadata.get("tickers_missing_on_anchor_date", [])
    if missing_on_anchor:
        raise AssertionError(f"anchor date still missing tickers after alignment: {missing_on_anchor}")
    quality_status = metadata.get("data_quality_status")
    if quality_status not in (None, "", "OK"):
        raise AssertionError(f"data_quality_status is not OK: {quality_status}")
    if metadata.get("universe_breadth_source_ticker_count", 0) < 50:
        raise AssertionError("70-asset breadth source universe is unexpectedly small")
    breadth_series = metadata.get("synthetic_breadth_series", [])
    if not isinstance(breadth_series, list) or len(breadth_series) < 5:
        raise AssertionError("synthetic breadth metadata is missing or incomplete")

    return [
        f"latest_date={latest_date}",
        f"scenario_count={scenario_count}",
        f"factor_count={factor_count}",
        f"scenario_vector_rows={len(latest_vector_rows)}",
        f"scenario_vector_as_of_date={latest_vector_as_of_date}",
        f"engine_version={ENGINE_VERSION}",
        f"expanded_proxy_tickers={metadata.get('loaded_ticker_count')}/{metadata.get('expected_ticker_count')}",
        f"quality_status={metadata.get('data_quality_status', 'UNKNOWN')}",
        f"anchor_forward_fill_count={len(metadata.get('anchor_forward_fills', []))}",
        f"breadth_source_tickers={metadata.get('universe_breadth_source_ticker_count')}",
    ]


def write_validation_report(run_id: str, details: list[str]) -> tuple[Path, Path]:
    reports = ROOT / "outputs" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    detail_map = dict(detail.split("=", 1) for detail in details if "=" in detail)
    payload = {
        "run_id": run_id,
        "pipeline_phase": "phase4_structured_scenario_vector_validation",
        "status": "PASS",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expected_scenario_count": EXPECTED_SCENARIO_COUNT,
        "expected_scenario_codes": sorted(EXPECTED_SCENARIO_CODES),
        "engine_version": ENGINE_VERSION,
        "details": detail_map,
    }
    json_path = reports / f"phase4_validation_{run_id}.json"
    md_path = reports / f"phase4_validation_{run_id}.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(
        "\n".join(
            [
                "# Phase 4.5 Scenario Vector Validation",
                "",
                f"- run_id: `{run_id}`",
                "- status: `PASS`",
                f"- expected_scenario_count: {EXPECTED_SCENARIO_COUNT}",
                f"- engine_version: `{ENGINE_VERSION}`",
                "- diagnostic_only: true",
                "",
                "## Details",
                *[f"- {detail}" for detail in details],
                "",
            ]
        ),
        encoding="utf-8",
    )
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Phase 4 output invariants.")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args(argv)
    try:
        details = validate(args.run_id)
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print("OK")
    for detail in details:
        print(detail)
    json_path, md_path = write_validation_report(args.run_id, details)
    print(f"PHASE4_VALIDATION_JSON={json_path}")
    print(f"PHASE4_VALIDATION_REPORT={md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
