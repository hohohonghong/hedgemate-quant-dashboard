#!/usr/bin/env python3
"""Integrated smoke checks for the local HedgeMate dashboard."""

from __future__ import annotations

import argparse
import json
import threading
import urllib.error
import urllib.request
from http import HTTPStatus
from pathlib import Path

import serve_dashboard


ISSUE_CLASSES = ("BUG", "SAFETY_GATE_EXPECTED", "RESEARCH_GAP", "UX_GAP", "OPS_GAP")


def issue(issue_class, code, message, severity="P2", next_action=""):
    return {
        "class": issue_class,
        "code": code,
        "severity": severity,
        "message": message,
        "nextAction": next_action,
    }


def safe_int(value, default=0):
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return default


def request_json(base_url, path, payload=None, timeout=10):
    data = None
    headers = {}
    method = "GET"
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
        method = "POST"
    request = urllib.request.Request(f"{base_url}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        return response.status, json.loads(body or "{}")


def start_local_server():
    server = serve_dashboard.ThreadingHTTPServer(("127.0.0.1", 0), serve_dashboard.DashboardHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, f"http://127.0.0.1:{server.server_address[1]}"


def stop_local_server(server, thread):
    if not server:
        return
    server.shutdown()
    thread.join(timeout=5)
    server.server_close()


def artifact_issues(manifest):
    issues = []
    for row in serve_dashboard.active_bundle_missing_artifacts(manifest):
        issues.append(
            issue(
                "BUG",
                "required_active_artifact_missing",
                f"Required active artifact is missing: {row.get('key')}={row.get('path')}",
                severity="P0",
                next_action="Regenerate the active bundle and do not mark /api/run completed until required artifacts exist.",
            )
        )
    for row in serve_dashboard.manifest_artifact_status(manifest):
        if not row.get("exists"):
            issues.append(
                issue(
                    "OPS_GAP",
                    "manifest_artifact_missing",
                    f"Manifest artifact is missing: {row.get('key')}={row.get('path')}",
                    severity="P1",
                    next_action="Regenerate or repair HedgeMate/outputs/latest_manifest.json.",
                )
            )
    artifacts = manifest.get("artifacts", {}) if isinstance(manifest, dict) else {}
    bundle = manifest.get("active_bundle", {}) if isinstance(manifest.get("active_bundle"), dict) else {}
    bundle_fingerprint = bundle.get("portfolio_input_fingerprint") if isinstance(bundle, dict) else {}
    manifest_fingerprint = manifest.get("portfolio_input_fingerprint") if isinstance(manifest, dict) else {}
    if not bundle_fingerprint or not bundle_fingerprint.get("hash"):
        issues.append(
            issue(
                "BUG",
                "active_bundle_portfolio_fingerprint_missing",
                "Active bundle portfolio_input_fingerprint.hash is missing.",
                severity="P0",
                next_action="Persist and promote only the active run's portfolio input fingerprint.",
            )
        )
    if manifest_fingerprint and bundle_fingerprint and manifest_fingerprint.get("hash") != bundle_fingerprint.get("hash"):
        issues.append(
            issue(
                "BUG",
                "manifest_active_bundle_fingerprint_mismatch",
                "Top-level manifest portfolio fingerprint differs from active_bundle fingerprint.",
                severity="P0",
                next_action="Rebuild latest_manifest.json so top-level and active_bundle portfolio fingerprints match.",
            )
        )
    if manifest.get("active_hedgemate_run") != bundle.get("hedgemate_run"):
        issues.append(
            issue(
                "BUG",
                "manifest_active_bundle_run_mismatch",
                "Top-level active_hedgemate_run differs from active_bundle.hedgemate_run.",
                severity="P0",
                next_action="Do not expose the product dashboard until the active run ids match.",
            )
        )
    portfolio_path = serve_dashboard.resolve_any_artifact(artifacts.get("portfolioInput"))
    expected_sha = bundle.get("portfolioInputSha256")
    if not expected_sha:
        issues.append(
            issue(
                "BUG",
                "active_bundle_portfolio_input_sha_missing",
                "Active bundle portfolioInputSha256 is missing.",
                severity="P0",
                next_action="Store the promoted run input SHA in active_bundle.portfolioInputSha256.",
            )
        )
    if expected_sha and portfolio_path:
        actual_sha = serve_dashboard.file_sha256(portfolio_path)
        if actual_sha != expected_sha:
            issues.append(
                issue(
                    "OPS_GAP",
                    "portfolio_input_hash_mismatch",
                    "Manifest portfolioInputSha256 does not match the persisted portfolio input.",
                    severity="P0",
                    next_action="Rebuild the active bundle from the persisted run input.",
                )
            )
    return issues


def product_decision_issues(product):
    issues = []
    recommendation = product.get("recommendationDecision") or {}
    action = product.get("actionPlanDecision") or {}
    event_status = product.get("eventOverlayStatus") or {}
    product_status = product.get("productStatus")
    integrity = product.get("activeBundleIntegrity") or {}
    freshness_status = str(product.get("freshnessStatus") or (product.get("dataFreshness") or {}).get("freshnessStatus") or "").upper()
    action_rows = product.get("hedgeActionPlan") or []
    formal_recommendations = safe_int(recommendation.get("formalRecommendationCount"))
    formal_actions = safe_int(action.get("formalActionCount"))
    formal_type_counts = action.get("formalActionTypeCounts") or {}
    formal_rebalance_hedge_count = safe_int(action.get("formalRebalanceHedgeCount") or formal_type_counts.get("FORMAL_REBALANCE_HEDGE"))
    formal_de_risk_cash_count = safe_int(action.get("formalDeRiskCashCount") or formal_type_counts.get("FORMAL_DE_RISK_CASH"))
    formal_hold_count = safe_int(action.get("formalHoldCount") or formal_type_counts.get("FORMAL_HOLD"))
    blocker_summary = product.get("formalGateBlockerSummary") or {}

    if recommendation.get("canExecuteRecommendations") and formal_recommendations <= 0:
        issues.append(
            issue(
                "BUG",
                "zero_formal_recommendations_executable",
                "canExecuteRecommendations=true while formalRecommendationCount is zero.",
                severity="P0",
                next_action="Keep canExecuteRecommendations=false until PASS_RECOMMEND rows exist.",
            )
        )
    if action.get("canExecuteAction") and formal_actions <= 0:
        issues.append(
            issue(
                "BUG",
                "zero_formal_actions_executable",
                "canExecuteAction=true while formalActionCount is zero.",
                severity="P0",
                next_action="Keep canExecuteAction=false until selected FORMAL_ACTION rows exist.",
            )
        )
    if action.get("canExecuteAction") and product_status != "ACTION_READY":
        issues.append(
            issue(
                "BUG",
                "action_executable_without_action_ready_status",
                f"canExecuteAction=true while productStatus={product_status!r}.",
                severity="P0",
                next_action="Disable canExecuteAction unless productStatus is ACTION_READY.",
            )
        )
    if action.get("canExecuteAction") and freshness_status == "STALE":
        issues.append(
            issue(
                "BUG",
                "stale_data_action_executable",
                "canExecuteAction=true while freshnessStatus is STALE.",
                severity="P0",
                next_action="Keep action execution blocked until data freshness is current.",
            )
        )
    if product_status == "ACTION_READY" and not integrity.get("ok"):
        issues.append(
            issue(
                "BUG",
                "action_ready_without_active_bundle_integrity",
                "productStatus=ACTION_READY while activeBundleIntegrity.ok is false.",
                severity="P0",
                next_action="Require active run, portfolio fingerprint/SHA, ticker list, and required artifacts before ACTION_READY.",
            )
        )
    if action.get("canExecuteFormalAction") and formal_rebalance_hedge_count + formal_de_risk_cash_count <= 0:
        issues.append(
            issue(
                "BUG",
                "zero_formal_action_type_executable",
                "canExecuteFormalAction=true without FORMAL_REBALANCE_HEDGE or FORMAL_DE_RISK_CASH.",
                severity="P0",
                next_action="Base execution on action-level formal_action_type, not linked recommendation status.",
            )
        )
    if formal_actions > 0 and formal_rebalance_hedge_count + formal_de_risk_cash_count + formal_hold_count <= 0:
        issues.append(
            issue(
                "BUG",
                "linked_pass_recommend_misread_as_action",
                "Selected FORMAL_ACTION rows lack an action-level formal_action_type.",
                severity="P0",
                next_action="Do not treat linked PASS_RECOMMEND evidence as the final action formal gate.",
            )
        )

    selected_formal_rows = [
        row
        for row in action_rows
        if str(row.get("formal_action_type") or row.get("formalActionType") or "").upper()
        in {"FORMAL_REBALANCE_HEDGE", "FORMAL_DE_RISK_CASH"}
    ]
    for row in selected_formal_rows:
        count = safe_int(row.get("alternatives_compared_count") or row.get("alternativesComparedCount"))
        if count < 4:
            issues.append(
                issue(
                    "BUG",
                    "formal_action_missing_alternative_comparison",
                    f"Formal action {row.get('action_id') or row.get('actionId') or '-'} has fewer than four alternatives compared.",
                    severity="P0",
                    next_action="Compare current, rebalance hedge, trim-to-cash, and hold before formal promotion.",
                )
            )
            break
    if formal_de_risk_cash_count > 0:
        cash_rows = [
            row
            for row in action_rows
            if str(row.get("formal_action_type") or row.get("formalActionType") or "").upper() == "FORMAL_DE_RISK_CASH"
        ]
        if not any("CASH" in str(row.get("cash_baseline_verdict") or "").upper() for row in cash_rows):
            issues.append(
                issue(
                    "BUG",
                    "cash_action_missing_cash_baseline_evidence",
                    "FORMAL_DE_RISK_CASH is present without cash-baseline evidence.",
                    severity="P0",
                    next_action="Recommend cash only when the trim-to-cash baseline beats hedge alternatives after cost.",
                )
            )
    if formal_hold_count > 0:
        issues.append(
            issue(
                "SAFETY_GATE_EXPECTED",
                "formal_hold_fallback_used",
                "FORMAL_HOLD is present; this must be a last fallback after all cost-adjusted action alternatives fail.",
                severity="P2",
                next_action="Confirm no rebalance hedge or cash action beats hold after costs, liquidity, and turnover gates.",
            )
        )

    trade_usage = str(event_status.get("trade_gate_usage") or event_status.get("recommendation_usage") or "").lower()
    event_mode = str(event_status.get("mode") or "").lower()
    event_is_review_only = (
        "fixture" in event_mode
        or event_mode in {"seed", "manual"}
        or "fixture" in trade_usage
        or "disabled" in trade_usage
    )
    if event_is_review_only and recommendation.get("canExecuteRecommendations"):
        issues.append(
            issue(
                "BUG",
                "fixture_event_overlay_promoted",
                "Review-only or fixture event overlay is still executable.",
                severity="P0",
                next_action="Require live trusted event metadata before formal recommendation execution.",
            )
        )

    if not recommendation.get("canExecuteRecommendations") and formal_recommendations <= 0:
        if not (recommendation.get("primaryReasons") or blocker_summary.get("items")):
            issues.append(
                issue(
                    "UX_GAP",
                    "missing_no_formal_explanation",
                    "No-formal-recommendation state lacks user-facing reasons or blocker summary.",
                    severity="P1",
                    next_action="Expose primaryReasons and formalGateBlockerSummary in /api/product-dashboard.",
                )
            )
        else:
            issues.append(
                issue(
                    "SAFETY_GATE_EXPECTED",
                    "no_formal_recommendation",
                    "Formal recommendations are blocked by visible safety gates.",
                    severity="P2",
                    next_action="Resolve blocker next actions before expecting formal recommendations.",
                )
            )
    unknown_blockers = blocker_summary.get("unknownBlockers") or []
    if unknown_blockers:
        issues.append(
            issue(
                "BUG",
                "unknown_formal_gate_blocker",
                f"Unknown formal gate blocker codes are present: {', '.join(map(str, unknown_blockers))}",
                severity="P1",
                next_action="Add blocker detail mappings before relying on the formal gate audit.",
            )
        )
    return issues


def scenario_sensitivity_issues(payload):
    issues = []
    rows = payload.get("rows") or []
    if payload.get("rowCount") != len(rows):
        issues.append(
            issue(
                "BUG",
                "scenario_sensitivity_row_count_mismatch",
                "Scenario sensitivity API rowCount does not equal rows.length.",
                severity="P1",
                next_action="Return rowCount from the backend parsed rows.",
            )
        )
    for key in ("sourceQualityCounts", "gateEligibleCounts", "eventOrSeedDependentCounts"):
        if not isinstance(payload.get(key), dict):
            issues.append(
                issue(
                    "BUG",
                    f"scenario_sensitivity_missing_{key}",
                    f"Scenario sensitivity API is missing {key}.",
                    severity="P1",
                    next_action="Return source, gate, and event/seed counts from the backend.",
                )
            )
    if payload.get("artifactPath") and payload.get("rowCount", 0) <= 0:
        issues.append(
            issue(
                "OPS_GAP",
                "scenario_sensitivity_empty_artifact",
                "Scenario sensitivity artifact is present but parsed zero rows.",
                severity="P1",
                next_action="Regenerate asset_scenario_sensitivity for the active HedgeMate run.",
            )
        )
    return issues


def run_checks(base_url):
    failed_checks = []
    issues = []
    payloads = {}

    for name, method, path, body in [
        ("health", "GET", "/api/health", None),
        ("dataFreshness", "GET", "/api/data-freshness", None),
        ("productDashboard", "GET", "/api/product-dashboard", None),
        ("assets", "GET", "/api/assets", None),
        ("portfolioPreview", "POST", "/api/portfolio/preview", {"portfolioRows": [{"asset": "AAPL", "amountKrw": 1000000}]}),
        ("scenarioSensitivities", "GET", "/api/scenario-sensitivities", None),
    ]:
        try:
            status, payload = request_json(base_url, path, payload=body)
            payloads[name] = payload
            if status >= HTTPStatus.BAD_REQUEST:
                failed_checks.append({"check": name, "status": status})
        except urllib.error.HTTPError as exc:
            failed_checks.append({"check": name, "status": exc.code, "error": exc.read().decode("utf-8", errors="replace")})
        except Exception as exc:
            failed_checks.append({"check": name, "error": str(exc)})

    product = payloads.get("productDashboard") or {}
    manifest = product.get("manifest") or serve_dashboard.read_product_manifest()
    if manifest:
        issues.extend(artifact_issues(manifest))
    else:
        issues.append(issue("OPS_GAP", "manifest_missing", "No active product manifest is available.", severity="P1"))
    if product:
        issues.extend(product_decision_issues(product))
    if payloads.get("scenarioSensitivities") is not None:
        issues.extend(scenario_sensitivity_issues(payloads["scenarioSensitivities"]))

    for failed in failed_checks:
        issues.append(
            issue(
                "BUG",
                f"smoke_{failed['check']}_failed",
                f"Smoke endpoint failed: {failed}",
                severity="P1",
                next_action="Fix the endpoint or test fixture before declaring the dashboard ready.",
            )
        )

    remaining = {name: [] for name in ISSUE_CLASSES}
    for item in issues:
        remaining.setdefault(item["class"], []).append(item)

    blocking = [
        item
        for item in issues
        if item["class"] in {"BUG", "UX_GAP", "OPS_GAP"} or item.get("severity") in {"P0", "P1"}
    ]
    recommendation = (product.get("recommendationDecision") or {}) if product else {}
    action = (product.get("actionPlanDecision") or {}) if product else {}
    action_rows = (product.get("hedgeActionPlan") or []) if product else []
    event_status = (product.get("eventOverlayStatus") or {}) if product else {}
    freshness = (product.get("dataFreshness") or {}) if product else {}
    blocker_summary = (product.get("formalGateBlockerSummary") or {}) if product else {}
    artifact_rows = serve_dashboard.manifest_artifact_status(manifest) if manifest else []
    missing_artifacts = [row for row in artifact_rows if not row.get("exists")]
    formal_action_type_counts = action.get("formalActionTypeCounts") or {}
    alternatives_compared_count = sum(
        1
        for row in action_rows
        if safe_int(row.get("alternatives_compared_count") or row.get("alternativesComparedCount")) >= 4
    )

    return {
        "overallStatus": "FAIL" if blocking else "PASS",
        "failedChecks": failed_checks,
        "remainingIssuesByClass": remaining,
        "nextActions": [item["nextAction"] for item in blocking if item.get("nextAction")],
        "summary": {
            "formalRecommendations": recommendation.get("formalRecommendationCount"),
            "formalActionTypeCounts": formal_action_type_counts,
            "formalRebalanceHedgeCount": action.get("formalRebalanceHedgeCount"),
            "formalDeRiskCashCount": action.get("formalDeRiskCashCount"),
            "formalHoldCount": action.get("formalHoldCount"),
            "reviewRequiredCount": action.get("reviewRequiredCount"),
            "reviewOnlyActions": action.get("reviewActionCount"),
            "alternativesComparedCount": alternatives_compared_count,
            "holdFallbackUsed": bool(action.get("formalHoldCount")),
            "eventOverlay": event_status.get("mode"),
            "activeManifest": freshness.get("freshnessStatus") or product.get("freshnessStatus") if product else None,
            "canExecuteRecommendations": recommendation.get("canExecuteRecommendations"),
            "canExecuteAction": action.get("canExecuteAction"),
            "canExecuteFormalAction": action.get("canExecuteFormalAction"),
            "manifestArtifactCount": len(artifact_rows),
            "missingManifestArtifactCount": len(missing_artifacts),
            "scenarioSensitivityRows": (payloads.get("scenarioSensitivities") or {}).get("rowCount"),
            "formalGateBlockerTop": [
                {
                    "code": item.get("code"),
                    "count": item.get("count"),
                    "nextAction": item.get("nextAction"),
                }
                for item in (blocker_summary.get("items") or [])[:10]
            ],
        },
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Smoke test the HedgeMate integrated dashboard.")
    parser.add_argument("--base-url", help="Existing dashboard base URL. If omitted, an in-process local server is started.")
    parser.add_argument("--output", type=Path, help="Optional path to write the JSON smoke summary.")
    return parser.parse_args()


def main():
    args = parse_args()
    server = None
    thread = None
    base_url = args.base_url
    if not base_url:
        server, thread, base_url = start_local_server()
    try:
        summary = run_checks(base_url.rstrip("/"))
    finally:
        stop_local_server(server, thread)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    raise SystemExit(0 if summary["overallStatus"] == "PASS" else 1)


if __name__ == "__main__":
    main()
