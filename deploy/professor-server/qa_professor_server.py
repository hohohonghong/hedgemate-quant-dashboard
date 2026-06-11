#!/usr/bin/env python3
"""QA checks for a professor-server HedgeMate deployment.

The script prints secrets-free PASS/FAIL output and exits non-zero on failed
required checks.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import ssl
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


KST = ZoneInfo("Asia/Seoul")
FORBIDDEN_TEXT = (
    "HedgeMate User",
    "user@hedgemate.io",
    "Hegdemate",
    "hegdemate",
    "실시간 시장데이터 확인중 실시간 시장데이터 확인중",
)
_HTTPS_CONTEXT = None


def https_context():
    global _HTTPS_CONTEXT
    if _HTTPS_CONTEXT is None:
        try:
            import certifi

            _HTTPS_CONTEXT = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            _HTTPS_CONTEXT = ssl.create_default_context()
    return _HTTPS_CONTEXT


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--api-base",
        default="http://127.0.0.1:8766/api",
        help="API base URL, for example https://hedgemate.eyefeet.com/api",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Deployment package root for file/artifact checks.",
    )
    parser.add_argument(
        "--allow-non-gemini-news",
        action="store_true",
        help="Downgrade Gemini news provider failures to warnings.",
    )
    parser.add_argument(
        "--wait-seconds",
        type=int,
        default=300,
        help="Wait up to this many seconds for startup refresh statuses to settle.",
    )
    return parser.parse_args(argv)


def get_json(api_base, path):
    url = f"{api_base.rstrip('/')}/{path.lstrip('/')}"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=60, context=https_context()) as response:
        return json.loads(response.read().decode("utf-8"))


def add(results, name, ok, detail="", required=True):
    results.append(
        {
            "name": name,
            "ok": bool(ok),
            "required": bool(required),
            "detail": detail,
        }
    )


def count_csv_rows(path):
    if not path or not path.exists():
        return None
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def artifact_path(root, *parts):
    return Path(root, *parts)


def run_checks(args):
    results = []
    api_base = args.api_base.rstrip("/")
    root = Path(args.root).resolve()

    try:
        health = get_json(api_base, "health")
        add(results, "api health", health.get("ok") is True, json.dumps(health, ensure_ascii=False))
    except Exception as exc:
        add(results, "api health", False, f"{type(exc).__name__}: {exc}")
        return results

    status = {}
    deadline = time.monotonic() + max(0, args.wait_seconds)
    while True:
        try:
            status = get_json(api_base, "status")
        except Exception as exc:
            add(results, "api status", False, f"{type(exc).__name__}: {exc}")
            status = {}
            break
        refreshing = any(
            status.get(key) == "REFRESHING"
            for key in ("market_data", "intraday_nowcast", "news_overlay", "selected_portfolio")
        )
        if not refreshing or time.monotonic() >= deadline:
            break
        time.sleep(5)

    add(results, "serverSafeMode=false", status.get("serverSafeMode") is False, str(status.get("serverSafeMode")))
    add(results, "scheduler running", status.get("scheduler") == "RUNNING", str(status.get("scheduler")))
    add(results, "market data fresh", status.get("market_data") == "FRESH", str(status.get("market_data")))
    add(results, "intraday nowcast fresh", status.get("intraday_nowcast") == "FRESH", str(status.get("intraday_nowcast")))
    add(results, "news overlay fresh", status.get("news_overlay") == "FRESH", str(status.get("news_overlay")))
    add(
        results,
        "productStatus accepted",
        status.get("productStatus") in {"REVIEW_ONLY", "EXECUTION_READY", "READY"},
        str(status.get("productStatus")),
    )

    try:
        assets_payload = get_json(api_base, "assets")
        assets = assets_payload.get("assets") if isinstance(assets_payload, dict) else assets_payload
        add(results, "asset universe count 150", len(assets or []) == 150, f"count={len(assets or [])}")
    except Exception as exc:
        add(results, "asset universe count 150", False, f"{type(exc).__name__}: {exc}")

    try:
        scenario = get_json(api_base, "scenario-dashboard")
    except Exception as exc:
        add(results, "scenario dashboard", False, f"{type(exc).__name__}: {exc}")
        scenario = {}

    freshness = scenario.get("marketStateFreshness") or {}
    today_kst = datetime.now(KST).date().isoformat()
    add(
        results,
        "market display date is today KST",
        freshness.get("displayDate") == today_kst,
        f"displayDate={freshness.get('displayDate')} todayKst={today_kst}",
    )
    add(
        results,
        "primary source is intraday nowcast",
        freshness.get("primarySource") == "intraday_nowcast",
        str(freshness.get("primarySource")),
    )

    news = scenario.get("intradayNewsOverlayStatus") or {}
    top5 = scenario.get("intradayNewsTop5") or []
    news_provider_ok = news.get("provider") == "gemini" and news.get("fallbackUsed") is False
    add(
        results,
        "news provider gemini",
        news_provider_ok,
        f"provider={news.get('provider')} fallback={news.get('fallbackUsed')}",
        required=not args.allow_non_gemini_news,
    )
    add(results, "news top5 count", news.get("top5Count") == 5 and len(top5) == 5, f"status={news.get('top5Count')} api={len(top5)}")
    real_urls = [str(item.get("url") or "") for item in top5 if isinstance(item, dict)]
    add(
        results,
        "news URLs are real links",
        len(real_urls) == 5 and all(url.startswith("http") and not url.startswith("fallback://") for url in real_urls),
        "; ".join(real_urls[:2]),
    )

    adjustment = scenario.get("intradayNewsScoreAdjustment") or {}
    add(results, "news adjustment applied", adjustment.get("applied") is True, json.dumps(adjustment, ensure_ascii=False))

    active_run = status.get("activeHedgemateRun")
    active_backtest = status.get("activeBacktestRun")
    if root.exists() and active_run:
        report_dir = root / "HedgeMate" / "outputs" / "reports"
        validation_dir = root / "HedgeMate" / "outputs" / "validation"
        candidate_rows = count_csv_rows(report_dir / f"hedge_action_candidates_{active_run}.csv")
        one_rows = count_csv_rows(report_dir / f"portfolio_1to1_hedge_{active_run}.csv")
        multi_rows = count_csv_rows(report_dir / f"portfolio_multi_hedge_{active_run}.csv")
        formal_rows = count_csv_rows(report_dir / f"formal_gate_audit_{active_run}_backtest_gated.csv")
        backtest_rows = count_csv_rows(validation_dir / f"walk_forward_backtest_{active_backtest}.csv") if active_backtest else None
        add(results, "candidate artifact rows", bool(candidate_rows and candidate_rows >= 60), f"rows={candidate_rows}")
        add(results, "1to1 artifact rows", bool(one_rows and one_rows > 0), f"rows={one_rows}")
        add(results, "multi artifact rows", bool(multi_rows and multi_rows > 0), f"rows={multi_rows}")
        add(results, "formal gate artifact rows", bool(formal_rows and formal_rows > 0), f"rows={formal_rows}")
        add(results, "walk-forward artifact rows", bool(backtest_rows and backtest_rows >= 100), f"rows={backtest_rows}")

    dist_dir = root / "hedge-front" / "dist"
    runtime_config = dist_dir / "hedgemate-runtime-config.js"
    if runtime_config.exists():
        add(
            results,
            "frontend same-origin runtime config",
            'window.__HEDGEMATE_API_URL__ = "";' in runtime_config.read_text(encoding="utf-8"),
            str(runtime_config),
        )
    else:
        add(results, "frontend same-origin runtime config", False, f"missing {runtime_config}")

    scan_roots = [root / "hedge-front" / "src", dist_dir]
    hits = []
    for scan_root in scan_roots:
        if not scan_root.exists():
            continue
        for path in scan_root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".js", ".jsx", ".css", ".html", ".mjs"}:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for token in FORBIDDEN_TEXT:
                if token in text:
                    hits.append(f"{path.relative_to(root)}:{token}")
    add(results, "forbidden user-facing strings absent", not hits, "; ".join(hits[:10]))

    return results


def main(argv=None):
    args = parse_args(argv)
    results = run_checks(args)
    failed_required = [row for row in results if row["required"] and not row["ok"]]
    for row in results:
        level = "PASS" if row["ok"] else "WARN" if not row["required"] else "FAIL"
        detail = f" - {row['detail']}" if row.get("detail") else ""
        print(f"{level}: {row['name']}{detail}")
    print(json.dumps({"failedRequired": len(failed_required), "checked": len(results)}, ensure_ascii=False))
    return 1 if failed_required else 0


if __name__ == "__main__":
    raise SystemExit(main())
