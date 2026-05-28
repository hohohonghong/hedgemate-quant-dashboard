"""Phase 5 event overlay engine for structured news/policy signals.

The Phase 4 market-state engine remains the primary structured-data layer.
This module turns a small, reviewed set of news/policy items into a separate
event overlay so downstream steps can compare "structured only" vs "event
assisted" signals without letting text snippets directly decide the market.
"""
from __future__ import annotations

import csv
import html
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path


EVENT_OVERLAY_ENGINE_VERSION = "phase5_event_overlay_v1"
EVENT_EXTRACTION_SCHEMA_VERSION = "phase5_event_extraction_schema_v1"

EVENT_TYPES = {
    "rate",
    "inflation",
    "fx",
    "geopolitics",
    "earnings",
    "policy",
    "growth",
    "credit",
    "risk_sentiment",
    "trade",
    "commodity",
    "semiconductor",
}
REGIONS = {"us", "korea", "china", "global", "asia", "europe"}
DIRECTIONS = {
    "risk_on",
    "risk_off",
    "inflation_up",
    "inflation_down",
    "rate_up",
    "rate_down",
    "fx_pressure",
    "fx_relief",
    "growth_up",
    "growth_down",
    "policy_support",
    "policy_tightening",
    "semiconductor_up",
    "semiconductor_down",
    "trade_pressure",
}
TIME_HORIZONS = {"intraday", "days", "weeks", "months"}
SCENARIO_CODES = {
    "soft_landing_goldilocks",
    "slowdown_recession_deflation_risk",
    "higher_for_longer_long_rate_shock",
    "stagflation_reinflation_energy_shock",
    "usd_strength_krw_weakness",
    "acute_global_stress_liquidity_crunch",
    "china_trade_fragmentation_shock",
    "semiconductor_ai_cycle_shock",
    "korea_domestic_financial_stress",
    "geopolitical_escalation_supply_shock",
}

ARTICLE_EVENT_FIELDS = [
    "date",
    "source",
    "title",
    "url_or_ref",
    "event_type",
    "region",
    "affected_assets",
    "direction",
    "severity",
    "novelty",
    "time_horizon",
    "scenario_links",
    "evidence_span",
    "extract_confidence",
    "needs_review",
    "review_reason",
    "dedupe_key",
    "engine_version",
]

DAILY_OVERLAY_FIELDS = [
    "date",
    "scenario_code",
    "event_overlay_score",
    "event_count",
    "needs_review_count",
    "avg_severity",
    "avg_novelty",
    "overlay_confidence",
    "event_types",
    "regions",
    "direction_summary",
    "top_event_titles",
    "evidence_summary",
    "source_count",
    "engine_version",
]

EVENT_TYPE_KEYWORDS = [
    ("rate", ["rate", "yield", "treasury", "fomc", "fed", "금리", "연준", "국채"]),
    ("inflation", ["inflation", "cpi", "ppi", "prices", "물가", "인플레이션"]),
    ("fx", ["fx", "dollar", "usd", "krw", "won", "환율", "원화", "달러"]),
    ("geopolitics", ["war", "conflict", "geopolitical", "전쟁", "분쟁", "지정학"]),
    ("earnings", ["earnings", "guidance", "profit", "실적", "가이던스"]),
    ("policy", ["policy", "tariff", "subsidy", "regulation", "정책", "관세", "규제"]),
    ("growth", ["growth", "recession", "employment", "gdp", "성장", "침체", "고용"]),
    ("credit", ["credit", "spread", "default", "신용", "스프레드"]),
    ("trade", ["trade", "export", "import", "supply chain", "무역", "수출", "공급망"]),
    ("commodity", ["oil", "energy", "commodity", "crude", "유가", "에너지", "원자재"]),
    ("semiconductor", ["semiconductor", "chip", "memory", "ai", "반도체", "메모리"]),
]

DIRECTION_KEYWORDS = [
    ("risk_off", ["risk-off", "selloff", "volatility", "stress", "불안", "매도", "변동성"]),
    ("risk_on", ["risk-on", "rally", "soft landing", "낙관", "랠리", "위험선호"]),
    ("inflation_up", ["inflation rises", "hot cpi", "price pressure", "물가 상승", "인플레이션 압력"]),
    ("inflation_down", ["disinflation", "cooling inflation", "물가 둔화"]),
    ("rate_up", ["yield rises", "rate hike", "higher for longer", "금리 상승", "긴축"]),
    ("rate_down", ["yield falls", "rate cut", "금리 하락", "인하"]),
    ("fx_pressure", ["dollar strength", "won weakness", "usd/krw rises", "원화 약세", "달러 강세"]),
    ("fx_relief", ["dollar weakness", "won strength", "원화 강세", "달러 약세"]),
    ("growth_down", ["recession", "slowdown", "weak demand", "침체", "둔화"]),
    ("growth_up", ["growth improves", "strong demand", "성장 개선", "수요 개선"]),
    ("policy_support", ["stimulus", "support", "부양", "지원"]),
    ("policy_tightening", ["tightening", "restriction", "규제", "긴축"]),
    ("semiconductor_up", ["chip rally", "memory recovery", "반도체 강세", "메모리 회복"]),
    ("semiconductor_down", ["chip weakness", "memory slump", "반도체 약세", "메모리 부진"]),
    ("trade_pressure", ["tariff", "export control", "trade tension", "관세", "수출 통제", "무역 갈등"]),
]

SCENARIO_KEYWORDS = [
    ("semiconductor_ai_cycle_shock", ["semiconductor", "chip", "memory", "ai", "nvda", "soxx", "korea semiconductor"]),
    ("korea_domestic_financial_stress", ["korea credit", "household debt", "pf", "construction", "bank", "kospi", "korean financial"]),
    ("geopolitical_escalation_supply_shock", ["geopolitical", "war", "shipping", "strait", "middle east", "defense", "oil supply"]),
    ("higher_for_longer_long_rate_shock", ["rate", "yield", "treasury", "fomc", "fed", "금리", "국채", "연준"]),
    ("stagflation_reinflation_energy_shock", ["inflation", "oil", "energy", "commodity", "물가", "유가", "원자재"]),
    ("usd_strength_krw_weakness", ["fx", "dollar", "usd", "krw", "won", "환율", "원화", "달러"]),
    ("china_trade_fragmentation_shock", ["china", "trade", "tariff", "export control", "중국", "관세", "무역", "수출 통제"]),
    ("acute_global_stress_liquidity_crunch", ["risk-off", "volatility", "war", "stress", "selloff", "지정학", "변동성", "리스크"]),
    ("slowdown_recession_deflation_risk", ["recession", "slowdown", "weak demand", "growth down", "침체", "둔화", "수요 약화"]),
    ("soft_landing_goldilocks", ["soft landing", "risk-on", "growth improves", "disinflation", "위험선호", "물가 둔화"]),
]

PROVIDER_EVENT_SCHEMA = {
    "schema_version": EVENT_EXTRACTION_SCHEMA_VERSION,
    "required_for_aggregation": ["date", "title", "evidence_span", "scenario_links"],
    "reviewable_if_missing": ["evidence_span", "scenario_links"],
    "numeric_0_to_100": ["severity", "novelty", "extract_confidence"],
    "enums": {
        "event_type": sorted(EVENT_TYPES),
        "region": sorted(REGIONS),
        "direction": sorted(DIRECTIONS),
        "time_horizon": sorted(TIME_HORIZONS),
        "scenario_links": sorted(SCENARIO_CODES),
    },
}


def parse_float(value: object, default: float | None = None) -> float | None:
    if value in (None, ""):
        return default
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(parsed) or math.isinf(parsed):
        return default
    return parsed


def clip(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def split_multi(value: object) -> list[str]:
    if value in (None, ""):
        return []
    parts = re.split(r"[|,;]", str(value))
    return [part.strip() for part in parts if part and part.strip()]


def join_multi(values: list[str] | set[str]) -> str:
    return "|".join(sorted({value for value in values if value}))


def normalized_text(*values: object) -> str:
    return " ".join(str(value or "").lower() for value in values)


def first_keyword_match(text: str, choices: list[tuple[str, list[str]]], default: str) -> str:
    for label, keywords in choices:
        if any(keyword.lower() in text for keyword in keywords):
            return label
    return default


def infer_event_type(row: dict[str, str]) -> str:
    explicit = (row.get("event_type") or "").strip().lower()
    if explicit in EVENT_TYPES:
        return explicit
    return first_keyword_match(normalized_text(row.get("title"), row.get("body"), row.get("text")), EVENT_TYPE_KEYWORDS, "risk_sentiment")


def infer_direction(row: dict[str, str]) -> str:
    explicit = (row.get("direction") or "").strip().lower()
    if explicit in DIRECTIONS:
        return explicit
    return first_keyword_match(normalized_text(row.get("title"), row.get("body"), row.get("text")), DIRECTION_KEYWORDS, "risk_off")


def infer_region(row: dict[str, str]) -> str:
    explicit = (row.get("region") or "").strip().lower()
    if explicit in REGIONS:
        return explicit
    text = normalized_text(row.get("title"), row.get("body"), row.get("text"))
    if any(token in text for token in ["korea", "krw", "kospi", "한국", "원화"]):
        return "korea"
    if any(token in text for token in ["china", "중국"]):
        return "china"
    if any(token in text for token in ["fed", "treasury", "s&p", "nasdaq", "미국", "연준"]):
        return "us"
    return "global"


def infer_scenario_links(row: dict[str, str]) -> list[str]:
    explicit = [code for code in split_multi(row.get("scenario_links")) if code in SCENARIO_CODES]
    if explicit:
        return explicit
    text = normalized_text(row.get("event_type"), row.get("direction"), row.get("title"), row.get("body"), row.get("text"))
    linked = []
    for scenario_code, keywords in SCENARIO_KEYWORDS:
        if any(keyword.lower() in text for keyword in keywords):
            linked.append(scenario_code)
    return linked or ["acute_global_stress_liquidity_crunch"]


def validate_provider_event_payload(raw_rows: list[dict[str, object]], strict: bool = False) -> list[dict[str, object]]:
    """Validate provider output before normalization.

    This intentionally allows reviewable issues in non-strict mode so a local
    fixture or future LLM provider can produce a review queue instead of
    breaking the whole Phase 5 run. Strict mode is useful once a live provider
    is attached and schema drift should fail fast.
    """
    errors: list[dict[str, object]] = []
    enum_fields = {
        "event_type": EVENT_TYPES,
        "region": REGIONS,
        "direction": DIRECTIONS,
        "time_horizon": TIME_HORIZONS,
    }
    for idx, row in enumerate(raw_rows):
        if not isinstance(row, dict):
            errors.append(
                {
                    "index": idx,
                    "field": "__row__",
                    "severity": "fatal",
                    "message": "provider row must be an object",
                    "value": repr(row),
                }
            )
            continue

        for field in ["date", "title"]:
            if not str(row.get(field) or "").strip():
                errors.append(
                    {
                        "index": idx,
                        "field": field,
                        "severity": "fatal" if strict else "review",
                        "message": f"missing {field}",
                        "value": "",
                    }
                )

        for field in ["evidence_span", "scenario_links"]:
            if not str(row.get(field) or "").strip():
                errors.append(
                    {
                        "index": idx,
                        "field": field,
                        "severity": "fatal" if strict else "review",
                        "message": f"missing {field}; row will require review or inference",
                        "value": "",
                    }
                )

        for field, valid_values in enum_fields.items():
            raw_value = str(row.get(field) or "").strip().lower()
            if raw_value and raw_value not in valid_values:
                errors.append(
                    {
                        "index": idx,
                        "field": field,
                        "severity": "fatal" if strict else "review",
                        "message": f"invalid {field}",
                        "value": raw_value,
                    }
                )

        scenario_links = split_multi(row.get("scenario_links"))
        invalid_links = [link for link in scenario_links if link not in SCENARIO_CODES]
        if invalid_links:
            errors.append(
                {
                    "index": idx,
                    "field": "scenario_links",
                    "severity": "fatal" if strict else "review",
                    "message": "invalid scenario link",
                    "value": "|".join(invalid_links),
                }
            )

        for field in PROVIDER_EVENT_SCHEMA["numeric_0_to_100"]:
            raw_value = row.get(field)
            if raw_value in (None, ""):
                continue
            parsed = parse_float(raw_value)
            if parsed is None or parsed < 0.0 or parsed > 100.0:
                errors.append(
                    {
                        "index": idx,
                        "field": field,
                        "severity": "fatal" if strict else "review",
                        "message": f"{field} must be between 0 and 100",
                        "value": raw_value,
                    }
                )
    return errors


def build_dedupe_key(row: dict[str, str]) -> str:
    date = (row.get("date") or "").strip()
    source = re.sub(r"\s+", " ", (row.get("source") or "").strip().lower())
    title = re.sub(r"\s+", " ", (row.get("title") or "").strip().lower())
    return "|".join([date, source, title])


def normalize_article_events(raw_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    rows = []
    for raw in raw_rows:
        date = (raw.get("date") or raw.get("published_date") or "").strip()
        title = (raw.get("title") or "").strip()
        source = (raw.get("source") or "manual").strip()
        evidence_span = (raw.get("evidence_span") or "").strip()
        scenario_links = infer_scenario_links(raw)
        severity = clip(parse_float(raw.get("severity"), 50.0) or 50.0)
        novelty = clip(parse_float(raw.get("novelty"), 50.0) or 50.0)
        extract_confidence = clip(parse_float(raw.get("extract_confidence"), 60.0) or 60.0)
        event_type = infer_event_type(raw)
        direction = infer_direction(raw)
        region = infer_region(raw)
        time_horizon = (raw.get("time_horizon") or "days").strip().lower()
        if time_horizon not in TIME_HORIZONS:
            time_horizon = "days"

        review_reasons = []
        if not date:
            review_reasons.append("missing_date")
        if not title:
            review_reasons.append("missing_title")
        if not evidence_span:
            review_reasons.append("missing_evidence_span")
        if raw.get("scenario_links") in (None, ""):
            review_reasons.append("scenario_links_inferred")
        if extract_confidence < 50:
            review_reasons.append("low_extract_confidence")

        row = {
            "date": date,
            "source": source,
            "title": title,
            "url_or_ref": (raw.get("url_or_ref") or raw.get("url") or "").strip(),
            "event_type": event_type,
            "region": region,
            "affected_assets": (raw.get("affected_assets") or "").strip(),
            "direction": direction,
            "severity": severity,
            "novelty": novelty,
            "time_horizon": time_horizon,
            "scenario_links": join_multi(scenario_links),
            "evidence_span": evidence_span,
            "extract_confidence": extract_confidence,
            "needs_review": "Y" if review_reasons else "N",
            "review_reason": "|".join(review_reasons),
            "engine_version": EVENT_OVERLAY_ENGINE_VERSION,
        }
        row["dedupe_key"] = build_dedupe_key(row)
        rows.append(row)

    return dedupe_article_events(rows)


def dedupe_article_events(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    by_key: dict[str, dict[str, object]] = {}
    for row in sorted(rows, key=lambda item: (str(item.get("date")), str(item.get("source")), str(item.get("title")))):
        key = str(row.get("dedupe_key") or build_dedupe_key(row))
        current = by_key.get(key)
        if current is None:
            by_key[key] = row
            continue
        current_score = (parse_float(current.get("severity"), 0.0) or 0.0) + (parse_float(current.get("extract_confidence"), 0.0) or 0.0)
        row_score = (parse_float(row.get("severity"), 0.0) or 0.0) + (parse_float(row.get("extract_confidence"), 0.0) or 0.0)
        if row_score > current_score:
            by_key[key] = row
    return sorted(by_key.values(), key=lambda item: (str(item.get("date")), str(item.get("source")), str(item.get("title"))))


def validate_article_rows(rows: list[dict[str, object]]) -> None:
    for row in rows:
        if not row.get("date"):
            raise AssertionError(f"event row missing date: {row}")
        if not row.get("title"):
            raise AssertionError(f"event row missing title: {row}")
        links = split_multi(row.get("scenario_links"))
        if not links or not all(link in SCENARIO_CODES for link in links):
            raise AssertionError(f"event row has invalid scenario_links: {row}")
        for key in ["severity", "novelty", "extract_confidence"]:
            value = parse_float(row.get(key))
            if value is None or not 0.0 <= value <= 100.0:
                raise AssertionError(f"{key} out of range: {row}")


def build_daily_overlay_rows(article_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in article_rows:
        if row.get("needs_review") == "Y" and not row.get("evidence_span"):
            continue
        for scenario_code in split_multi(row.get("scenario_links")):
            grouped[(str(row.get("date")), scenario_code)].append(row)

    daily_rows = []
    for (date, scenario_code), rows in sorted(grouped.items()):
        weights = []
        severities = []
        novelty_values = []
        for row in rows:
            severity = parse_float(row.get("severity"), 0.0) or 0.0
            novelty = parse_float(row.get("novelty"), 0.0) or 0.0
            confidence = (parse_float(row.get("extract_confidence"), 0.0) or 0.0) / 100.0
            review_weight = 0.5 if row.get("needs_review") == "Y" else 1.0
            weight = max(confidence * review_weight, 0.05)
            weights.append(weight)
            severities.append(severity)
            novelty_values.append(novelty)
        weighted_score = sum(severity * weight for severity, weight in zip(severities, weights)) / sum(weights)
        count_bonus = min(12.0, 4.0 * math.log1p(len(rows)))
        score = clip(weighted_score + count_bonus)
        confidence_values = [parse_float(row.get("extract_confidence"), 0.0) or 0.0 for row in rows]
        non_review_ratio = sum(1 for row in rows if row.get("needs_review") != "Y") / len(rows)
        overlay_confidence = clip((sum(confidence_values) / len(confidence_values)) * (0.65 + 0.35 * non_review_ratio))
        top_rows = sorted(rows, key=lambda row: (-(parse_float(row.get("severity"), 0.0) or 0.0), str(row.get("title"))))
        direction_counts = Counter(str(row.get("direction") or "") for row in rows)
        daily_rows.append(
            {
                "date": date,
                "scenario_code": scenario_code,
                "event_overlay_score": score,
                "event_count": len(rows),
                "needs_review_count": sum(1 for row in rows if row.get("needs_review") == "Y"),
                "avg_severity": sum(severities) / len(severities),
                "avg_novelty": sum(novelty_values) / len(novelty_values),
                "overlay_confidence": overlay_confidence,
                "event_types": join_multi({str(row.get("event_type") or "") for row in rows}),
                "regions": join_multi({str(row.get("region") or "") for row in rows}),
                "direction_summary": "|".join(f"{key}:{value}" for key, value in sorted(direction_counts.items())),
                "top_event_titles": " | ".join(str(row.get("title")) for row in top_rows[:3]),
                "evidence_summary": " | ".join(str(row.get("evidence_span")) for row in top_rows[:3] if row.get("evidence_span")),
                "source_count": len({str(row.get("source") or "") for row in rows}),
                "engine_version": EVENT_OVERLAY_ENGINE_VERSION,
            }
        )
    return daily_rows


def load_event_input(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            payload = payload.get("events", [])
        return [dict(row) for row in payload]
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def safe_round(value: object, digits: int = 6) -> object:
    if isinstance(value, float):
        return round(value, digits)
    return value


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: safe_round(row.get(key, "")) for key in fieldnames})


def esc(value: object) -> str:
    return html.escape(str(value if value is not None else ""))


def pct(value: object) -> str:
    parsed = parse_float(value)
    return "-" if parsed is None else f"{parsed:.1f}%"


def render_phase5_dashboard(article_rows: list[dict[str, object]], daily_rows: list[dict[str, object]], run_id: str) -> str:
    by_scenario = sorted(daily_rows, key=lambda row: (-(parse_float(row.get("event_overlay_score"), 0.0) or 0.0), str(row.get("scenario_code"))))
    review_rows = [row for row in article_rows if row.get("needs_review") == "Y"]
    cards = "\n".join(
        f"""
        <article class="card">
          <div class="eyebrow">{esc(row.get('date'))} · {esc(row.get('scenario_code'))}</div>
          <h3>{pct(row.get('event_overlay_score'))}</h3>
          <p>{esc(row.get('top_event_titles'))}</p>
          <small>confidence {pct(row.get('overlay_confidence'))} · events {esc(row.get('event_count'))} · {esc(row.get('direction_summary'))}</small>
        </article>
        """
        for row in by_scenario[:6]
    ) or "<p>표시할 이벤트 오버레이가 없습니다.</p>"
    article_table = "\n".join(
        f"<tr><td>{esc(row.get('date'))}</td><td>{esc(row.get('source'))}</td><td>{esc(row.get('title'))}<br><small>{esc(row.get('evidence_span'))}</small></td><td>{esc(row.get('scenario_links'))}</td><td>{pct(row.get('severity'))}</td><td>{esc(row.get('needs_review'))}</td></tr>"
        for row in article_rows
    )
    daily_table = "\n".join(
        f"<tr><td>{esc(row.get('date'))}</td><td>{esc(row.get('scenario_code'))}</td><td>{pct(row.get('event_overlay_score'))}</td><td>{pct(row.get('overlay_confidence'))}</td><td>{esc(row.get('event_types'))}</td><td>{esc(row.get('evidence_summary'))}</td></tr>"
        for row in by_scenario
    )
    review_block = "\n".join(
        f"<li><b>{esc(row.get('title'))}</b> — {esc(row.get('review_reason'))}</li>"
        for row in review_rows
    ) or "<li>검토 필요 이벤트 없음</li>"
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>Phase 5 Event Overlay · {esc(run_id)}</title>
  <style>
    :root {{ --ink:#17211b; --muted:#66756b; --paper:#f7f2e8; --card:#fffaf0; --accent:#276749; --warn:#b7791f; --line:#e3d8c7; }}
    body {{ margin:0; font-family: 'Aptos', 'Noto Sans KR', sans-serif; color:var(--ink); background:linear-gradient(135deg,#f7f2e8,#eaf3ea); }}
    main {{ max-width:1180px; margin:0 auto; padding:36px 24px 56px; }}
    h1 {{ font-size:34px; margin:0 0 8px; }}
    h2 {{ margin-top:34px; }}
    .lead {{ color:var(--muted); max-width:820px; }}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:16px; }}
    .card {{ background:var(--card); border:1px solid var(--line); border-radius:20px; padding:18px; box-shadow:0 12px 24px rgba(23,33,27,.08); }}
    .card h3 {{ color:var(--accent); font-size:30px; margin:8px 0; }}
    .eyebrow, small {{ color:var(--muted); }}
    table {{ width:100%; border-collapse:collapse; background:rgba(255,250,240,.86); border-radius:16px; overflow:hidden; }}
    th, td {{ border-bottom:1px solid var(--line); padding:10px 12px; text-align:left; vertical-align:top; }}
    th {{ background:#ecdfc8; }}
    .warn {{ color:var(--warn); }}
  </style>
</head>
<body>
<main>
  <h1>Phase 5 뉴스/정책 이벤트 오버레이</h1>
  <p class="lead">이 화면은 뉴스/정책문이 어떤 시나리오를 보조적으로 밀었는지 보여줍니다. 현재 기본 실행기는 reviewed local fixture 샘플을 기준으로 하며, live research feed나 Phase 6 최종 병합 결과는 아직 포함하지 않습니다.</p>
  <section class="grid">{cards}</section>
  <h2>Scenario Daily Overlay</h2>
  <table><thead><tr><th>Date</th><th>Scenario</th><th>Overlay</th><th>Confidence</th><th>Event Types</th><th>Evidence</th></tr></thead><tbody>{daily_table}</tbody></table>
  <h2>Article Events</h2>
  <table><thead><tr><th>Date</th><th>Source</th><th>Title / Evidence</th><th>Scenario Links</th><th>Severity</th><th>Review</th></tr></thead><tbody>{article_table}</tbody></table>
  <h2 class="warn">Needs Review</h2>
  <ul>{review_block}</ul>
</main>
</body>
</html>
"""


def render_event_review_markdown(article_rows: list[dict[str, object]], daily_rows: list[dict[str, object]], run_id: str) -> str:
    lines = [
        "# Phase 5 Event Overlay Review",
        "",
        f"- run_id: `{run_id}`",
        f"- article_events: {len(article_rows)}",
        f"- daily_overlay_rows: {len(daily_rows)}",
        f"- needs_review: {sum(1 for row in article_rows if row.get('needs_review') == 'Y')}",
        "- 해석 범위: 뉴스/정책 이벤트는 Phase 4 정형 장세 판단의 보조 오버레이입니다.",
        "- 현재 실행 단계: reviewed local fixture 기반 샘플이며, live research feed/Phase 6 최종 병합은 아직 별도 단계입니다.",
        "",
        "## Scenario Overlay",
    ]
    for row in sorted(daily_rows, key=lambda item: (str(item.get("date")), -(parse_float(item.get("event_overlay_score"), 0.0) or 0.0))):
        lines.append(
            f"- `{row.get('date')}` `{row.get('scenario_code')}`: score={parse_float(row.get('event_overlay_score'), 0.0):.2f}, "
            f"confidence={parse_float(row.get('overlay_confidence'), 0.0):.2f}, events={row.get('event_count')}"
        )
    lines.extend(["", "## Review Queue"])
    review_rows = [row for row in article_rows if row.get("needs_review") == "Y"]
    if not review_rows:
        lines.append("- 검토 필요 이벤트 없음")
    for row in review_rows:
        lines.append(f"- `{row.get('date')}` {row.get('title')} — {row.get('review_reason')}")
    return "\n".join(lines).rstrip() + "\n"
