import json
import tempfile
import unittest
from pathlib import Path

from scripts import manifest_sync, run_final_market_state_pipeline, run_market_state_pipeline


class ScenarioManifestSyncTests(unittest.TestCase):
    def test_sync_active_hedgemate_from_product_manifest_replaces_legacy_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            product_manifest = Path(tmp) / "HedgeMate" / "outputs" / "latest_manifest.json"
            product_manifest.parent.mkdir(parents=True)
            product_manifest.write_text(
                json.dumps(
                    {
                        "active_hedgemate_run": "hedgemate-prod",
                        "active_bundle": {"hedgemate_run": "hedgemate-prod"},
                        "artifacts": {
                            "assetScenarioSensitivity": "HedgeMate/outputs/processed/asset_scenario_sensitivity_hedgemate-prod.csv",
                            "scenarioVector": "scenario_research/outputs/scenario_vectors/current_scenario_vector_prod.csv",
                            "recommendationStatusQa": "HedgeMate/outputs/reports/recommendation_status_qa_post_backtest_hedgemate-prod_backtest_gated.md",
                        },
                    }
                ),
                encoding="utf-8",
            )

            updated = manifest_sync.sync_active_hedgemate_from_product_manifest(
                {"active_hedgemate_run": "20260310T000000000000-deadbeef"},
                product_manifest,
            )

            self.assertEqual(updated["active_hedgemate_run"], "hedgemate-prod")
            self.assertEqual(updated["legacy_hedgemate_run"], "20260310T000000000000-deadbeef")
            self.assertEqual(updated["active_hedgemate_manifest_basis"], "HedgeMate/outputs/latest_manifest.json")
            self.assertEqual(updated["active_hedgemate_product_manifest_path"], "../HedgeMate/outputs/latest_manifest.json")
            self.assertIn("post_backtest", updated["active_hedgemate_recommendation_status_qa_path"])

    def test_scenario_pipeline_manifest_update_preserves_product_active_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scenario_manifest = root / "scenario_research" / "outputs" / "latest_manifest.json"
            product_manifest = root / "HedgeMate" / "outputs" / "latest_manifest.json"
            scenario_manifest.parent.mkdir(parents=True)
            product_manifest.parent.mkdir(parents=True)
            scenario_manifest.write_text(
                json.dumps({"active_hedgemate_run": "20260310T000000000000-deadbeef"}),
                encoding="utf-8",
            )
            product_manifest.write_text(
                json.dumps(
                    {
                        "active_hedgemate_run": "hedgemate-prod",
                        "active_bundle": {"hedgemate_run": "hedgemate-prod"},
                        "artifacts": {
                            "assetScenarioSensitivity": "HedgeMate/outputs/processed/asset_scenario_sensitivity_hedgemate-prod.csv",
                            "recommendationStatusQa": "HedgeMate/outputs/reports/recommendation_status_qa_post_backtest_hedgemate-prod_backtest_gated.md",
                        },
                    }
                ),
                encoding="utf-8",
            )

            original_product_manifest = manifest_sync.HEDGEMATE_MANIFEST_PATH
            original_market_manifest = run_market_state_pipeline.OUTPUT_MANIFEST_JSON
            original_final_manifest = run_final_market_state_pipeline.OUTPUT_MANIFEST_JSON
            try:
                manifest_sync.HEDGEMATE_MANIFEST_PATH = product_manifest
                run_market_state_pipeline.OUTPUT_MANIFEST_JSON = scenario_manifest
                run_final_market_state_pipeline.OUTPUT_MANIFEST_JSON = scenario_manifest

                run_market_state_pipeline.update_latest_manifest({"active_scenario_run": "scenario-prod"})
                run_final_market_state_pipeline.update_latest_manifest({"active_final_run": "final-prod"})
            finally:
                manifest_sync.HEDGEMATE_MANIFEST_PATH = original_product_manifest
                run_market_state_pipeline.OUTPUT_MANIFEST_JSON = original_market_manifest
                run_final_market_state_pipeline.OUTPUT_MANIFEST_JSON = original_final_manifest

            payload = json.loads(scenario_manifest.read_text(encoding="utf-8"))
            self.assertEqual(payload["active_scenario_run"], "scenario-prod")
            self.assertEqual(payload["active_final_run"], "final-prod")
            self.assertEqual(payload["active_hedgemate_run"], "hedgemate-prod")
            self.assertEqual(payload["legacy_hedgemate_run"], "20260310T000000000000-deadbeef")
            self.assertEqual(payload["active_hedgemate_manifest_basis"], "HedgeMate/outputs/latest_manifest.json")


if __name__ == "__main__":
    unittest.main()
