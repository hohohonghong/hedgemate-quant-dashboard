"""Helpers for keeping scenario and HedgeMate active manifests consistent."""

from __future__ import annotations

import json
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
HEDGEMATE_MANIFEST_PATH = WORKSPACE_ROOT / "HedgeMate" / "outputs" / "latest_manifest.json"


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _scenario_manifest_path(raw_path: object) -> str | None:
    if not raw_path:
        return None
    text = str(raw_path).replace("\\", "/")
    if text.startswith("../") or Path(text).is_absolute():
        return text
    return "../" + text


def _artifact_name(raw_path: object) -> str | None:
    if not raw_path:
        return None
    return Path(str(raw_path).replace("\\", "/")).name


def sync_active_hedgemate_from_product_manifest(
    scenario_manifest: dict,
    product_manifest_path: Path | None = None,
) -> dict:
    """Overlay HedgeMate product-bundle fields onto a scenario latest manifest.

    Scenario-only refreshes update market-state fields, but the user-facing
    dashboard contract still needs to point at the gated HedgeMate active bundle.
    This keeps stale legacy runs from reappearing in scenario_research's manifest.
    """

    product_manifest = _read_json(product_manifest_path or HEDGEMATE_MANIFEST_PATH)
    active_bundle = product_manifest.get("active_bundle", {}) if isinstance(product_manifest, dict) else {}
    if not isinstance(active_bundle, dict):
        active_bundle = {}

    hedge_run = product_manifest.get("active_hedgemate_run") or active_bundle.get("hedgemate_run")
    if not hedge_run:
        return scenario_manifest

    updated = dict(scenario_manifest)
    previous_run = updated.get("active_hedgemate_run")
    if previous_run and previous_run != hedge_run:
        updated["legacy_hedgemate_run"] = previous_run
        updated["legacy_hedgemate_note"] = (
            "Superseded by HedgeMate/outputs/latest_manifest.json active bundle; "
            "do not use this legacy run as product recommendation evidence."
        )

    artifacts = product_manifest.get("artifacts", {})
    if not isinstance(artifacts, dict):
        artifacts = {}

    sensitivity_path = artifacts.get("assetScenarioSensitivity") or f"HedgeMate/outputs/processed/asset_scenario_sensitivity_{hedge_run}.csv"
    summary_path = f"HedgeMate/outputs/reports/asset_scenario_sensitivity_summary_{hedge_run}.md"
    qa_path = artifacts.get("recommendationStatusQa")

    updated.update(
        {
            "active_hedgemate_run": hedge_run,
            "active_hedgemate_summary": _artifact_name(summary_path),
            "active_hedgemate_summary_path": _scenario_manifest_path(summary_path),
            "active_hedgemate_sensitivity": _artifact_name(sensitivity_path),
            "active_hedgemate_sensitivity_path": _scenario_manifest_path(sensitivity_path),
            "active_hedgemate_scenario_vector": artifacts.get("scenarioVector"),
            "active_hedgemate_recommendation_status_qa": _artifact_name(qa_path),
            "active_hedgemate_recommendation_status_qa_path": _scenario_manifest_path(qa_path),
            "active_hedgemate_product_manifest_path": "../HedgeMate/outputs/latest_manifest.json",
            "active_hedgemate_manifest_basis": "HedgeMate/outputs/latest_manifest.json",
        }
    )
    return updated
