#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

try:
    from .manifest_sync import sync_active_hedgemate_from_product_manifest
except ImportError:
    from manifest_sync import sync_active_hedgemate_from_product_manifest

try:
    from .final_market_state_engine import (
        FINAL_MERGE_ENGINE_VERSION,
        FINAL_MARKET_STATE_FIELDS,
        SCENARIO_CONFIDENCE_FIELDS,
        build_final_market_state_rows,
        build_scenario_vector_rows_from_final,
        build_top_active_scenarios_payload,
        render_final_market_state_markdown,
    )
    from .market_state_engine import SCENARIO_VECTOR_FIELDS
except ImportError:
    from final_market_state_engine import (
        FINAL_MERGE_ENGINE_VERSION,
        FINAL_MARKET_STATE_FIELDS,
        SCENARIO_CONFIDENCE_FIELDS,
        build_final_market_state_rows,
        build_scenario_vector_rows_from_final,
        build_top_active_scenarios_payload,
        render_final_market_state_markdown,
    )
    from market_state_engine import SCENARIO_VECTOR_FIELDS


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_FINAL_DIR = ROOT / "outputs" / "final"
OUTPUT_REPORT_DIR = ROOT / "outputs" / "reports"
OUTPUT_PROCESSED_DIR = ROOT / "outputs" / "processed"
OUTPUT_EVENTS_DIR = ROOT / "outputs" / "events"
OUTPUT_SCENARIO_VECTOR_DIR = ROOT / "outputs" / "scenario_vectors"
OUTPUT_MANIFEST_JSON = ROOT / "outputs" / "latest_manifest.json"


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def update_latest_manifest(updates: dict[str, object]) -> None:
    existing: dict[str, object] = {}
    if OUTPUT_MANIFEST_JSON.exists():
        try:
            existing = json.loads(OUTPUT_MANIFEST_JSON.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = {}
    existing.update({key: value for key, value in updates.items() if value is not None})
    existing = sync_active_hedgemate_from_product_manifest(existing)
    OUTPUT_MANIFEST_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MANIFEST_JSON.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")


def latest_matching_path(pattern: str) -> Path:
    matches = sorted(ROOT.glob(pattern))
    if not matches:
        raise FileNotFoundError(pattern)
    return matches[-1]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Run the Phase 6 final market-state merge pipeline.")
    parser.add_argument("--run-id", required=True, help="Output id for Phase 6 artifacts.")
    parser.add_argument("--scenario-run-id", default=None, help="Phase 4 scenario_state run id.")
    parser.add_argument("--overlay-run-id", default=None, help="Phase 5 event overlay run id.")
    return parser.parse_args(argv)


def resolve_state_path(run_id: str | None) -> Path:
    if run_id:
        return OUTPUT_PROCESSED_DIR / f"scenario_state_daily_{run_id}.csv"
    return latest_matching_path("outputs/processed/scenario_state_daily_*.csv")


def resolve_overlay_path(run_id: str | None) -> Path:
    if run_id:
        return OUTPUT_EVENTS_DIR / f"event_overlay_daily_{run_id}.csv"
    return latest_matching_path("outputs/events/event_overlay_daily_*.csv")


def main(argv=None) -> int:
    args = parse_args(argv)
    state_path = resolve_state_path(args.scenario_run_id)
    overlay_path = resolve_overlay_path(args.overlay_run_id)

    state_rows = load_csv(state_path)
    overlay_rows = load_csv(overlay_path)
    final_rows, confidence_rows = build_final_market_state_rows(state_rows, overlay_rows)
    payload = build_top_active_scenarios_payload(final_rows)
    scenario_vector_rows = build_scenario_vector_rows_from_final(final_rows)

    final_csv = OUTPUT_FINAL_DIR / f"final_market_state_daily_{args.run_id}.csv"
    confidence_csv = OUTPUT_FINAL_DIR / f"scenario_confidence_{args.run_id}.csv"
    top_json = OUTPUT_FINAL_DIR / f"top_active_scenarios_{args.run_id}.json"
    summary_md = OUTPUT_REPORT_DIR / f"final_market_state_summary_{args.run_id}.md"
    metadata_json = OUTPUT_REPORT_DIR / f"final_market_state_metadata_{args.run_id}.json"
    scenario_vector_csv = OUTPUT_SCENARIO_VECTOR_DIR / f"current_scenario_vector_{args.run_id}.csv"
    scenario_vector_json = OUTPUT_SCENARIO_VECTOR_DIR / f"current_scenario_vector_{args.run_id}.json"

    write_csv(final_csv, FINAL_MARKET_STATE_FIELDS, final_rows)
    write_csv(confidence_csv, SCENARIO_CONFIDENCE_FIELDS, confidence_rows)
    write_csv(scenario_vector_csv, SCENARIO_VECTOR_FIELDS, scenario_vector_rows)
    scenario_vector_json.write_text(json.dumps(scenario_vector_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    top_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_md.write_text(render_final_market_state_markdown(payload), encoding="utf-8")
    metadata_json.write_text(
        json.dumps(
            {
                "run_id": args.run_id,
                "pipeline_phase": "phase6_final_merge",
                "state_path": str(state_path),
                "overlay_path": str(overlay_path),
                "api_free": True,
                "engine_version": FINAL_MERGE_ENGINE_VERSION,
                "final_csv": str(final_csv),
                "confidence_csv": str(confidence_csv),
                "top_json": str(top_json),
                "summary_md": str(summary_md),
                "scenario_vector_csv": str(scenario_vector_csv),
                "scenario_vector_json": str(scenario_vector_json),
                "final_row_count": len(final_rows),
                "overlay_row_count": len(overlay_rows),
                "scenario_vector_row_count": len(scenario_vector_rows),
                "scenario_vector_as_of_date": scenario_vector_rows[0].get("as_of_date") if scenario_vector_rows else None,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    latest_date = max((row.get("date") for row in final_rows if row.get("date")), default=None)
    latest_rows = [row for row in final_rows if row.get("date") == latest_date] if latest_date else final_rows
    scenario_count = len({row.get("scenario_code") for row in latest_rows if row.get("scenario_code")})
    update_latest_manifest(
        {
            "active_final_run": args.run_id,
            "active_final_market_state": final_csv.name,
            "active_final_market_state_path": f"final/{final_csv.name}",
            "active_scenario_confidence": confidence_csv.name,
            "active_scenario_confidence_path": f"final/{confidence_csv.name}",
            "active_top_active_scenarios": top_json.name,
            "active_top_active_scenarios_path": f"final/{top_json.name}",
            "active_final_summary": summary_md.name,
            "active_final_summary_path": f"reports/{summary_md.name}",
            "active_final_scenario_vector": scenario_vector_csv.name,
            "active_final_scenario_vector_path": f"scenario_vectors/{scenario_vector_csv.name}",
            "active_scenario_run": args.scenario_run_id,
            "scenario_version": "v2" if scenario_count >= 10 else "v1",
            "scenario_count": scenario_count,
            "final_market_state_as_of_date": latest_date,
        }
    )

    print(f"FINAL_MARKET_STATE_CSV={final_csv}")
    print(f"SCENARIO_CONFIDENCE_CSV={confidence_csv}")
    print(f"TOP_ACTIVE_SCENARIOS_JSON={top_json}")
    print(f"FINAL_MARKET_STATE_SUMMARY={summary_md}")
    print(f"FINAL_MARKET_STATE_METADATA={metadata_json}")
    print(f"SCENARIO_VECTOR_CSV={scenario_vector_csv}")
    print(f"SCENARIO_VECTOR_JSON={scenario_vector_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
