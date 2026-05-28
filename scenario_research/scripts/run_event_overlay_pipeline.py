#!/usr/bin/env python3
"""Run the Phase 5 event overlay pipeline from fixture or live provider input."""
from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

try:
    from .event_overlay_engine import (
        ARTICLE_EVENT_FIELDS,
        DAILY_OVERLAY_FIELDS,
        EVENT_EXTRACTION_SCHEMA_VERSION,
        PROVIDER_EVENT_SCHEMA,
        build_daily_overlay_rows,
        normalize_article_events,
        render_event_review_markdown,
        render_phase5_dashboard,
        validate_article_rows,
        validate_provider_event_payload,
        write_csv,
    )
    from .event_overlay_providers import EventProviderError, build_event_provider
except ImportError:
    from event_overlay_engine import (
        ARTICLE_EVENT_FIELDS,
        DAILY_OVERLAY_FIELDS,
        EVENT_EXTRACTION_SCHEMA_VERSION,
        PROVIDER_EVENT_SCHEMA,
        build_daily_overlay_rows,
        normalize_article_events,
        render_event_review_markdown,
        render_phase5_dashboard,
        validate_article_rows,
        validate_provider_event_payload,
        write_csv,
    )
    from event_overlay_providers import EventProviderError, build_event_provider


REPO_ROOT = Path(__file__).resolve().parents[2]
SCENARIO_ROOT = REPO_ROOT / "scenario_research"
DEFAULT_INPUT = SCENARIO_ROOT / "inputs" / "event_overlay_sample_20260507.csv"
OUTPUT_EVENTS_DIR = SCENARIO_ROOT / "outputs" / "events"
OUTPUT_REPORT_DIR = SCENARIO_ROOT / "outputs" / "reports"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def default_run_id() -> str:
    ts = now_utc()
    return f"phase5-{ts.strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:6]}"


def build_overlay_metadata(
    run_id,
    input_path,
    article_rows,
    daily_rows,
    article_path,
    daily_path,
    review_path,
    dashboard_path,
    provider_name="fixture",
    provider_requires_api_key=False,
    provider_api_key_env=None,
    provider_model=None,
    live_research_attached=False,
    schema_errors=None,
    strict_schema=False,
):
    schema_errors = schema_errors or []
    fatal_schema_error_count = sum(1 for error in schema_errors if error.get("severity") == "fatal")
    return {
        "run_id": run_id,
        "input": str(input_path),
        "pipeline_phase": "phase5_structured_overlay",
        "input_mode": "reviewed_local_fixture" if provider_name == "fixture" else provider_name,
        "provider": provider_name,
        "provider_requires_api_key": provider_requires_api_key,
        "provider_api_key_env": provider_api_key_env,
        "provider_model": provider_model,
        "extraction_schema_version": EVENT_EXTRACTION_SCHEMA_VERSION,
        "provider_event_schema": PROVIDER_EVENT_SCHEMA,
        "strict_schema": strict_schema,
        "schema_error_count": len(schema_errors),
        "fatal_schema_error_count": fatal_schema_error_count,
        "schema_errors_sample": schema_errors[:10],
        "live_research_attached": bool(live_research_attached),
        "phase6_final_merge_ready": False,
        "phase6_gap": "structured_and_unstructured_not_merged",
        "article_event_count": len(article_rows),
        "daily_overlay_count": len(daily_rows),
        "needs_review_count": sum(1 for row in article_rows if row.get("needs_review") == "Y"),
        "article_path": str(article_path),
        "daily_path": str(daily_path),
        "review_path": str(review_path),
        "dashboard_path": str(dashboard_path),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Phase 5 event overlay artifacts.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="CSV/JSON fixture of reviewed news or policy events.")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--provider", default="fixture", choices=["fixture", "gemini"], help="Event extraction provider. Gemini uses GEMINI_API_KEY and structured JSON output.")
    parser.add_argument("--strict-schema", action="store_true", help="Fail on reviewable provider schema issues instead of queueing them for review.")
    parser.add_argument("--allow-empty", action="store_true", help="Write empty artifacts when the input file is missing/empty.")
    args = parser.parse_args(argv)

    run_id = args.run_id or default_run_id()
    provider = build_event_provider(args.provider, args.input)
    try:
        raw_rows = provider.load_events()
    except EventProviderError as exc:
        raise SystemExit(str(exc)) from exc

    if not raw_rows and not args.allow_empty:
        raise SystemExit(f"No event input rows found: {args.input}")

    schema_errors = validate_provider_event_payload(raw_rows, strict=args.strict_schema)
    fatal_schema_errors = [error for error in schema_errors if error.get("severity") == "fatal"]
    if fatal_schema_errors:
        raise SystemExit(f"Provider schema validation failed: {fatal_schema_errors[:3]}")

    article_rows = normalize_article_events(raw_rows)
    validate_article_rows(article_rows)
    daily_rows = build_daily_overlay_rows(article_rows)

    article_path = OUTPUT_EVENTS_DIR / f"event_overlay_article_{run_id}.csv"
    daily_path = OUTPUT_EVENTS_DIR / f"event_overlay_daily_{run_id}.csv"
    review_path = OUTPUT_REPORT_DIR / f"event_overlay_review_{run_id}.md"
    dashboard_path = OUTPUT_REPORT_DIR / f"phase5_event_overlay_dashboard_{run_id}.html"
    metadata_path = OUTPUT_REPORT_DIR / f"event_overlay_metadata_{run_id}.json"

    write_csv(article_path, ARTICLE_EVENT_FIELDS, article_rows)
    write_csv(daily_path, DAILY_OVERLAY_FIELDS, daily_rows)
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(render_event_review_markdown(article_rows, daily_rows, run_id), encoding="utf-8")
    dashboard_path.write_text(render_phase5_dashboard(article_rows, daily_rows, run_id), encoding="utf-8")
    metadata_path.write_text(
        json.dumps(
            build_overlay_metadata(
                run_id=run_id,
                input_path=args.input,
                article_rows=article_rows,
                daily_rows=daily_rows,
                article_path=article_path,
                daily_path=daily_path,
                review_path=review_path,
                dashboard_path=dashboard_path,
                provider_name=provider.name,
                provider_requires_api_key=provider.requires_api_key,
                provider_api_key_env=provider.api_key_env,
                provider_model=getattr(provider, "model_name", None),
                live_research_attached=getattr(provider, "live_research_attached", False),
                schema_errors=schema_errors,
                strict_schema=args.strict_schema,
            ),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"EVENT_OVERLAY_ARTICLE={article_path}")
    print(f"EVENT_OVERLAY_DAILY={daily_path}")
    print(f"EVENT_OVERLAY_REVIEW={review_path}")
    print(f"PHASE5_EVENT_DASHBOARD={dashboard_path}")
    print(f"EVENT_OVERLAY_METADATA={metadata_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
