#!/usr/bin/env python3
"""Generate a self-contained dashboard for Scenario Research -> HedgeMate review.

The Phase 4 dashboard explains the market diagnosis itself.  This companion
dashboard checks the next integration boundary: whether the latest scenario
vector is visible, whether HedgeMate consumed it, and whether recommendation
outputs expose scenario-aware signals that can be inspected by eye.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
HEDGEMATE_ROOT = ROOT.parent / "HedgeMate"

FAVORABLE_SCENARIO_CODES = {"soft_landing_goldilocks"}
STATE_KO = {
    "STRONG": "강한 우호장",
    "STRESS": "위험",
    "ACTIVE": "활성",
    "WATCH": "관찰",
    "OFF": "비활성",
    "PROVISIONAL": "임시 신호",
}
ROLE_KO = {
    "scenario_vulnerability_reducer": "현재 장세 취약도 완화 후보",
    "scenario_vulnerability_additive": "현재 장세 취약도 추가 후보",
    "scenario_neutral": "시나리오 중립 후보",
    "inflation_hedge": "물가/에너지 헤지 성격",
    "rate_sensitive": "금리 민감 성격",
    "krw_weakness_hedge": "원화 약세 헤지 성격",
    "krw_weakness_vulnerable": "원화 약세 취약 성격",
    "slowdown_defense": "경기둔화 방어 성격",
    "slowdown_vulnerable": "경기둔화 취약 성격",
    "liquidity_stress_defense": "리스크오프 방어 성격",
    "liquidity_stress_vulnerable": "리스크오프 취약 성격",
    "china_asia_shock_hedge": "중국/아시아 충격 헤지 성격",
    "china_asia_shock_vulnerable": "중국/아시아 충격 취약 성격",
    "risk_on_participation": "위험선호 참여 성격",
    "neutral_or_defensive": "중립/방어 성격",
}


def esc(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def f(row: dict[str, str], key: str, default: float = 0.0) -> float:
    try:
        value = row.get(key, "")
        if value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def fmt(value: object, digits: int = 2) -> str:
    try:
        if value == "":
            return "-"
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "-"


def pct(value: object, digits: int = 0) -> str:
    try:
        if value == "":
            return "-"
        return f"{float(value) * 100:.{digits}f}%"
    except (TypeError, ValueError):
        return "-"


def pill(text: str, cls: str = "") -> str:
    return f"<span class='pill {esc(cls)}'>{esc(text)}</span>"


def state_pill(raw_state: str, display_state: str) -> str:
    shown = display_state or raw_state
    cls = shown.lower().replace("_", "-")
    label = STATE_KO.get(shown, shown)
    raw = f"<small>raw: {esc(raw_state)}</small>" if raw_state and raw_state != shown else ""
    return f"<span class='pill {cls}'>{esc(shown)} · {esc(label)}</span>{raw}"


def score_color(score: float, scenario_code: str, display_state: str) -> str:
    if display_state == "PROVISIONAL":
        return "#ffb454"
    if scenario_code in FAVORABLE_SCENARIO_CODES and score >= 60:
        return "#00d49a"
    if score >= 75:
        return "#ff4d5e"
    if score >= 60:
        return "#00d49a"
    if score >= 45:
        return "#d967ff"
    return "#73809b"


def score_bar(score: float, scenario_code: str = "", display_state: str = "") -> str:
    width = max(0.0, min(score, 100.0))
    color = score_color(score, scenario_code, display_state)
    return f"<div class='bar'><span style='width:{width:.1f}%;background:{color}'></span></div><small>{score:.1f}</small>"


def table(headers: list[str], rows: list[list[str]], empty: str = "표시할 데이터가 없습니다.") -> str:
    if not rows:
        return f"<p class='muted'>{esc(empty)}</p>"
    head = "".join(f"<th>{esc(header)}</th>" for header in headers)
    body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def status_badge(ok: bool, text: str) -> str:
    return pill(("OK · " if ok else "점검 · ") + text, "good" if ok else "warn")


def render_scenario_vector(rows: list[dict[str, str]]) -> str:
    ordered = sorted(rows, key=lambda row: -f(row, "score"))
    body = []
    for row in ordered:
        positives = row.get("top_positive_drivers") or "-"
        negatives = row.get("top_negative_drivers") or "-"
        body.append(
            [
                (
                    f"<b>{esc(row.get('scenario_name_ko') or row.get('scenario_name'))}</b>"
                    f"<br><small>{esc(row.get('scenario_name'))}</small>"
                    f"<br><small>lens: {esc(row.get('lens'))}</small>"
                ),
                state_pill(row.get("raw_state", ""), row.get("display_state", "")),
                score_bar(f(row, "score"), row.get("scenario_code", ""), row.get("display_state", "")),
                f"{pct(row.get('coverage'))}<br><small>confidence {fmt(row.get('confidence'), 1)}</small>",
                f"<small><b>+</b> {esc(positives)}<br><b>-</b> {esc(negatives)}</small>",
            ]
        )
    return table(["시나리오", "상태", "점수", "신뢰도", "근거"], body)


def render_range_summary(rows: list[dict[str, str]]) -> str:
    body = []
    for row in rows:
        status = row.get("data_status", "")
        cls = "good" if status == "OK" else "warn" if status in {"LOW_COVERAGE", "PARTIAL"} else "bad"
        body.append(
            [
                esc(row.get("date")),
                pill(status or "-", cls),
                f"{esc(row.get('scenario_ko') or '-')}<br><small>{esc(row.get('top_scenario') or '-')}</small>",
                score_bar(f(row, "top_score"), "", row.get("top_display_state", "")) if row.get("top_score") else "-",
                esc(row.get("status_detail") or "-"),
                f"<small><b>+</b> {esc(row.get('positive_drivers') or '-')}<br><b>-</b> {esc(row.get('anti_drivers') or '-')}</small>",
            ]
        )
    return table(["날짜", "데이터", "Top 장세", "Top 점수", "상태 설명", "주요 근거"], body)


def top_recommendations(rows: list[dict[str, str]], limit: int = 8) -> list[dict[str, str]]:
    valid = [row for row in rows if row.get("status", "").lower() != "failed"]
    return sorted(valid, key=lambda row: f(row, "final_score"), reverse=True)[:limit]


def render_recommendations(title: str, rows: list[dict[str, str]]) -> str:
    body = []
    for row in top_recommendations(rows):
        role = row.get("recommended_role") or "-"
        role_text = ROLE_KO.get(role, role)
        scenario_component = row.get("scenario_score_component", "")
        scenario_reduction = row.get("scenario_vulnerability_reduction", "")
        penalties = [
            f"adverse {fmt(row.get('adverse_scenario_penalty'), 3)}",
            f"concentration {fmt(row.get('factor_concentration_penalty'), 3)}",
        ]
        body.append(
            [
                f"<b>{esc(row.get('candidate_ticker') or '-')}</b><br><small>{esc(row.get('candidate_bucket') or '-')}</small>",
                score_bar(f(row, "final_score") * 100.0),
                f"{fmt(scenario_component, 3)}<br><small>vuln ↓ {fmt(scenario_reduction, 3)}</small>",
                f"{esc(role_text)}<br><small>{esc(role)}</small>",
                f"<small>{esc(row.get('scenario_reason_ko') or row.get('recommendation_reason') or '-')}</small>",
                f"<small>{esc(' · '.join(penalties))}</small>",
            ]
        )
    return f"<h3>{esc(title)}</h3>" + table(
        ["후보", "최종점수", "시나리오 성분", "역할", "한국어 사유", "패널티"],
        body,
        "추천 결과가 없습니다.",
    )


def render_sensitivity_summary(
    scenario_rows: list[dict[str, str]], sensitivity_rows: list[dict[str, str]]
) -> str:
    scenario_by_code = {row.get("scenario_code"): row for row in scenario_rows}
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in sensitivity_rows:
        grouped[row.get("scenario_code", "")].append(row)

    body = []
    for code, rows in sorted(grouped.items(), key=lambda item: -f(scenario_by_code.get(item[0], {}), "score")):
        scenario = scenario_by_code.get(code, {})
        levels = Counter(row.get("sensitivity_level", "") for row in rows)
        directions = Counter(row.get("direction", "") for row in rows)
        top_assets = sorted(rows, key=lambda row: f(row, "magnitude"), reverse=True)[:5]
        top_text = ", ".join(f"{row.get('ticker')}({fmt(row.get('magnitude'), 2)})" for row in top_assets)
        body.append(
            [
                (
                    f"<b>{esc(scenario.get('scenario_name_ko') or rows[0].get('scenario_name_ko') or code)}</b>"
                    f"<br><small>{esc(code)} · lens {esc(scenario.get('lens') or rows[0].get('lens'))}</small>"
                ),
                score_bar(f(scenario, "score"), code, scenario.get("display_state", "")),
                f"high {levels.get('high', 0)} · medium {levels.get('medium', 0)} · low {levels.get('low', 0)}",
                f"+ {directions.get('positive', 0)} · - {directions.get('negative', 0)} · 0 {directions.get('neutral', 0)}",
                f"<small>{esc(top_text or '-')}</small>",
            ]
        )
    return table(["시나리오", "현재 점수", "민감도 분포", "방향", "상위 민감 자산"], body)


def render_lens_counts(scenario_rows: list[dict[str, str]], sensitivity_rows: list[dict[str, str]]) -> str:
    scenario_lens_counts = Counter(row.get("lens") or "unknown" for row in scenario_rows)
    sensitivity_lens_counts = Counter(row.get("lens") or "unknown" for row in sensitivity_rows)
    all_lenses = sorted(set(scenario_lens_counts) | set(sensitivity_lens_counts))
    rows = [
        [
            esc(lens),
            str(scenario_lens_counts.get(lens, 0)),
            str(sensitivity_lens_counts.get(lens, 0)),
        ]
        for lens in all_lenses
    ]
    return table(["렌즈", "진단 시나리오 수", "자산 민감도 row 수"], rows)


def build_dashboard(
    run_id: str,
    hedgemate_run_id: str,
    range_start: str,
    range_end: str,
    output: Path | None = None,
) -> Path:
    reports = ROOT / "outputs" / "reports"
    scenario_vector_path = ROOT / "outputs" / "scenario_vectors" / f"current_scenario_vector_{run_id}.csv"
    metadata_path = reports / f"scenario_snapshot_metadata_{run_id}.json"
    range_path = reports / f"phase4_range_review_{run_id}_{range_start}_to_{range_end}.csv"

    sensitivity_path = (
        HEDGEMATE_ROOT
        / "outputs"
        / "processed"
        / f"asset_scenario_sensitivity_{hedgemate_run_id}.csv"
    )
    single_path = HEDGEMATE_ROOT / "outputs" / "reports" / f"single_asset_hedge_1to1_{hedgemate_run_id}.csv"
    portfolio_path = HEDGEMATE_ROOT / "outputs" / "reports" / f"portfolio_1to1_hedge_{hedgemate_run_id}.csv"

    scenario_rows = load_csv(scenario_vector_path)
    metadata = load_json(metadata_path)
    range_rows = load_csv(range_path)
    sensitivity_rows = load_csv(sensitivity_path)
    single_rows = load_csv(single_path)
    portfolio_rows = load_csv(portfolio_path)

    as_of_date = scenario_rows[0].get("as_of_date", "-") if scenario_rows else "-"
    anchor_date = metadata.get("anchor_date", "-")
    anchor_count = metadata.get("anchor_ticker_count", 0)
    total_tickers = metadata.get("total_tickers", 0)
    anchor_coverage = metadata.get("anchor_ticker_coverage_ratio", 0.0)
    latest_generated = metadata.get("generated_at", "-")
    top_scenario = max(scenario_rows, key=lambda row: f(row, "score"), default={})
    active_adverse = [
        row
        for row in scenario_rows
        if row.get("scenario_code") not in FAVORABLE_SCENARIO_CODES
        and (f(row, "score") >= 45 or row.get("display_state") in {"WATCH", "ACTIVE", "STRESS"})
    ]
    latest_ok = len(scenario_rows) == 7 and float(anchor_coverage or 0.0) >= 0.75
    rec_fields = set(single_rows[0].keys() if single_rows else []) | set(portfolio_rows[0].keys() if portfolio_rows else [])
    has_rec_fields = {
        "scenario_score_component",
        "scenario_vulnerability_reduction",
        "adverse_scenario_penalty",
        "factor_concentration_penalty",
        "scenario_reason_ko",
    }.issubset(rec_fields)
    nonzero_scenario_component = any(abs(f(row, "scenario_score_component")) > 1e-9 for row in single_rows + portfolio_rows)
    korean_reason_present = any(row.get("scenario_reason_ko") for row in single_rows + portfolio_rows)

    cards = [
        ("시나리오 기준일", as_of_date, f"anchor {anchor_date}, generated {latest_generated}"),
        ("진단 커버리지", f"{anchor_count}/{total_tickers}", f"anchor coverage {pct(anchor_coverage, 0)}"),
        ("Top 장세", top_scenario.get("scenario_name_ko", "-"), top_scenario.get("market_interpretation_ko", "")),
        ("HedgeMate run", hedgemate_run_id, f"sensitivity rows {len(sensitivity_rows)}, rec rows {len(single_rows) + len(portfolio_rows)}"),
    ]

    checklist = [
        status_badge(len(scenario_rows) == 7, f"시나리오 벡터 7개 row ({len(scenario_rows)})"),
        status_badge(latest_ok, f"정렬 기준일 {anchor_date}, 커버리지 {pct(anchor_coverage, 0)}"),
        status_badge(bool(sensitivity_rows), f"HedgeMate 자산×시나리오 민감도 {len(sensitivity_rows)} rows"),
        status_badge(has_rec_fields, "추천 CSV에 시나리오 조정 필드 존재"),
        status_badge(nonzero_scenario_component, "추천 점수에 scenario_score_component 반영"),
        status_badge(korean_reason_present, "추천 사유에 한국어 장세 설명 존재"),
        status_badge(bool(range_rows), f"{range_start}~{range_end} 날짜별 리뷰 CSV 존재"),
    ]

    html_doc = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Scenario Research → HedgeMate 통합 리뷰 · {esc(run_id)}</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg:#08111f; --panel:#101b2f; --panel2:#15233b; --text:#edf4ff; --muted:#9aabc4;
      --line:#273852; --good:#00d49a; --warn:#ffb454; --bad:#ff5c72; --pink:#d967ff;
    }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; padding:28px; background:radial-gradient(circle at top left,#1f355b 0,#08111f 42%,#050912 100%); color:var(--text); font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
    h1 {{ margin:0 0 8px; font-size:30px; letter-spacing:-.03em; }}
    h2 {{ margin:30px 0 12px; font-size:20px; }}
    h3 {{ margin:18px 0 10px; color:#dbe8ff; }}
    p {{ color:var(--muted); line-height:1.55; }}
    .hero {{ border:1px solid var(--line); background:linear-gradient(135deg,rgba(21,35,59,.94),rgba(9,17,31,.94)); border-radius:22px; padding:24px; box-shadow:0 20px 70px rgba(0,0,0,.28); }}
    .grid {{ display:grid; gap:14px; }}
    .cards {{ grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); margin-top:18px; }}
    .card {{ background:rgba(16,27,47,.85); border:1px solid var(--line); border-radius:18px; padding:16px; }}
    .card small,.muted,small {{ color:var(--muted); }}
    .metric {{ font-size:22px; font-weight:800; margin:6px 0; }}
    .flow {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:10px; margin-top:12px; }}
    .step {{ border:1px solid var(--line); border-radius:16px; background:rgba(255,255,255,.035); padding:14px; position:relative; }}
    .step b {{ color:#fff; }}
    table {{ width:100%; border-collapse:collapse; overflow:hidden; border-radius:14px; background:rgba(9,17,31,.65); }}
    th,td {{ border-bottom:1px solid var(--line); padding:11px 12px; text-align:left; vertical-align:top; }}
    th {{ color:#c9d9f2; font-size:12px; text-transform:uppercase; letter-spacing:.06em; background:rgba(255,255,255,.04); }}
    tr:last-child td {{ border-bottom:0; }}
    .pill {{ display:inline-block; padding:4px 9px; border-radius:999px; border:1px solid var(--line); background:rgba(255,255,255,.055); color:#dbe8ff; font-size:12px; font-weight:700; margin:2px 4px 2px 0; }}
    .pill.good,.pill.strong {{ border-color:rgba(0,212,154,.45); background:rgba(0,212,154,.12); color:#8dffd9; }}
    .pill.warn,.pill.watch,.pill.provisional {{ border-color:rgba(255,180,84,.48); background:rgba(255,180,84,.12); color:#ffd6a1; }}
    .pill.bad,.pill.stress {{ border-color:rgba(255,92,114,.5); background:rgba(255,92,114,.12); color:#ffb2bf; }}
    .pill.off {{ color:#b8c4d8; }}
    .bar {{ width:130px; height:9px; border-radius:99px; background:#263550; overflow:hidden; margin:4px 0; }}
    .bar span {{ display:block; height:100%; border-radius:99px; }}
    .section {{ margin-top:22px; padding:18px; border:1px solid var(--line); border-radius:20px; background:rgba(16,27,47,.72); }}
    .checklist {{ display:flex; flex-wrap:wrap; gap:6px; }}
    .path {{ font-family:ui-monospace,SFMono-Regular,Consolas,monospace; color:#b7c7df; word-break:break-all; }}
    a {{ color:#90cdfd; }}
  </style>
</head>
<body>
  <section class="hero">
    <h1>Scenario Research → HedgeMate 통합 리뷰</h1>
    <p>
      최신 수집 데이터로 만든 장세 진단 벡터가 HedgeMate 추천 점수에 실제로 연결됐는지 확인하는 화면입니다.
      오늘({esc(run_id)}) 실행 기준, 시나리오 정렬 anchor는 <b>{esc(anchor_date)}</b>입니다.
      한국/환율 일부 ticker는 2026-05-07 값이 있을 수 있지만, 미국장 포함 75% 이상 공통 정렬 기준은 {esc(anchor_date)}입니다.
    </p>
    <div class="grid cards">
      {''.join(f"<div class='card'><small>{esc(label)}</small><div class='metric'>{esc(value)}</div><small>{esc(detail)}</small></div>" for label, value, detail in cards)}
    </div>
    <div class="flow">
      <div class="step"><b>1. Scenario Research</b><p>시장 proxy와 breadth를 정렬해 7개 시나리오 점수/상태/근거를 생성합니다.</p></div>
      <div class="step"><b>2. Current Scenario Vector</b><p>HedgeMate가 소비할 수 있는 1일 기준 diagnosis vector CSV/JSON을 생성합니다.</p></div>
      <div class="step"><b>3. Asset Sensitivity Mapping</b><p>자산별 장세 민감도와 취약/헤지 역할을 매핑합니다.</p></div>
      <div class="step"><b>4. Scenario-aware Recommendation</b><p>취약도를 낮추는 후보는 가점, 장세 취약/집중 후보는 감점합니다.</p></div>
    </div>
  </section>

  <section class="section">
    <h2>눈으로 확인할 체크리스트</h2>
    <div class="checklist">{''.join(checklist)}</div>
  </section>

  <section class="section">
    <h2>현재 장세 진단 벡터</h2>
    <p>이 표가 HedgeMate 추천 로직으로 넘어가는 핵심 입력입니다. PROVISIONAL은 방향은 보이지만 coverage/confidence가 부족하므로 과신하면 안 되는 상태입니다.</p>
    {render_scenario_vector(scenario_rows)}
  </section>

  <section class="section">
    <h2>{esc(range_start)} ~ {esc(range_end)} 날짜별 리뷰</h2>
    <p>주말/미국장 미정렬일/저커버리지일을 억지로 forward-fill하지 않고 별도 표시합니다.</p>
    {render_range_summary(range_rows)}
  </section>

  <section class="section">
    <h2>HedgeMate 추천 결과: 시나리오 반영 확인</h2>
    <p>시나리오 성분이 0.5보다 크면 현재 장세에서 취약도를 낮추는 방향으로 보정된 후보로 해석할 수 있습니다.</p>
    {render_recommendations("단일자산 005930.KS 기준", single_rows)}
    {render_recommendations("포트폴리오 기준", portfolio_rows)}
  </section>

  <section class="section">
    <h2>자산×시나리오 민감도 매핑 요약</h2>
    <p>현재 수집 자산이 어떤 장세 lens에 민감하게 분포하는지 확인합니다. 추천 후보가 이 매핑을 통해 가점/감점됩니다.</p>
    {render_lens_counts(scenario_rows, sensitivity_rows)}
    <h3>시나리오별 민감도 분포</h3>
    {render_sensitivity_summary(scenario_rows, sensitivity_rows)}
  </section>

  <section class="section">
    <h2>파일 링크/경로</h2>
    <p class="path">Scenario vector: {esc(scenario_vector_path)}</p>
    <p class="path">Phase4 latest dashboard: {esc(reports / f'phase4_review_dashboard_{run_id}.html')}</p>
    <p class="path">Phase4 range dashboard: {esc(reports / f'phase4_range_review_{run_id}_{range_start}_to_{range_end}.html')}</p>
    <p class="path">HedgeMate sensitivity: {esc(sensitivity_path)}</p>
    <p class="path">HedgeMate single-asset rec: {esc(single_path)}</p>
    <p class="path">HedgeMate portfolio rec: {esc(portfolio_path)}</p>
  </section>
</body>
</html>
"""

    output_path = output or reports / f"integration_review_dashboard_{run_id}.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_doc, encoding="utf-8")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, help="Scenario Research run id")
    parser.add_argument("--hedgemate-run-id", required=True, help="HedgeMate run id that consumed the scenario vector")
    parser.add_argument("--range-start", default="2026-05-01")
    parser.add_argument("--range-end", default="2026-05-07")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = build_dashboard(args.run_id, args.hedgemate_run_id, args.range_start, args.range_end, args.output)
    print(output)


if __name__ == "__main__":
    main()
