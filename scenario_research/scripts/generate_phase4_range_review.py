#!/usr/bin/env python3
"""Generate a date-range Phase 4 scenario review dashboard.

This is a lightweight, dependency-free companion to the Phase 4 review dashboard.
It creates one HTML and one CSV file for a calendar date range, explicitly marking
non-trading / low-coverage / not-yet-aligned dates instead of filling data forward.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import math
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
STATE_KO = {
    "STRONG": "강한 우호장",
    "STRESS": "위험",
    "ACTIVE": "활성",
    "WATCH": "관찰",
    "OFF": "비활성",
    "PROVISIONAL": "임시 신호",
}
MIN_TRUSTED_COVERAGE = 0.75
MIN_TRUSTED_CONFIDENCE = 40.0
FAVORABLE_SCENARIOS = {"Soft Landing / Goldilocks"}
SCENARIO_SHORT = {
    "Soft Landing / Goldilocks": "Soft Landing",
    "Slowdown / Recession / Deflation Risk": "Slowdown",
    "Higher-for-Longer / Long-Rate Shock": "Long-Rate",
    "Stagflation / Reinflation / Energy Shock": "Stagflation",
    "USD Strength / KRW Weakness": "KRW Weakness",
    "Acute Global Stress / Liquidity Crunch": "Global Stress",
    "China / Trade Fragmentation Shock": "China Shock",
}
SCENARIO_KO = {
    "Soft Landing / Goldilocks": ("우호적 위험선호장", "성장은 버티고 물가 부담은 완화되어 주식·성장자산에 우호적인 장세입니다."),
    "Slowdown / Recession / Deflation Risk": ("경기둔화/침체 우려장", "수요 둔화와 경기침체, 디플레이션 압력이 커지는 방어적 장세입니다."),
    "Higher-for-Longer / Long-Rate Shock": ("장기금리 부담장", "장기금리 상승과 긴축 부담이 채권·성장주·신용자산을 압박하는 장세입니다."),
    "Stagflation / Reinflation / Energy Shock": ("물가·에너지 재상승장", "성장 부담이 있는데 유가·원자재·인플레이션 압력이 다시 커지는 장세입니다."),
    "USD Strength / KRW Weakness": ("달러강세/원화약세장", "달러가 강하고 원화가 약해져 KRW 기준 투자자의 환율 리스크가 커지는 장세입니다."),
    "Acute Global Stress / Liquidity Crunch": ("급성 리스크오프/유동성 경색장", "변동성이 튀고 위험자산이 동반 약세를 보이는 단기 스트레스 장세입니다."),
    "China / Trade Fragmentation Shock": ("중국·무역분절 충격장", "중국 경기·무역갈등·공급망 충격이 한국과 아시아 자산에 번지는 장세입니다."),
}
CHECKS = [
    "Top scenario 확인",
    "7개 시나리오 점수 순위",
    "Positive driver 확인",
    "Anti-driver / 반대근거 확인",
    "Coverage / confidence 경고",
    "최근 흐름 확인",
]


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def f(row: dict[str, str], key: str, default: float = 0.0) -> float:
    try:
        return float(row.get(key, ""))
    except (TypeError, ValueError):
        return default


def fmt(value: object, digits: int = 1) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "-"


def pct(value: float) -> str:
    return f"{value * 100:.0f}%"


def daterange(start: str, end: str) -> list[str]:
    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end)
    out = []
    current = start_date
    while current <= end_date:
        out.append(current.isoformat())
        current += timedelta(days=1)
    return out


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def color(score: float, scenario_name: str = "", trusted: bool = True) -> str:
    if not trusted:
        return "#ffbc69"
    if scenario_name in FAVORABLE_SCENARIOS and score >= 60:
        return "#00e5a8"
    if score >= 75:
        return "#ff4d5e"
    if score >= 60:
        return "#00e5a8"
    if score >= 45:
        return "#ff2ea6"
    return "#6d7892"


def state_class(state: str) -> str:
    return state.lower()


def pill(state: str) -> str:
    return f"<span class='pill {state_class(state)}'>{esc(state)} · {esc(STATE_KO.get(state, state))}</span>"


def is_trusted(row: dict[str, str], status: str = "OK") -> bool:
    return (
        status == "OK"
        and f(row, "coverage_ratio") >= MIN_TRUSTED_COVERAGE
        and f(row, "confidence") >= MIN_TRUSTED_CONFIDENCE
    )


def display_state(row: dict[str, str], status: str = "OK") -> str:
    if not is_trusted(row, status):
        return "PROVISIONAL"
    if row.get("display_state"):
        return row["display_state"]
    raw_state = row.get("raw_state") or row["state_label"]
    if row["scenario_name"] in FAVORABLE_SCENARIOS and raw_state == "STRESS":
        return "STRONG"
    return raw_state


def scenario_title(name: str) -> str:
    ko, _ = SCENARIO_KO.get(name, ("", ""))
    short = SCENARIO_SHORT.get(name, name)
    return f"{short} · {ko}" if ko else short


def scenario_description(name: str) -> str:
    return SCENARIO_KO.get(name, ("", ""))[1]


def sparkline(values: list[float], width: int = 160, height: int = 30) -> str:
    if not values:
        return ""
    if len(values) == 1:
        values = values * 2
    mn, mx = min(values), max(values)
    span = mx - mn if mx != mn else 1.0
    pts = []
    for i, value in enumerate(values):
        x = i * width / (len(values) - 1)
        y = height - ((value - mn) / span * (height - 6) + 3)
        pts.append(f"{x:.1f},{y:.1f}")
    return f"<svg class='spark' viewBox='0 0 {width} {height}'><polyline points='{' '.join(pts)}' /></svg>"


def drivers_for(date_str: str, scenario: str, feature_rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    rows = [row for row in feature_rows if row["date"] == date_str and row["scenario_name"] == scenario]
    positives = sorted([row for row in rows if f(row, "contribution") > 0], key=lambda r: -f(r, "contribution"))[:3]
    negatives = sorted([row for row in rows if f(row, "contribution") < 0], key=lambda r: f(r, "contribution"))[:3]
    return positives, negatives


def day_status(day_rows: list[dict[str, str]]) -> tuple[str, str]:
    if not day_rows:
        return "NO_DATA", "시장/정렬 데이터 없음"
    scenario_count = len({row["scenario_name"] for row in day_rows})
    avg_cov = mean([f(row, "coverage_ratio") for row in day_rows])
    if scenario_count < 7:
        return "PARTIAL", f"부분 데이터: {scenario_count}/7 scenarios"
    if avg_cov < 0.75:
        return "LOW_COVERAGE", f"평균 coverage {pct(avg_cov)}"
    return "OK", f"7/7 scenarios · 평균 coverage {pct(avg_cov)}"


def check_statuses(day_rows: list[dict[str, str]], positive: list[dict[str, str]], negative: list[dict[str, str]]) -> list[tuple[str, str, str]]:
    if not day_rows:
        return [(item, "불가", "bad") for item in CHECKS]
    scenario_count = len({row["scenario_name"] for row in day_rows})
    top = sorted(day_rows, key=lambda row: -f(row, "structured_score"))[0]
    top_cov = f(top, "coverage_ratio")
    top_conf = f(top, "confidence")
    avg_cov = mean([f(row, "coverage_ratio") for row in day_rows])
    return [
        (CHECKS[0], "가능", "good"),
        (CHECKS[1], "가능" if scenario_count == 7 else f"부분 {scenario_count}/7", "good" if scenario_count == 7 else "warn"),
        (CHECKS[2], "가능" if positive else "부족", "good" if positive else "warn"),
        (CHECKS[3], "가능" if negative else "부족", "good" if negative else "warn"),
        (CHECKS[4], "주의" if top_cov < MIN_TRUSTED_COVERAGE or avg_cov < MIN_TRUSTED_COVERAGE or top_conf < MIN_TRUSTED_CONFIDENCE else "OK", "warn" if top_cov < MIN_TRUSTED_COVERAGE or avg_cov < MIN_TRUSTED_COVERAGE or top_conf < MIN_TRUSTED_CONFIDENCE else "good"),
        (CHECKS[5], "가능", "good"),
    ]


def render_driver_list(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "<li>없음</li>"
    return "".join(
        f"<li><b>{esc(row['signal_label'])}</b> <span>contribution {f(row, 'contribution'):+.3f}, z {f(row, 'normalized_value'):+.2f}</span></li>"
        for row in rows
    )


def render_score_table(day_rows: list[dict[str, str]], status: str) -> str:
    if not day_rows:
        return "<p class='muted'>해당 날짜의 시나리오 state row가 없습니다.</p>"
    body = []
    for row in sorted(day_rows, key=lambda item: -f(item, "structured_score")):
        score = f(row, "structured_score")
        shown_state = display_state(row, status)
        body.append(
            f"<tr><td><b>{esc(scenario_title(row['scenario_name']))}</b><br><small>lens: {esc(row.get('lens', 'legacy'))} · {esc(row.get('market_interpretation_ko') or scenario_description(row['scenario_name']))}</small></td>"
            f"<td>{pill(shown_state)}<br><small>raw: {esc(row.get('raw_state') or row['state_label'])}</small></td>"
            f"<td><div class='bar'><span style='width:{min(score,100):.1f}%;background:{color(score, row['scenario_name'], is_trusted(row, status))}'></span></div><small>{score:.1f}</small></td>"
            f"<td>{pct(f(row, 'coverage_ratio'))}</td><td>{fmt(row['confidence'])}</td></tr>"
        )
    return "<table><thead><tr><th>Scenario</th><th>State</th><th>Score</th><th>Coverage</th><th>Confidence</th></tr></thead><tbody>" + "".join(body) + "</tbody></table>"


def build(run_id: str, start: str, end: str) -> tuple[Path, Path]:
    processed = ROOT / "outputs" / "processed"
    reports = ROOT / "outputs" / "reports"
    state_path = processed / f"scenario_state_daily_{run_id}.csv"
    feature_path = processed / f"scenario_feature_daily_{run_id}.csv"
    metadata_path = reports / f"scenario_snapshot_metadata_{run_id}.json"
    state_rows = load_csv(state_path)
    feature_rows = load_csv(feature_path)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}

    rows_by_date = defaultdict(list)
    rows_by_scenario = defaultdict(list)
    for row in state_rows:
        rows_by_date[row["date"]].append(row)
        rows_by_scenario[row["scenario_name"]].append(row)

    target_dates = daterange(start, end)
    summary_rows: list[dict[str, str]] = []
    cards = []

    for date_str in target_dates:
        day_rows = rows_by_date.get(date_str, [])
        status, status_detail = day_status(day_rows)
        if day_rows:
            top = sorted(day_rows, key=lambda row: -f(row, "structured_score"))[0]
            scenario = top["scenario_name"]
            positives, negatives = drivers_for(date_str, scenario, feature_rows)
            recent_scores = [f(row, "structured_score") for row in sorted(rows_by_scenario[scenario], key=lambda r: r["date"]) if row["date"] <= date_str][-45:]
            active_count = sum(1 for row in day_rows if row["state_label"] == "ACTIVE")
            watch_count = sum(1 for row in day_rows if row["state_label"] == "WATCH")
            stress_count = sum(1 for row in day_rows if row["state_label"] == "STRESS")
            avg_cov = mean([f(row, "coverage_ratio") for row in day_rows])
            checks = check_statuses(day_rows, positives, negatives)
        else:
            top = None
            scenario = ""
            positives = []
            negatives = []
            recent_scores = []
            active_count = watch_count = stress_count = 0
            avg_cov = 0.0
            checks = check_statuses(day_rows, positives, negatives)

        summary_rows.append(
            {
                "date": date_str,
                "data_status": status,
                "status_detail": status_detail,
                "scenario_count": str(len(day_rows)),
                "avg_coverage": f"{avg_cov:.4f}" if day_rows else "",
                "top_scenario": scenario,
                "top_lens": top.get("lens", "") if top else "",
                "top_raw_state": top["state_label"] if top else "",
                "top_display_state": display_state(top, status) if top else "",
                "scenario_ko": top.get("scenario_name_ko") or SCENARIO_KO.get(scenario, ("", ""))[0] if top else "",
                "scenario_description": top.get("market_interpretation_ko") or scenario_description(scenario) if top else "",
                "top_score": f"{f(top, 'structured_score'):.4f}" if top else "",
                "top_confidence": f"{f(top, 'confidence'):.4f}" if top else "",
                "top_coverage": f"{f(top, 'coverage_ratio'):.4f}" if top else "",
                "active_count": str(active_count),
                "watch_count": str(watch_count),
                "stress_count": str(stress_count),
                "positive_drivers": " | ".join(row["signal_label"] for row in positives),
                "anti_drivers": " | ".join(row["signal_label"] for row in negatives),
            }
        )

        check_html = "".join(f"<span class='check {cls}'>{esc(name)}: {esc(label)}</span>" for name, label, cls in checks)
        if top:
            shown_state = display_state(top, status)
            headline = f"{esc(scenario_title(scenario))} · {pill(shown_state)} · lens {esc(top.get('lens', 'legacy'))} · score {fmt(top['structured_score'])}"
            detail = f"confidence {fmt(top['confidence'])} · coverage {pct(f(top, 'coverage_ratio'))} · raw state {top.get('raw_state') or top['state_label']} · ACTIVE {active_count} / WATCH {watch_count} / STRESS {stress_count}"
        else:
            headline = "No aligned scenario snapshot"
            detail = "주말/휴장/아직 전체 ticker 정렬 전 날짜입니다. 임의 보간은 하지 않았습니다."

        cards.append(
            f"""
<section class='daycard {status.lower()}'>
  <div class='dayhead'>
    <div><h2>{esc(date_str)}</h2><p class='statusline'>{esc(status)} · {esc(status_detail)}</p></div>
    <div class='sparkbox'>{sparkline(recent_scores)}</div>
  </div>
  <h3>{headline}</h3>
  <p class='explain'>{esc(top.get('market_interpretation_ko') or scenario_description(scenario)) if top else ''}</p>
  <p class='muted'>{detail}</p>
  <div class='checks'>{check_html}</div>
  <div class='twocol'>
    <div class='panel'><b class='goodtxt'>Positive drivers</b><ul>{render_driver_list(positives)}</ul></div>
    <div class='panel'><b class='warntxt'>Anti / limiting drivers</b><ul>{render_driver_list(negatives)}</ul></div>
  </div>
  {render_score_table(day_rows, status)}
</section>
"""
        )

    csv_path = reports / f"phase4_range_review_{run_id}_{start}_to_{end}.csv"
    html_path = reports / f"phase4_range_review_{run_id}_{start}_to_{end}.html"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(summary_rows[0].keys()) if summary_rows else []
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)

    html_text = f"""<!doctype html>
<html lang='ko'>
<head>
<meta charset='utf-8' />
<meta name='viewport' content='width=device-width, initial-scale=1' />
<title>Phase 4 6-Day Review · {esc(start)}~{esc(end)}</title>
<style>
:root{{--bg:#090d17;--card:#121d30;--card2:#0c1424;--line:#2b3a55;--text:#f5f8ff;--muted:#9aa7bd;--green:#00e5a8;--pink:#ff2ea6;--red:#ff4d5e;--amber:#ffbc69;--gray:#71809b;}}
*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(circle at 85% 0%,#073d32,transparent 28%),radial-gradient(circle at 0% 80%,#36102d,transparent 28%),var(--bg);color:var(--text);font-family:Inter,Pretendard,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}.wrap{{max-width:1280px;margin:0 auto;padding:34px 24px 56px}}.hero,.daycard{{border:1px solid var(--line);background:linear-gradient(180deg,rgba(18,29,48,.96),rgba(10,17,30,.96));border-radius:24px;padding:24px;box-shadow:0 22px 70px rgba(0,0,0,.28)}}h1{{font-size:34px;margin:0 0 8px;letter-spacing:-.04em}}h2{{margin:0;font-size:22px}}h3{{font-size:18px;margin:16px 0 8px}}p{{line-height:1.55}}.muted,.statusline,small{{color:var(--muted)}}.explain{{color:#d7e4f7;margin-top:4px}}.days{{display:grid;gap:18px;margin-top:18px}}.dayhead{{display:flex;align-items:center;justify-content:space-between;gap:16px}}.pill{{display:inline-flex;padding:5px 9px;border-radius:999px;font-size:12px;font-weight:800}}.stress{{color:var(--red);border:1px solid rgba(255,77,94,.45);background:rgba(255,77,94,.15)}}.active{{color:var(--green);border:1px solid rgba(0,229,168,.45);background:rgba(0,229,168,.15)}}.watch{{color:var(--pink);border:1px solid rgba(255,46,166,.45);background:rgba(255,46,166,.13)}}.off{{color:#c3cede;border:1px solid rgba(113,128,155,.45);background:rgba(113,128,155,.14)}}.strong{{color:var(--green);border:1px solid rgba(0,229,168,.55);background:rgba(0,229,168,.18)}}.provisional{{color:var(--amber);border:1px solid rgba(255,188,105,.55);background:rgba(255,188,105,.16)}}.checks{{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0}}.check{{font-size:12px;border:1px solid var(--line);border-radius:999px;padding:6px 9px;background:#0b1322}}.check.good{{color:var(--green)}}.check.warn{{color:var(--amber)}}.check.bad{{color:var(--red)}}.twocol{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:14px 0}}.panel{{background:#0b1322;border:1px solid #22314a;border-radius:16px;padding:14px}}ul{{margin:8px 0 0;padding-left:18px;color:var(--muted)}}li{{margin:6px 0}}.goodtxt{{color:var(--green)}}.warntxt{{color:var(--amber)}}table{{width:100%;border-collapse:collapse;margin-top:14px}}th,td{{text-align:left;border-bottom:1px solid rgba(255,255,255,.07);padding:9px 8px;font-size:14px}}th{{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.06em}}.bar{{height:12px;background:#26344c;border-radius:999px;overflow:hidden;min-width:170px}}.bar span{{display:block;height:100%;border-radius:999px}}.spark{{width:160px;height:30px}}.spark polyline{{fill:none;stroke:var(--green);stroke-width:2.2}}.no_data,.partial,.low_coverage{{border-color:rgba(255,188,105,.55)}}.footer{{margin-top:18px;color:var(--muted);font-size:12px}}@media(max-width:860px){{.twocol{{grid-template-columns:1fr}}.dayhead{{align-items:flex-start;flex-direction:column}}}}
</style>
</head>
<body><main class='wrap'>
<section class='hero'>
<h1>Phase 4 · 6일치 시나리오 검토</h1>
<p class='muted'>대상 기간: <b>{esc(start)} ~ {esc(end)}</b> · run_id: <b>{esc(run_id)}</b></p>
<p class='muted'>체크리스트 + 그날의 top scenario + driver/anti-driver + coverage 경고를 날짜별로 묶었습니다. 주말/아직 정렬 전 날짜는 보간하지 않고 NO_DATA 또는 PARTIAL로 표시합니다.</p>
<p class='muted'>Snapshot anchor: <b>{esc(metadata.get('anchor_date','-'))}</b> · coverage <b>{esc(metadata.get('anchor_ticker_count','-'))}/{esc(metadata.get('total_tickers','-'))}</b></p>
</section>
<section class='days'>
{''.join(cards)}
</section>
<div class='footer'>CSV summary: {esc(csv_path.relative_to(ROOT))}</div>
</main></body></html>"""
    html_path.write_text(html_text, encoding="utf-8")
    return html_path, csv_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Phase 4 date-range scenario review dashboard.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    args = parser.parse_args()
    html_path, csv_path = build(args.run_id, args.start, args.end)
    print(html_path)
    print(csv_path)


if __name__ == "__main__":
    main()
