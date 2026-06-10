#!/usr/bin/env python3
"""Generate a lightweight Phase 4 review dashboard from scenario research outputs.

No third-party dependencies. Produces a single self-contained HTML file that helps
review whether the Phase 4 explainability layer answers the key quant sanity-check
questions: top scenario, score order, drivers, anti-drivers, coverage, recent trend,
scenario overlap, and historical sanity checks.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_ID = "scenario-standalone-aligned"
STATE_ORDER = {"STRESS": 4, "ACTIVE": 3, "WATCH": 2, "OFF": 1}
STATE_LABEL_KO = {
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
VALIDATION_CASES = [
    ("2022 Global Rate Shock", "2021-11-01", "2022-10-31", "Higher-for-Longer / Long-Rate Shock"),
    ("Russia-Ukraine / Energy Shock", "2022-02-01", "2022-10-31", "Stagflation / Reinflation / Energy Shock"),
    ("China Slowdown / Property Stress", "2023-01-01", "2024-12-31", "China / Trade Fragmentation Shock"),
]


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def pct(value: float) -> str:
    return f"{value * 100:.0f}%"


def fmt(value: object, digits: int = 1) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "-"


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def f(row: dict[str, str], key: str, default: float = 0.0) -> float:
    try:
        return float(row.get(key, ""))
    except (TypeError, ValueError):
        return default


def state_class(state: str) -> str:
    return state.lower().replace("_", "-")


def state_pill(state: str) -> str:
    return f'<span class="pill {state_class(state)}">{esc(state)} · {STATE_LABEL_KO.get(state, state)}</span>'


def is_trusted(row: dict[str, str]) -> bool:
    return f(row, "coverage_ratio") >= MIN_TRUSTED_COVERAGE and f(row, "confidence") >= MIN_TRUSTED_CONFIDENCE


def display_state(row: dict[str, str]) -> str:
    """Return the user-facing interpretation label.

    Raw state labels remain in the CSV engine output. The Phase 4 review layer
    avoids overclaiming when coverage/confidence are weak and avoids calling a
    favorable Soft Landing regime "STRESS".
    """
    if row.get("display_state"):
        return row["display_state"]
    if not is_trusted(row):
        return "PROVISIONAL"
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


def bar_width(score: float) -> float:
    return max(0.0, min(score, 100.0))


def color_for_score(score: float, scenario_name: str = "", trusted: bool = True) -> str:
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
    return "#6c7a96"


def coverage_badge(cov: float) -> tuple[str, str]:
    if cov >= 0.85:
        return "OK", "good"
    if cov >= 0.60:
        return "주의", "warn"
    return "낮음", "bad"


def corr(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3:
        return None
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx == 0 or vy == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / math.sqrt(vx * vy)


def sparkline_svg(points: list[float], *, width: int = 180, height: int = 34) -> str:
    if not points:
        return ""
    if len(points) == 1:
        points = points * 2
    mn, mx = min(points), max(points)
    span = mx - mn if mx != mn else 1.0
    coords = []
    for i, value in enumerate(points):
        x = i * (width / (len(points) - 1))
        y = height - ((value - mn) / span * (height - 6) + 3)
        coords.append(f"{x:.1f},{y:.1f}")
    return f'<svg class="spark" viewBox="0 0 {width} {height}" aria-hidden="true"><polyline points="{" ".join(coords)}" /></svg>'


def summarize_validation(state_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    summaries = []
    for name, start, end, expected in VALIDATION_CASES:
        rows = [row for row in state_rows if start <= row["date"] <= end]
        dates = sorted({row["date"] for row in rows})
        top1 = 0
        top3 = 0
        expected_rows = [row for row in rows if row["scenario_name"] == expected]
        for date in dates:
            day_rows = [row for row in rows if row["date"] == date]
            ordered = sorted(day_rows, key=lambda row: -f(row, "structured_score"))
            if ordered and ordered[0]["scenario_name"] == expected:
                top1 += 1
            if any(row["scenario_name"] == expected for row in ordered[:3]):
                top3 += 1
        active = sum(1 for row in expected_rows if row["state_label"] in {"ACTIVE", "STRESS"})
        watch = sum(1 for row in expected_rows if row["state_label"] == "WATCH")
        avg_score = mean([f(row, "structured_score") for row in expected_rows]) if expected_rows else 0.0
        max_row = max(expected_rows, key=lambda row: f(row, "structured_score"), default=None)
        summaries.append(
            {
                "name": name,
                "period": f"{start} ~ {end}",
                "expected": expected,
                "dates": len(dates),
                "top1": top1,
                "top3": top3,
                "active": active,
                "watch": watch,
                "expected_rows": len(expected_rows),
                "avg_score": avg_score,
                "max_date": max_row["date"] if max_row else "-",
                "max_score": f(max_row, "structured_score") if max_row else 0.0,
                "max_state": max_row["state_label"] if max_row else "-",
            }
        )
    return summaries


def generate(run_id: str, output: Path | None = None) -> Path:
    processed = ROOT / "outputs" / "processed"
    reports = ROOT / "outputs" / "reports"
    state_path = processed / f"scenario_state_daily_{run_id}.csv"
    feature_path = processed / f"scenario_feature_daily_{run_id}.csv"
    factor_path = processed / f"market_factor_daily_{run_id}.csv"
    driver_path = reports / f"scenario_driver_table_{run_id}.csv"
    metadata_path = reports / f"scenario_snapshot_metadata_{run_id}.json"
    output_path = output or reports / f"phase4_review_dashboard_{run_id}.html"

    state_rows = load_csv(state_path)
    feature_rows = load_csv(feature_path)
    factor_rows = load_csv(factor_path) if factor_path.exists() else []
    driver_rows = load_csv(driver_path)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}

    if not state_rows:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(render_empty_dashboard(run_id, state_path, feature_path, driver_path, metadata), encoding="utf-8")
        return output_path

    latest_date = max(row["date"] for row in state_rows)
    latest_rows = [row for row in state_rows if row["date"] == latest_date]
    latest_rows.sort(key=lambda row: -f(row, "structured_score"))
    top = latest_rows[0]
    latest_factor_rows = [row for row in factor_rows if row.get("date") == latest_date]
    latest_factor_rows.sort(key=lambda row: -f(row, "factor_score"))
    latest_features = [row for row in feature_rows if row["date"] == latest_date]

    rows_by_scenario = defaultdict(list)
    for row in state_rows:
        rows_by_scenario[row["scenario_name"]].append(row)
    features_by_scenario = defaultdict(list)
    for row in latest_features:
        features_by_scenario[row["scenario_name"]].append(row)

    latest_dates = sorted({row["date"] for row in state_rows})[-90:]
    recent_rows_by_scenario = {
        scenario: [row for row in sorted(rows, key=lambda r: r["date"]) if row["date"] in latest_dates]
        for scenario, rows in rows_by_scenario.items()
    }

    low_cov = [row for row in latest_rows if f(row, "coverage_ratio") < 0.75]
    active_count = sum(1 for row in latest_rows if row["state_label"] == "ACTIVE")
    watch_count = sum(1 for row in latest_rows if row["state_label"] == "WATCH")
    stress_count = sum(1 for row in latest_rows if row["state_label"] == "STRESS")

    by_date = defaultdict(dict)
    for row in state_rows:
        by_date[row["date"]][row["scenario_name"]] = f(row, "structured_score")
    scenarios = sorted(rows_by_scenario)
    high_corr = []
    for i, left in enumerate(scenarios):
        for right in scenarios[i + 1 :]:
            xs, ys = [], []
            for mapping in by_date.values():
                if left in mapping and right in mapping:
                    xs.append(mapping[left])
                    ys.append(mapping[right])
            c = corr(xs, ys)
            if c is not None and abs(c) >= 0.60:
                high_corr.append((abs(c), c, left, right, len(xs)))
    high_corr.sort(reverse=True)

    validation = summarize_validation(state_rows)

    top_display_state = display_state(top)
    checklist = [
        ("오늘 top 시나리오가 무엇인가?", "확인 가능" if is_trusted(top) else "임시", "good" if is_trusted(top) else "warn", f"{scenario_title(top['scenario_name'])} · {top_display_state} · score {fmt(top['structured_score'])}"),
        ("7개 시나리오 점수 순서가 말이 되는가?", "검토 가능", "good", "Scoreboard에서 순위와 상태를 동시에 확인"),
        ("왜 이 시나리오가 올라왔는가?", "확인 가능", "good", "Top positive drivers 표시"),
        ("반대 근거도 보이는가?", "보강됨", "warn", "현재 대시보드에서 anti-driver를 계산해 표시"),
        ("coverage가 낮은 결과를 경고하는가?", "주의 필요", "bad" if low_cov else "good", f"낮은 coverage 시나리오 {len(low_cov)}개"),
        ("최근 흐름이 일시적 노이즈인지 보이는가?", "검토 가능", "good", "최근 90일 sparkline/heatmap 표시"),
        ("추가 지표가 어지럽지 않게 압축되는가?", "팩터화", "good" if latest_factor_rows else "warn", f"팩터 {len(latest_factor_rows)}개"),
        ("시나리오 중복이 큰가?", "주의", "warn" if high_corr else "good", f"|corr| ≥ 0.60 관계 {len(high_corr)}개"),
        ("과거 대표 구간에서 말이 되는가?", "부분 검증", "warn", "간이 historical sanity check 포함"),
    ]

    html_text = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Phase 4 Scenario Review Dashboard · {esc(run_id)}</title>
  <style>
    :root {{
      --bg:#090d17; --panel:#111b2d; --panel2:#15243a; --line:#2d3d58;
      --text:#f3f7ff; --muted:#9faabe; --green:#00e5a8; --pink:#ff2ea6;
      --red:#ff4d5e; --amber:#ffbc69; --blue:#4edcff; --gray:#6c7a96;
    }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:radial-gradient(circle at 80% 0%, #073d32 0, transparent 30%), radial-gradient(circle at 0% 80%, #36102d 0, transparent 26%), var(--bg); color:var(--text); font-family:Inter, Pretendard, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    .wrap {{ max-width:1240px; margin:0 auto; padding:32px 24px 48px; }}
    .hero {{ display:grid; grid-template-columns:1.3fr .7fr; gap:18px; align-items:stretch; }}
    .card {{ background:linear-gradient(180deg, rgba(21,36,58,.94), rgba(13,22,37,.94)); border:1px solid var(--line); border-radius:22px; box-shadow:0 20px 60px rgba(0,0,0,.28); padding:22px; }}
    h1 {{ font-size:34px; margin:0 0 10px; letter-spacing:-.04em; }}
    h2 {{ font-size:20px; margin:0 0 16px; }}
    h3 {{ font-size:15px; margin:0 0 10px; color:var(--muted); text-transform:uppercase; letter-spacing:.08em; }}
    p {{ color:var(--muted); line-height:1.6; margin:6px 0; }}
    .accent {{ color:var(--green); font-weight:800; }}
    .grid {{ display:grid; gap:18px; margin-top:18px; }}
    .grid.two {{ grid-template-columns:1fr 1fr; }}
    .grid.three {{ grid-template-columns:repeat(3, 1fr); }}
    .kpis {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-top:20px; }}
    .kpi {{ background:#0c1424; border:1px solid #23324a; border-radius:16px; padding:14px; }}
    .kpi .label {{ color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.08em; }}
    .kpi .value {{ margin-top:6px; font-size:22px; font-weight:900; }}
    .pill {{ display:inline-flex; align-items:center; gap:6px; padding:6px 10px; border-radius:999px; font-size:12px; font-weight:800; }}
    .active {{ background:rgba(0,229,168,.16); color:var(--green); border:1px solid rgba(0,229,168,.45); }}
    .watch {{ background:rgba(255,46,166,.14); color:var(--pink); border:1px solid rgba(255,46,166,.45); }}
    .stress {{ background:rgba(255,77,94,.16); color:var(--red); border:1px solid rgba(255,77,94,.45); }}
    .off {{ background:rgba(108,122,150,.16); color:#c1ccdc; border:1px solid rgba(108,122,150,.40); }}
    .strong {{ background:rgba(0,229,168,.18); color:var(--green); border:1px solid rgba(0,229,168,.55); }}
    .provisional {{ background:rgba(255,188,105,.16); color:var(--amber); border:1px solid rgba(255,188,105,.55); }}
    table {{ width:100%; border-collapse:collapse; }}
    th, td {{ text-align:left; padding:10px 8px; border-bottom:1px solid rgba(255,255,255,.07); vertical-align:top; }}
    th {{ color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.06em; }}
    td {{ font-size:14px; }}
    .scorebar {{ position:relative; height:12px; border-radius:999px; background:#26344c; overflow:hidden; min-width:160px; }}
    .scorebar > span {{ display:block; height:100%; border-radius:999px; }}
    .small {{ color:var(--muted); font-size:12px; }}
    .status.good {{ color:var(--green); }} .status.warn {{ color:var(--amber); }} .status.bad {{ color:var(--red); }}
    .question {{ display:grid; grid-template-columns:1fr auto; gap:10px; padding:13px 0; border-bottom:1px solid rgba(255,255,255,.07); }}
    .question b {{ display:block; margin-bottom:4px; }}
    .drivers {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; }}
    .driverbox {{ background:#0b1322; border:1px solid #22314a; border-radius:14px; padding:12px; }}
    .driverbox ul {{ margin:8px 0 0; padding-left:18px; color:var(--muted); }}
    .driverbox li {{ margin:6px 0; }}
    .spark {{ width:180px; height:34px; }} .spark polyline {{ fill:none; stroke:var(--green); stroke-width:2.2; }}
    .heatrow {{ display:grid; grid-template-columns:160px 1fr 72px; gap:10px; align-items:center; margin:8px 0; }}
    .heatcells {{ display:grid; grid-template-columns:repeat(30, 1fr); gap:3px; }}
    .cell {{ height:14px; border-radius:3px; background:#26344c; }}
    .note {{ border-left:3px solid var(--amber); padding-left:12px; color:var(--muted); }}
    .footer {{ margin-top:22px; color:#748198; font-size:12px; }}
    @media (max-width: 920px) {{ .hero, .grid.two, .grid.three, .drivers {{ grid-template-columns:1fr; }} .kpis {{ grid-template-columns:repeat(2,1fr); }} }}
  </style>
</head>
<body>
  <main class="wrap">
    <section class="hero">
      <div class="card">
        <h1>Phase 4 검증 대시보드</h1>
        <p><span class="accent">목적:</span> “점수가 나왔다”를 넘어서, 사람이 보고 시나리오 매핑·근거·한계를 검토할 수 있게 만드는 화면.</p>
        <div class="kpis">
          <div class="kpi"><div class="label">기준일</div><div class="value">{esc(latest_date)}</div></div>
          <div class="kpi"><div class="label">Top Scenario</div><div class="value">{esc(SCENARIO_SHORT.get(top['scenario_name'], top['scenario_name']))}</div></div>
          <div class="kpi"><div class="label">Lens</div><div class="value">{esc(top.get('lens', 'legacy'))}</div></div>
          <div class="kpi"><div class="label">Display State</div><div class="value">{state_pill(top_display_state)}</div></div>
          <div class="kpi"><div class="label">Score / Confidence</div><div class="value">{fmt(top['structured_score'])} / {fmt(top['confidence'])}</div></div>
        </div>
        <p class="note"><b>{esc(top.get('scenario_name_ko') or SCENARIO_KO.get(top['scenario_name'], ('', ''))[0])}</b> — {esc(top.get('market_interpretation_ko') or scenario_description(top['scenario_name']))}</p>
      </div>
      <div class="card">
        <h3>Snapshot Health</h3>
        <p>Anchor coverage: <b>{metadata.get('anchor_ticker_count', '-')} / {metadata.get('total_tickers', '-')}</b> ({fmt(metadata.get('anchor_ticker_coverage_ratio', 0) * 100)}%)</p>
        <p>Raw labels: ACTIVE {active_count} · WATCH {watch_count} · STRESS {stress_count}</p>
        <p class="note">coverage 낮은 시나리오는 강한 점수가 나와도 해석을 보수적으로 봐야 합니다.</p>
      </div>
    </section>

    <section class="grid two">
      <div class="card">
        <h2>질문 체크리스트 · 현재 답변 가능성</h2>
        {''.join(f'<div class="question"><div><b>{esc(q)}</b><span class="small">{esc(detail)}</span></div><div class="status {cls}">{esc(status)}</div></div>' for q, status, cls, detail in checklist)}
      </div>
      <div class="card">
        <h2>팩터 압축 요약</h2>
        <p>추가 지표는 개별 신호가 아니라 Growth, Rates, Credit, FX, Korea, Breadth 같은 팩터 점수로 압축합니다.</p>
        {render_factor_table(latest_factor_rows)}
      </div>
    </section>

    <section class="grid two">
      <div class="card">
        <h2>Scenario Scoreboard</h2>
        <table>
          <thead><tr><th>Scenario</th><th>State</th><th>Score</th><th>Coverage</th><th>Trend</th></tr></thead>
          <tbody>
            {''.join(render_score_row(row, recent_rows_by_scenario.get(row['scenario_name'], [])) for row in latest_rows)}
          </tbody>
        </table>
      </div>
      <div class="card">
        <h2>70개 자산 Breadth</h2>
        <p>시장 proxy만 보지 않고 실제 70개 자산 유니버스의 상승 확산도를 보조 확인합니다.</p>
        {render_breadth_metadata(metadata)}
      </div>
    </section>

    <section class="card grid">
      <h2>Driver / Anti-driver Review</h2>
      <p>Phase 4에서 가장 중요한 검토: “왜 떴는가”와 “왜 확신이 제한되는가”를 같이 봅니다.</p>
      {''.join(render_driver_section(row, features_by_scenario.get(row['scenario_name'], [])) for row in latest_rows)}
    </section>

    <section class="grid two">
      <div class="card">
        <h2>최근 90일 점수 흐름</h2>
        <p>최근 30개 관측치를 압축 표시합니다. 초록/분홍/빨강이 강할수록 점수가 높은 구간입니다.</p>
        {''.join(render_heat_row(scenario, rows) for scenario, rows in sorted(recent_rows_by_scenario.items()))}
      </div>
      <div class="card">
        <h2>시나리오 중복/공선성 주의</h2>
        <p>|corr| ≥ 0.60인 관계입니다. 높은 상관은 “잘못”이라기보다 해석 시 겹침을 명시해야 한다는 신호입니다.</p>
        <table>
          <thead><tr><th>Pair</th><th>Corr</th><th>N</th></tr></thead>
          <tbody>{''.join(f'<tr><td>{esc(SCENARIO_SHORT.get(a,a))} ↔ {esc(SCENARIO_SHORT.get(b,b))}</td><td>{c:+.2f}</td><td>{n}</td></tr>' for _, c, a, b, n in high_corr[:8])}</tbody>
        </table>
      </div>
    </section>

    <section class="grid two">
      <div class="card">
        <h2>Coverage Warning</h2>
        {render_coverage_warning(latest_rows)}
      </div>
      <div class="card">
        <h2>Historical Sanity Check · Mini</h2>
        <table>
          <thead><tr><th>Case</th><th>Expected</th><th>Top1/Top3</th><th>Avg</th><th>Max</th></tr></thead>
          <tbody>{''.join(render_validation_row(row) for row in validation)}</tbody>
        </table>
      </div>
    </section>

    <div class="footer">Generated from {esc(state_path.relative_to(ROOT))}, {esc(feature_path.relative_to(ROOT))}, {esc(driver_path.relative_to(ROOT))}</div>
  </main>
</body>
</html>
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_text, encoding="utf-8")
    return output_path


def render_empty_dashboard(
    run_id: str,
    state_path: Path,
    feature_path: Path,
    driver_path: Path,
    metadata: dict[str, object],
) -> str:
    missing = metadata.get("missing_tickers_total", [])
    loaded = metadata.get("loaded_tickers", [])
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Phase 4 Scenario Review Dashboard · {esc(run_id)}</title>
  <style>
    body {{ margin:0; background:#090d17; color:#f3f7ff; font-family:Inter, Pretendard, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    .wrap {{ max-width:920px; margin:0 auto; padding:40px 24px; }}
    .card {{ background:#111b2d; border:1px solid #2d3d58; border-radius:22px; padding:24px; box-shadow:0 20px 60px rgba(0,0,0,.28); }}
    h1 {{ margin:0 0 12px; letter-spacing:-.04em; }}
    p, li {{ color:#9faabe; line-height:1.65; }}
    code {{ color:#ffbc69; }}
    .bad {{ color:#ff4d5e; font-weight:800; }}
    .note {{ border-left:3px solid #ffbc69; padding-left:12px; }}
  </style>
</head>
<body>
  <main class="wrap">
    <section class="card">
      <h1>Phase 4 검증 대시보드</h1>
      <p class="bad">시나리오 state row가 없어 점수·드라이버 대시보드를 생성할 수 없습니다.</p>
      <p class="note">이 화면은 실패를 숨기지 않고 데이터 수집/정렬 문제를 먼저 보여주기 위한 fallback입니다.</p>
      <ul>
        <li>anchor date: <code>{esc(metadata.get("anchor_date", "-"))}</code></li>
        <li>anchor coverage: <code>{esc(metadata.get("anchor_ticker_count", "-"))}/{esc(metadata.get("total_tickers", "-"))}</code></li>
        <li>loaded tickers: <code>{esc(", ".join(loaded) if isinstance(loaded, list) and loaded else "-")}</code></li>
        <li>missing tickers: <code>{esc(", ".join(missing) if isinstance(missing, list) and missing else "-")}</code></li>
      </ul>
      <p>Generated from {esc(state_path.relative_to(ROOT))}, {esc(feature_path.relative_to(ROOT))}, {esc(driver_path.relative_to(ROOT))}</p>
    </section>
  </main>
</body>
</html>
"""


def render_score_row(row: dict[str, str], recent_rows: list[dict[str, str]]) -> str:
    score = f(row, "structured_score")
    cov = f(row, "coverage_ratio")
    badge, cls = coverage_badge(cov)
    shown_state = display_state(row)
    recent_scores = [f(item, "structured_score") for item in sorted(recent_rows, key=lambda r: r["date"])[-45:]]
    return f"""
<tr>
  <td><b>{esc(scenario_title(row['scenario_name']))}</b><div class="small">lens: {esc(row.get('lens', 'legacy'))} · {esc(row.get('market_interpretation_ko') or scenario_description(row['scenario_name']))}</div></td>
  <td>{state_pill(shown_state)}<div class="small">raw: {esc(row['state_label'])}</div></td>
  <td><div class="scorebar"><span style="width:{bar_width(score):.1f}%; background:{color_for_score(score, row['scenario_name'], is_trusted(row))}"></span></div><div class="small">{score:.1f}</div></td>
  <td><span class="status {cls}">{pct(cov)} · {badge}</span></td>
  <td>{sparkline_svg(recent_scores)}</td>
</tr>"""


def render_factor_table(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "<p class='status warn'>market_factor_daily 파일이 없어 팩터 요약을 표시할 수 없습니다.</p>"
    body = []
    for row in rows[:8]:
        score = f(row, "factor_score")
        polarity = "우호" if row.get("factor_polarity") == "positive" else "리스크"
        if row.get("factor_polarity") == "risk":
            cls = "bad" if score >= 65 else "warn" if score >= 45 else "good"
        else:
            cls = "good" if score >= 45 else "warn"
        body.append(
            f"<tr><td><b>{esc(row.get('factor_name', '-'))}</b><div class='small'>{esc(row.get('interpretation', ''))}</div></td>"
            f"<td><span class='status {cls}'>{esc(polarity)} · {esc(row.get('factor_state', '-'))}</span></td>"
            f"<td><div class='scorebar'><span style='width:{bar_width(score):.1f}%; background:{'#ff4d5e' if cls == 'bad' else '#00e5a8' if cls == 'good' else '#ffbc69'}'></span></div><div class='small'>{score:.1f}</div></td>"
            f"<td>{pct(f(row, 'coverage_ratio'))}</td><td>{fmt(row.get('confidence'))}</td></tr>"
        )
    return "<table><thead><tr><th>Factor</th><th>Type</th><th>Score</th><th>Coverage</th><th>Conf.</th></tr></thead><tbody>" + "".join(body) + "</tbody></table>"


def render_breadth_metadata(metadata: dict[str, object]) -> str:
    series = metadata.get("synthetic_breadth_series", [])
    if not isinstance(series, list) or not series:
        return "<p class='status warn'>70개 자산 breadth 메타데이터가 없습니다.</p>"
    rows = []
    for item in series:
        if not isinstance(item, dict):
            continue
        latest_value = item.get("latest_value")
        latest = f"{float(latest_value) * 100:.1f}%" if isinstance(latest_value, (int, float)) else "-"
        rows.append(
            f"<tr><td><b>{esc(item.get('label', item.get('ticker', '-')))}</b><div class='small'>{esc(item.get('ticker', '-'))}</div></td>"
            f"<td>{esc(item.get('source_ticker_count', '-'))}</td><td>{esc(item.get('latest_date', '-'))}</td><td>{latest}</td></tr>"
        )
    return "<table><thead><tr><th>Breadth</th><th>Source N</th><th>Latest</th><th>Value</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def render_driver_section(row: dict[str, str], feature_rows: list[dict[str, str]]) -> str:
    scenario = row["scenario_name"]
    positives = sorted([item for item in feature_rows if f(item, "contribution") > 0], key=lambda item: -f(item, "contribution"))[:3]
    negatives = sorted([item for item in feature_rows if f(item, "contribution") < 0], key=lambda item: f(item, "contribution"))[:3]

    def items(rows: list[dict[str, str]]) -> str:
        if not rows:
            return "<li>최신일 feature 없음</li>"
        return "".join(
            f"<li><b>{esc(item['signal_label'])}</b> <span class='small'>contribution {f(item, 'contribution'):+.3f}, z {f(item, 'normalized_value'):+.2f}</span></li>"
            for item in rows
        )

    return f"""
      <div class="driverbox">
        <h3>{esc(scenario_title(scenario))} · {esc(display_state(row))} · score {fmt(row['structured_score'])}</h3>
        <p>lens: <b>{esc(row.get('lens', 'legacy'))}</b> · {esc(row.get('market_interpretation_ko') or scenario_description(scenario))}</p>
        <div class="drivers">
          <div><b class="status good">Positive drivers</b><ul>{items(positives)}</ul></div>
          <div><b class="status warn">Anti / limiting drivers</b><ul>{items(negatives)}</ul></div>
        </div>
      </div>
    """


def render_heat_row(scenario: str, rows: list[dict[str, str]]) -> str:
    points = sorted(rows, key=lambda r: r["date"])[-30:]
    cells = []
    for row in points:
        score = f(row, "structured_score")
        color = color_for_score(score)
        opacity = 0.22 + min(score, 100) / 100 * 0.78
        cells.append(f'<span class="cell" title="{esc(row["date"])} score {score:.1f}" style="background:{color}; opacity:{opacity:.2f}"></span>')
    latest = f(points[-1], "structured_score") if points else 0.0
    return f"<div class='heatrow'><div>{esc(SCENARIO_SHORT.get(scenario, scenario))}</div><div class='heatcells'>{''.join(cells)}</div><div class='small'>{latest:.1f}</div></div>"


def render_coverage_warning(rows: list[dict[str, str]]) -> str:
    low_rows = [row for row in rows if f(row, "coverage_ratio") < 0.75]
    if not low_rows:
        return "<p class='status good'>모든 최신 시나리오 coverage가 75% 이상입니다.</p>"
    body = ["<p class='status bad'>coverage 75% 미만 시나리오가 있습니다. 점수보다 confidence와 누락 proxy를 먼저 확인하세요.</p><table><thead><tr><th>Scenario</th><th>Coverage</th><th>Score</th><th>State</th></tr></thead><tbody>"]
    for row in low_rows:
        body.append(
            f"<tr><td>{esc(scenario_title(row['scenario_name']))}</td><td>{pct(f(row, 'coverage_ratio'))}</td><td>{fmt(row['structured_score'])}</td><td>{state_pill(display_state(row))}<div class='small'>raw: {esc(row['state_label'])}</div></td></tr>"
        )
    body.append("</tbody></table>")
    return "".join(body)


def render_validation_row(row: dict[str, object]) -> str:
    dates = int(row["dates"] or 0)
    top1 = int(row["top1"] or 0)
    top3 = int(row["top3"] or 0)
    top1_pct = (top1 / dates * 100) if dates else 0.0
    top3_pct = (top3 / dates * 100) if dates else 0.0
    return f"""
<tr>
  <td><b>{esc(row['name'])}</b><div class="small">{esc(row['period'])}</div></td>
  <td>{esc(SCENARIO_SHORT.get(str(row['expected']), str(row['expected'])))}</td>
  <td>{top1_pct:.0f}% / {top3_pct:.0f}%<div class="small">{top1}/{dates} · {top3}/{dates}</div></td>
  <td>{float(row['avg_score']):.1f}</td>
  <td>{esc(row['max_date'])}<div class="small">{float(row['max_score']):.1f} · {esc(row['max_state'])}</div></td>
</tr>"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Phase 4 review dashboard HTML.")
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    output = generate(args.run_id, args.output)
    print(output)


if __name__ == "__main__":
    main()
