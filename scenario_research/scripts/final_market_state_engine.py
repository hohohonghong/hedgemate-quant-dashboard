"""Phase 6 final market-state merge engine.

This layer combines the structured Phase 4 scenario rows with the Phase 5
event overlay so the research workspace can emit a single "final" daily
diagnosis without letting text overrides dominate the structured signal.
"""
from __future__ import annotations

from collections import defaultdict

try:
    from .market_state_engine import SCENARIO_METADATA
except ImportError:
    from market_state_engine import SCENARIO_METADATA


FINAL_MERGE_ENGINE_VERSION = "phase6_final_market_state_v1"
STRUCTURED_WEIGHT = 0.85
EVENT_WEIGHT = 0.15

FINAL_MARKET_STATE_FIELDS = [
    "date",
    "scenario_code",
    "scenario_name",
    "scenario_name_ko",
    "lens",
    "related_lenses",
    "source_quality",
    "event_or_seed_dependent",
    "top_positive_drivers",
    "top_negative_drivers",
    "market_interpretation_ko",
    "structured_score",
    "structured_confidence",
    "structured_coverage",
    "structured_raw_state",
    "structured_display_state",
    "event_overlay_score",
    "event_overlay_confidence",
    "event_count",
    "overlay_applied",
    "final_score",
    "final_confidence",
    "final_state",
    "final_display_state",
    "merge_engine_version",
]

SCENARIO_CONFIDENCE_FIELDS = [
    "date",
    "scenario_code",
    "structured_confidence",
    "structured_coverage",
    "event_overlay_confidence",
    "event_count",
    "overlay_applied",
    "final_confidence",
    "merge_engine_version",
]


def parse_float(value, default=0.0):
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def clip(value, low=0.0, high=100.0):
    return max(low, min(high, value))


def is_favorable_scenario(scenario_code):
    return bool(SCENARIO_METADATA.get(scenario_code, {}).get("is_favorable"))


def score_to_final_state(score, scenario_code):
    if score >= 75:
        return "STRONG" if is_favorable_scenario(scenario_code) else "STRESS"
    if score >= 60:
        return "ACTIVE"
    if score >= 45:
        return "WATCH"
    return "OFF"


def derive_final_display_state(final_state, final_score, final_confidence, structured_coverage):
    if final_state == "OFF":
        return "OFF"
    if structured_coverage < 0.75 or final_confidence < 40.0:
        return "PROVISIONAL"
    return final_state


def build_final_market_state_rows(
    state_rows,
    overlay_rows,
    structured_weight=STRUCTURED_WEIGHT,
    event_weight=EVENT_WEIGHT,
    engine_version=FINAL_MERGE_ENGINE_VERSION,
):
    overlay_by_key = {
        (row.get("date"), row.get("scenario_code")): row
        for row in overlay_rows
    }
    final_rows = []
    confidence_rows = []

    for row in state_rows:
        date = row.get("date")
        scenario_code = row.get("scenario_code")
        overlay = overlay_by_key.get((date, scenario_code))

        structured_score = parse_float(row.get("structured_score"))
        structured_confidence = parse_float(row.get("confidence"))
        structured_coverage = parse_float(row.get("coverage_ratio"))
        overlay_score = parse_float(overlay.get("event_overlay_score")) if overlay else None
        overlay_confidence = parse_float(overlay.get("overlay_confidence")) if overlay else None
        event_count = int(parse_float(overlay.get("event_count"), 0.0)) if overlay else 0
        overlay_applied = "Y" if overlay is not None else "N"

        structured_raw_state = row.get("raw_state") or row.get("state_label", "")
        structured_display_state = row.get("display_state") or row.get("state_label", "")

        if overlay is not None:
            final_score = clip(structured_weight * structured_score + event_weight * overlay_score)
            final_confidence = clip(structured_weight * structured_confidence + event_weight * overlay_confidence)
            final_state = score_to_final_state(final_score, scenario_code)
            final_display_state = derive_final_display_state(
                final_state=final_state,
                final_score=final_score,
                final_confidence=final_confidence,
                structured_coverage=structured_coverage,
            )
        else:
            final_score = structured_score
            final_confidence = structured_confidence
            final_state = structured_raw_state or score_to_final_state(final_score, scenario_code)
            if final_state == "OFF":
                final_display_state = "OFF"
            else:
                final_display_state = structured_display_state or derive_final_display_state(
                    final_state=final_state,
                    final_score=final_score,
                    final_confidence=final_confidence,
                    structured_coverage=structured_coverage,
                )

        final_rows.append(
            {
                "date": date,
                "scenario_code": scenario_code,
                "scenario_name": row.get("scenario_name", ""),
                "scenario_name_ko": row.get("scenario_name_ko", ""),
                "lens": row.get("lens", ""),
                "related_lenses": row.get("related_lenses", ""),
                "source_quality": row.get("source_quality", ""),
                "event_or_seed_dependent": row.get("event_or_seed_dependent", ""),
                "top_positive_drivers": row.get("top_positive_drivers", ""),
                "top_negative_drivers": row.get("top_negative_drivers", ""),
                "market_interpretation_ko": row.get("market_interpretation_ko", ""),
                "structured_score": structured_score,
                "structured_confidence": structured_confidence,
                "structured_coverage": structured_coverage,
                "structured_raw_state": structured_raw_state,
                "structured_display_state": structured_display_state,
                "event_overlay_score": overlay_score if overlay is not None else "",
                "event_overlay_confidence": overlay_confidence if overlay is not None else "",
                "event_count": event_count,
                "overlay_applied": overlay_applied,
                "final_score": final_score,
                "final_confidence": final_confidence,
                "final_state": final_state,
                "final_display_state": final_display_state,
                "merge_engine_version": engine_version,
            }
        )
        confidence_rows.append(
            {
                "date": date,
                "scenario_code": scenario_code,
                "structured_confidence": structured_confidence,
                "structured_coverage": structured_coverage,
                "event_overlay_confidence": overlay_confidence if overlay is not None else "",
                "event_count": event_count,
                "overlay_applied": overlay_applied,
                "final_confidence": final_confidence,
                "merge_engine_version": engine_version,
            }
        )

    final_rows.sort(key=lambda item: (item["date"], -item["final_score"], item["scenario_code"]))
    confidence_rows.sort(key=lambda item: (item["date"], item["scenario_code"]))
    return final_rows, confidence_rows


def build_top_active_scenarios_payload(final_rows, limit=3):
    if not final_rows:
        return {"date": None, "top_active_scenarios": []}

    rows_by_date = defaultdict(list)
    for row in final_rows:
        rows_by_date[row["date"]].append(row)
    latest_date = max(rows_by_date)
    latest_rows = sorted(rows_by_date[latest_date], key=lambda item: (-item["final_score"], item["scenario_code"]))

    selected = [row for row in latest_rows if row["final_display_state"] in {"STRONG", "STRESS", "ACTIVE"}][:limit]
    selected_codes = {row["scenario_code"] for row in selected}
    for row in latest_rows:
        if len(selected) >= limit:
            break
        if row["scenario_code"] not in selected_codes:
            selected.append(row)
            selected_codes.add(row["scenario_code"])

    return {
        "date": latest_date,
        "merge_engine_version": FINAL_MERGE_ENGINE_VERSION,
        "top_active_scenarios": [
            {
                "scenario_code": row["scenario_code"],
                "scenario_name": row["scenario_name"],
                "scenario_name_ko": row["scenario_name_ko"],
                "final_score": row["final_score"],
                "final_confidence": row["final_confidence"],
                "final_display_state": row["final_display_state"],
                "lens": row["lens"],
            }
            for row in selected
        ],
    }


def build_scenario_vector_rows_from_final(final_rows, as_of_date=None, engine_version=FINAL_MERGE_ENGINE_VERSION):
    if not final_rows:
        return []
    rows_by_date = defaultdict(list)
    for row in final_rows:
        rows_by_date[row["date"]].append(row)
    scenario_count = len({row["scenario_code"] for row in final_rows})
    if as_of_date is None:
        full_dates = [
            date_str
            for date_str, rows in rows_by_date.items()
            if len({row["scenario_code"] for row in rows}) == scenario_count
        ]
        as_of_date = max(full_dates or rows_by_date.keys())
    latest_rows = sorted(
        [row for row in final_rows if row["date"] == as_of_date],
        key=lambda item: (-parse_float(item.get("final_score")), item.get("scenario_code", "")),
    )
    return [
        {
            "as_of_date": as_of_date,
            "date": row.get("date", ""),
            "scenario_code": row.get("scenario_code", ""),
            "scenario_name": row.get("scenario_name", ""),
            "scenario_name_ko": row.get("scenario_name_ko", ""),
            "lens": row.get("lens", ""),
            "related_lenses": row.get("related_lenses", ""),
            "score": row.get("final_score", ""),
            "raw_state": row.get("final_state", ""),
            "display_state": row.get("final_display_state", ""),
            "confidence": row.get("final_confidence", ""),
            "coverage": row.get("structured_coverage", ""),
            "source_quality": row.get("source_quality", ""),
            "event_or_seed_dependent": row.get("event_or_seed_dependent", ""),
            "top_positive_drivers": row.get("top_positive_drivers", ""),
            "top_negative_drivers": row.get("top_negative_drivers", ""),
            "market_interpretation_ko": row.get("market_interpretation_ko", ""),
            "engine_version": engine_version,
        }
        for row in latest_rows
    ]


def render_final_market_state_markdown(payload):
    lines = [
        "# Phase 6 Final Market State Summary",
        "",
        f"- 기준일: `{payload.get('date')}`",
        f"- merge_engine_version: `{payload.get('merge_engine_version', FINAL_MERGE_ENGINE_VERSION)}`",
        f"- top_active_count: {len(payload.get('top_active_scenarios', []))}",
        "",
        "## Top Active Scenarios",
    ]
    if not payload.get("top_active_scenarios"):
        lines.append("- 상위 활성 시나리오가 없습니다.")
    for row in payload.get("top_active_scenarios", []):
        lines.append(
            f"- `{row.get('scenario_code')}` `{row.get('final_display_state')}` "
            f"score={parse_float(row.get('final_score')):.2f}, confidence={parse_float(row.get('final_confidence')):.2f}, "
            f"lens={row.get('lens')}"
        )
    return "\n".join(lines).rstrip() + "\n"
