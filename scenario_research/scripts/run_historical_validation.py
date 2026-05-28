#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PROCESSED_DIR = ROOT / "outputs" / "processed"
OUTPUT_REPORT_DIR = ROOT / "outputs" / "reports"
OUTPUT_VALIDATION_DIR = ROOT / "outputs" / "validation"

HISTORICAL_CASES = [
    {
        "case_code": "gfc_global_financial_crisis",
        "case_name": "GFC (글로벌 금융위기)",
        "start_date": "2007-10-01",
        "end_date": "2009-03-31",
        "scenario_code": "acute_global_stress_liquidity_crunch",
    },
    {
        "case_code": "covid_pandemic_shock",
        "case_name": "COVID / Pandemic Shock",
        "start_date": "2020-02-19",
        "end_date": "2020-04-15",
        "scenario_code": "acute_global_stress_liquidity_crunch",
    },
    {
        "case_code": "global_rate_shock_2022",
        "case_name": "2022 Global Rate Shock",
        "start_date": "2021-11-01",
        "end_date": "2022-10-31",
        "scenario_code": "higher_for_longer_long_rate_shock",
    },
    {
        "case_code": "war_energy_shock_2022",
        "case_name": "Russia-Ukraine / War-Energy Shock",
        "start_date": "2022-02-01",
        "end_date": "2022-10-31",
        "scenario_code": "stagflation_reinflation_energy_shock",
    },
    {
        "case_code": "china_slowdown_property_stress",
        "case_name": "China Slowdown / Property Stress",
        "start_date": "2023-01-01",
        "end_date": "2024-12-31",
        "scenario_code": "china_trade_fragmentation_shock",
    },
    {
        "case_code": "krw_weakness_2022",
        "case_name": "2022 KRW Weakness / USD Strength",
        "start_date": "2022-06-01",
        "end_date": "2022-10-31",
        "scenario_code": "usd_strength_krw_weakness",
    },
    {
        "case_code": "svb_credit_stress_2023",
        "case_name": "2023 US Regional Bank / Credit Stress",
        "start_date": "2023-03-01",
        "end_date": "2023-05-31",
        "scenario_code": "acute_global_stress_liquidity_crunch",
    },
    {
        "case_code": "ai_semiconductor_concentration_2024",
        "case_name": "2024 AI Semiconductor Concentration / Pullback Risk",
        "start_date": "2024-03-01",
        "end_date": "2024-08-31",
        "scenario_code": "semiconductor_ai_cycle_shock",
    },
    {
        "case_code": "middle_east_shipping_supply_shock_2024",
        "case_name": "2024 Middle East / Shipping Supply Shock",
        "start_date": "2024-01-01",
        "end_date": "2024-05-31",
        "scenario_code": "geopolitical_escalation_supply_shock",
    },
]

VALIDATION_FIELDS = [
    "case_id",
    "expected_scenario_code",
    "watch_date",
    "active_date",
    "stress_date",
    "data_sufficiency",
    "detection_status",
    "detection_lag_days",
    "coverage_ratio",
    "notes",
    "case_code",
    "case_name",
    "start_date",
    "end_date",
    "scenario_code",
    "validation_status",
    "observation_count",
    "avg_score",
    "peak_score",
    "peak_date",
    "peak_display_state",
    "first_watch_date",
    "first_active_date",
    "first_stress_date",
    "days_to_watch",
    "days_to_active",
    "days_to_stress",
    "top_non_target_scenario",
    "top_non_target_avg_score",
]


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


def parse_float(value, default=0.0):
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def latest_matching_path(pattern: str) -> Path:
    matches = sorted(ROOT.glob(pattern))
    if not matches:
        raise FileNotFoundError(pattern)
    return matches[-1]


def resolve_state_path(run_id: str | None) -> Path:
    if run_id:
        return OUTPUT_PROCESSED_DIR / f"scenario_state_daily_{run_id}.csv"
    return latest_matching_path("outputs/processed/scenario_state_daily_*.csv")


def first_date_for_state(rows: list[dict[str, str]], target_states: set[str]) -> str:
    for row in rows:
        state = row.get("display_state") or row.get("raw_state") or row.get("state_label", "")
        if state in target_states:
            return row.get("date", "")
    return ""


def days_between(start_date: str, end_date: str) -> str:
    if not start_date or not end_date:
        return ""
    return str((parse_date(end_date) - parse_date(start_date)).days)


def case_value(case: dict[str, str], *keys: str, default: str = "") -> str:
    for key in keys:
        value = case.get(key)
        if value not in (None, ""):
            return str(value)
    return default


def inclusive_day_count(start_date: str, end_date: str) -> int:
    try:
        return max(1, (parse_date(end_date) - parse_date(start_date)).days + 1)
    except (TypeError, ValueError):
        return 1


def classify_detection_status(first_watch: str, first_active: str, first_stress: str, marker_active: str, marker_stress: str) -> str:
    if first_active or first_stress:
        if marker_stress and first_stress and first_stress > marker_stress:
            return "LATE"
        if marker_active and first_active and first_active > marker_active:
            return "LATE"
        return "DETECTED"
    if first_watch:
        return "LATE"
    return "MISSED"


def build_validation_rows(state_rows: list[dict[str, str]], cases=None) -> list[dict[str, object]]:
    cases = cases or HISTORICAL_CASES
    rows_by_scenario = defaultdict(list)
    for row in state_rows:
        rows_by_scenario[row.get("scenario_code")].append(row)
    for rows in rows_by_scenario.values():
        rows.sort(key=lambda item: item.get("date", ""))

    results = []
    for case in cases:
        case_code = case_value(case, "case_code", "case_id")
        scenario_code = case_value(case, "scenario_code", "expected_scenario_code")
        start_date = case_value(case, "start_date")
        end_date = case_value(case, "end_date")
        marker_watch = case_value(case, "watch_date")
        marker_active = case_value(case, "active_date")
        marker_stress = case_value(case, "stress_date")
        target_rows = [
            row
            for row in rows_by_scenario.get(scenario_code, [])
            if start_date <= row.get("date", "") <= end_date
        ]
        if not target_rows:
            results.append(
                {
                    **case,
                    "case_id": case_code,
                    "expected_scenario_code": scenario_code,
                    "watch_date": marker_watch,
                    "active_date": marker_active,
                    "stress_date": marker_stress,
                    "data_sufficiency": "INSUFFICIENT_HISTORY",
                    "detection_status": "INSUFFICIENT_HISTORY",
                    "detection_lag_days": "",
                    "coverage_ratio": 0.0,
                    "notes": case.get("notes", "No scenario history rows in the evaluation window."),
                    "case_code": case_code,
                    "scenario_code": scenario_code,
                    "start_date": start_date,
                    "end_date": end_date,
                    "validation_status": "INSUFFICIENT_HISTORY",
                    "observation_count": 0,
                    "avg_score": "",
                    "peak_score": "",
                    "peak_date": "",
                    "peak_display_state": "",
                    "first_watch_date": "",
                    "first_active_date": "",
                    "first_stress_date": "",
                    "days_to_watch": "",
                    "days_to_active": "",
                    "days_to_stress": "",
                    "top_non_target_scenario": "",
                    "top_non_target_avg_score": "",
                }
            )
            continue

        peak_row = max(target_rows, key=lambda row: parse_float(row.get("structured_score")))
        avg_score = sum(parse_float(row.get("structured_score")) for row in target_rows) / len(target_rows)
        first_watch = first_date_for_state(target_rows, {"WATCH", "ACTIVE", "STRESS", "STRONG", "PROVISIONAL"})
        first_active = first_date_for_state(target_rows, {"ACTIVE", "STRESS", "STRONG"})
        first_stress = first_date_for_state(target_rows, {"STRESS", "STRONG"})
        coverage_ratio = min(1.0, len(target_rows) / inclusive_day_count(start_date, end_date))
        data_sufficiency = case.get("data_sufficiency") or ("PARTIAL" if coverage_ratio < 0.25 else "SUFFICIENT")
        detection_status = classify_detection_status(first_watch, first_active, first_stress, marker_active, marker_stress)
        lag_anchor = marker_active or marker_watch or start_date
        detected_anchor = first_active or first_watch or ""

        non_target_averages = []
        for scenario_code, rows in rows_by_scenario.items():
            if scenario_code == case_value(case, "scenario_code", "expected_scenario_code"):
                continue
            case_rows = [row for row in rows if start_date <= row.get("date", "") <= end_date]
            if not case_rows:
                continue
            non_target_averages.append(
                (
                    scenario_code,
                    sum(parse_float(row.get("structured_score")) for row in case_rows) / len(case_rows),
                )
            )
        top_non_target_scenario, top_non_target_avg_score = ("", "")
        if non_target_averages:
            top_non_target_scenario, top_non_target_avg_score = max(non_target_averages, key=lambda item: item[1])

        results.append(
            {
                **case,
                "case_id": case_code,
                "expected_scenario_code": case_value(case, "scenario_code", "expected_scenario_code"),
                "watch_date": first_watch,
                "active_date": first_active,
                "stress_date": first_stress,
                "data_sufficiency": data_sufficiency,
                "detection_status": detection_status,
                "detection_lag_days": days_between(lag_anchor, detected_anchor) if detected_anchor else "",
                "coverage_ratio": round(coverage_ratio, 6),
                "notes": case.get("notes", ""),
                "case_code": case_code,
                "scenario_code": case_value(case, "scenario_code", "expected_scenario_code"),
                "start_date": start_date,
                "end_date": end_date,
                "validation_status": "OK",
                "observation_count": len(target_rows),
                "avg_score": round(avg_score, 6),
                "peak_score": round(parse_float(peak_row.get("structured_score")), 6),
                "peak_date": peak_row.get("date", ""),
                "peak_display_state": peak_row.get("display_state") or peak_row.get("raw_state") or peak_row.get("state_label", ""),
                "first_watch_date": first_watch,
                "first_active_date": first_active,
                "first_stress_date": first_stress,
                "days_to_watch": days_between(start_date, first_watch),
                "days_to_active": days_between(start_date, first_active),
                "days_to_stress": days_between(start_date, first_stress),
                "top_non_target_scenario": top_non_target_scenario,
                "top_non_target_avg_score": round(top_non_target_avg_score, 6) if top_non_target_avg_score != "" else "",
            }
        )
    return results


def render_validation_markdown(rows: list[dict[str, object]], state_run_id: str) -> str:
    status_counts = defaultdict(int)
    for row in rows:
        status_counts[row.get("detection_status") or row.get("validation_status")] += 1
    lines = [
        "# Historical Validation Review",
        "",
        f"- scenario_run_id: `{state_run_id}`",
        f"- case_count: {len(rows)}",
        f"- detected: {status_counts['DETECTED']}",
        f"- late: {status_counts['LATE']}",
        f"- missed: {status_counts['MISSED']}",
        f"- insufficient_history: {status_counts['INSUFFICIENT_HISTORY']}",
        "",
        "## Case Summary",
    ]
    for row in rows:
        if row["validation_status"] != "OK":
            lines.append(
                f"- `{row['case_code']}` `{row['validation_status']}` — "
                f"{row['case_name']} ({row['start_date']} ~ {row['end_date']})"
            )
            continue
        lines.append(
            f"- `{row['case_code']}` peak={row['peak_score']} on `{row['peak_date']}` "
            f"state=`{row['peak_display_state']}` avg={row['avg_score']} "
            f"watch={row['first_watch_date'] or '-'} active={row['first_active_date'] or '-'} stress={row['first_stress_date'] or '-'}"
        )
    return "\n".join(lines).rstrip() + "\n"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Generate historical validation summaries from Phase 4 outputs.")
    parser.add_argument("--run-id", required=True, help="Output id for historical validation artifacts.")
    parser.add_argument("--scenario-run-id", default=None, help="Phase 4 scenario_state run id.")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    state_path = resolve_state_path(args.scenario_run_id)
    state_rows = load_csv(state_path)
    validation_rows = build_validation_rows(state_rows)

    csv_path = OUTPUT_VALIDATION_DIR / f"historical_validation_cases_{args.run_id}.csv"
    md_path = OUTPUT_REPORT_DIR / f"historical_validation_review_{args.run_id}.md"
    metadata_path = OUTPUT_REPORT_DIR / f"historical_validation_metadata_{args.run_id}.json"

    write_csv(csv_path, VALIDATION_FIELDS, validation_rows)
    md_path.write_text(render_validation_markdown(validation_rows, state_path.stem.removeprefix("scenario_state_daily_")), encoding="utf-8")
    metadata_path.write_text(
        json.dumps(
            {
                "run_id": args.run_id,
                "scenario_state_path": str(state_path),
                "validation_csv": str(csv_path),
                "validation_review": str(md_path),
                "case_count": len(validation_rows),
                "ok_case_count": sum(1 for row in validation_rows if row["validation_status"] == "OK"),
                "insufficient_history_case_count": sum(
                    1 for row in validation_rows if row["validation_status"] == "INSUFFICIENT_HISTORY"
                ),
                "detected_case_count": sum(1 for row in validation_rows if row.get("detection_status") == "DETECTED"),
                "late_case_count": sum(1 for row in validation_rows if row.get("detection_status") == "LATE"),
                "missed_case_count": sum(1 for row in validation_rows if row.get("detection_status") == "MISSED"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"HISTORICAL_VALIDATION_CSV={csv_path}")
    print(f"HISTORICAL_VALIDATION_REVIEW={md_path}")
    print(f"HISTORICAL_VALIDATION_METADATA={metadata_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
