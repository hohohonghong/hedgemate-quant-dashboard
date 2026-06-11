import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "serve_dashboard.py"

spec = importlib.util.spec_from_file_location("serve_dashboard_persistence_tests", MODULE_PATH)
serve_dashboard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(serve_dashboard)


def portfolio_payload(name="Core"):
    return {
        "name": name,
        "purpose": "risk management",
        "totalValue": 1000000,
        "assets": [
            {"ticker": "AAPL", "qty": 5, "cost": 100, "currency": "USD"},
            {"ticker": "MSFT", "qty": 5, "cost": 100, "currency": "USD"},
        ],
    }


class ImmediateThread:
    def __init__(self, target, args=(), daemon=None):
        self.target = target
        self.args = args
        self.daemon = daemon

    def start(self):
        self.target(*self.args)


class ServerPersistenceAuthPortfolioTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "HedgeMate"
        self.root.mkdir(parents=True, exist_ok=True)
        serve_dashboard.ROOT = self.root
        serve_dashboard.INPUT_DIR = self.root / "inputs"
        serve_dashboard.OUTPUT_RAW_DIR = self.root / "outputs" / "raw"
        serve_dashboard.OUTPUT_PROCESSED_DIR = self.root / "outputs" / "processed"
        serve_dashboard.OUTPUT_REPORT_DIR = self.root / "outputs" / "reports"
        serve_dashboard.OUTPUT_VALIDATION_DIR = self.root / "outputs" / "validation"
        serve_dashboard.SCENARIO_RESEARCH_ROOT = self.root.parent / "scenario_research"
        serve_dashboard.SCENARIO_OUTPUT_DIR = serve_dashboard.SCENARIO_RESEARCH_ROOT / "outputs"
        serve_dashboard.SCENARIO_NOWCAST_DIR = serve_dashboard.SCENARIO_OUTPUT_DIR / "nowcast_vectors"
        serve_dashboard.SCENARIO_NEWS_INTRADAY_DIR = serve_dashboard.SCENARIO_OUTPUT_DIR / "news_intraday"
        serve_dashboard.RUN_JOBS.clear()
        serve_dashboard.SCHEDULER_STATE.update(
            {
                "enabled": False,
                "running": False,
                "lastStartedAt": None,
                "lastCycleAt": None,
                "lastError": None,
                "thread": None,
                "stopEvent": None,
            }
        )
        self.store = serve_dashboard.reset_persistence_for_tests(
            sqlite_path=self.root / "outputs" / "server" / "test.sqlite3"
        )

    def tearDown(self):
        self.tmp.cleanup()

    def register_user(self, email="user@example.com"):
        body, cookie = serve_dashboard.auth_register(
            {"email": email, "password": "secretpass123", "displayName": "Test User"}
        )
        return body["user"], cookie

    def test_auth_register_login_me_and_logout_use_hashed_password_and_cookie(self):
        user, cookie = self.register_user("alice@example.com")

        self.assertIn("HttpOnly", cookie)
        stored = self.store.get_user_by_email("alice@example.com")
        self.assertNotEqual(stored["password_hash"], "secretpass123")
        self.assertTrue(stored["password_hash"].startswith("pbkdf2_sha256$"))

        cookie_pair = cookie.split(";", 1)[0]
        current = serve_dashboard.current_user_from_headers({"Cookie": cookie_pair})
        self.assertEqual(current["email"], user["email"])

        login_body, login_cookie = serve_dashboard.auth_login({"email": "alice@example.com", "password": "secretpass123"})
        self.assertTrue(login_body["authenticated"])
        self.assertIn("HttpOnly", login_cookie)

        logout_body, clear_cookie = serve_dashboard.auth_logout({"Cookie": cookie_pair})
        self.assertFalse(logout_body["authenticated"])
        self.assertIn("Max-Age=0", clear_cookie)
        self.assertIsNone(serve_dashboard.current_user_from_headers({"Cookie": cookie_pair}))

    def test_session_cookie_survives_ephemeral_secret_rotation(self):
        user, cookie = self.register_user("restart@example.com")
        cookie_pair = cookie.split(";", 1)[0]
        original_secret = serve_dashboard._EPHEMERAL_SESSION_SECRET
        try:
            serve_dashboard._EPHEMERAL_SESSION_SECRET = "rotated-test-secret"
            current = serve_dashboard.current_user_from_headers({"Cookie": cookie_pair})
        finally:
            serve_dashboard._EPHEMERAL_SESSION_SECRET = original_secret

        self.assertEqual(current["email"], user["email"])

    def test_portfolio_crud_is_scoped_by_user_id(self):
        alice, _ = self.register_user("alice@example.com")
        bob, _ = self.register_user("bob@example.com")

        alice_portfolio = serve_dashboard.save_portfolio_for_user(alice["id"], portfolio_payload("Alice Core"))
        bob_portfolio = serve_dashboard.save_portfolio_for_user(bob["id"], portfolio_payload("Bob Core"))

        self.assertEqual([row["id"] for row in self.store.list_portfolios(alice["id"])], [alice_portfolio["id"]])
        self.assertEqual([row["id"] for row in self.store.list_portfolios(bob["id"])], [bob_portfolio["id"]])
        self.assertIsNone(self.store.get_portfolio(bob["id"], alice_portfolio["id"]))

        updated = serve_dashboard.save_portfolio_for_user(
            alice["id"],
            {**portfolio_payload("Alice Updated"), "status": "updated"},
            portfolio_id=alice_portfolio["id"],
        )
        self.assertEqual(updated["name"], "Alice Updated")
        self.assertFalse(self.store.delete_portfolio(bob["id"], alice_portfolio["id"]))
        self.assertTrue(self.store.delete_portfolio(alice["id"], alice_portfolio["id"]))

    def test_portfolio_update_preserves_latest_analysis_metadata(self):
        user, _ = self.register_user("analysis-meta@example.com")
        portfolio = serve_dashboard.save_portfolio_for_user(user["id"], portfolio_payload("Analysis Meta"))

        updated = serve_dashboard.save_portfolio_for_user(
            user["id"],
            {
                **portfolio_payload("Analysis Meta"),
                "status": "analyzed",
                "latestAnalysisRunId": "run-meta",
                "latestAnalysisAt": "2026-06-12T00:00:00Z",
                "latestAnalysisFingerprintHash": "fingerprint-meta",
                "latestAnalysisPortfolioKey": "AAPL:5.000000:|MSFT:5.000000:",
            },
            portfolio_id=portfolio["portfolioId"],
        )

        self.assertEqual(updated["status"], "analyzed")
        self.assertEqual(updated["latestAnalysisRunId"], "run-meta")
        self.assertEqual(updated["latestAnalysisAt"], "2026-06-12T00:00:00Z")
        self.assertEqual(updated["latestAnalysisFingerprintHash"], "fingerprint-meta")
        self.assertEqual(updated["latestAnalysisPortfolioKey"], "AAPL:5.000000:|MSFT:5.000000:")

    def test_product_dashboard_returns_needs_analysis_without_successful_run(self):
        user, _ = self.register_user("needs@example.com")
        portfolio = serve_dashboard.save_portfolio_for_user(user["id"], portfolio_payload("Needs Analysis"))

        payload = serve_dashboard.load_product_dashboard_for_saved_portfolio(
            user["id"],
            portfolio_id=portfolio["portfolioId"],
        )

        self.assertEqual(payload["status"], "NEEDS_ANALYSIS")
        self.assertEqual(payload["productStatus"], "NEEDS_ANALYSIS")
        self.assertEqual(payload["selectedPortfolio"]["portfolioId"], portfolio["portfolioId"])

    def test_product_dashboard_loads_latest_successful_run_for_selected_portfolio(self):
        user, _ = self.register_user("success@example.com")
        portfolio = serve_dashboard.save_portfolio_for_user(user["id"], portfolio_payload("Success Portfolio"))
        manifest_path = self.root / "outputs" / "analysis_cache" / "manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps({"active_bundle": {"hedgemate_run": "run-success"}}), encoding="utf-8")
        run_db_id = self.store.create_portfolio_run(
            user["id"],
            portfolio["portfolioId"],
            portfolio["portfolioHash"],
            "run-success",
            data_version="20260610",
            status="RUNNING",
        )
        self.store.update_portfolio_run(run_db_id, "SUCCESS", artifact_dir=str(manifest_path), finished=True)

        with mock.patch.object(
            serve_dashboard,
            "load_product_dashboard_data",
            return_value={"productStatus": "ACTION_READY", "dataFreshness": {}, "manifest": {}},
        ) as loader:
            payload = serve_dashboard.load_product_dashboard_for_saved_portfolio(
                user["id"],
                portfolio_id=portfolio["portfolioId"],
            )

        self.assertTrue(loader.called)
        self.assertEqual(payload["status"], "READY")
        self.assertEqual(payload["productStatus"], "READY")
        self.assertEqual(payload["rawProductStatus"], "ACTION_READY")
        self.assertEqual(payload["portfolioRun"]["runId"], "run-success")

    def test_product_dashboard_ignores_older_running_run_when_newer_success_exists(self):
        user, _ = self.register_user("running-stale@example.com")
        portfolio = serve_dashboard.save_portfolio_for_user(user["id"], portfolio_payload("Recovered Portfolio"))
        manifest_path = self.root / "outputs" / "analysis_cache" / "manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps({"active_bundle": {"hedgemate_run": "run-success"}}), encoding="utf-8")
        self.store.create_portfolio_run(
            user["id"],
            portfolio["portfolioId"],
            portfolio["portfolioHash"],
            "run-stale-running",
            data_version="20260610",
            status="RUNNING",
        )
        success_run_id = self.store.create_portfolio_run(
            user["id"],
            portfolio["portfolioId"],
            portfolio["portfolioHash"],
            "run-success",
            data_version="20260610",
            status="RUNNING",
        )
        self.store.update_portfolio_run(success_run_id, "SUCCESS", artifact_dir=str(manifest_path), finished=True)

        with mock.patch.object(
            serve_dashboard,
            "load_product_dashboard_data",
            return_value={"productStatus": "REVIEW_ONLY", "dataFreshness": {}, "manifest": {}},
        ) as loader:
            payload = serve_dashboard.load_product_dashboard_for_saved_portfolio(
                user["id"],
                portfolio_id=portfolio["portfolioId"],
            )

        self.assertTrue(loader.called)
        self.assertEqual(payload["status"], "REVIEW_ONLY")
        self.assertEqual(payload["productStatus"], "REVIEW_ONLY")
        self.assertEqual(payload["portfolioRun"]["runId"], "run-success")

    def test_scheduler_records_skipped_fresh_refresh_jobs(self):
        freshness = {
            "marketDataFresh": True,
            "scenarioFinalFresh": True,
            "marketDataStaleTickers": [],
            "marketDataFailedTickers": [],
            "intradayNowcastFresh": True,
            "intradayNowcast": {"fresh": True},
        }
        with mock.patch.object(serve_dashboard, "load_data_freshness", return_value=freshness), \
             mock.patch.object(serve_dashboard, "latest_intraday_nowcast_status", return_value={"fresh": True}), \
             mock.patch.object(serve_dashboard, "latest_intraday_news_overlay_status", return_value={"fresh": True}):
            result = serve_dashboard.run_scheduled_refresh_cycle(thread_factory=ImmediateThread)

        self.assertTrue(result["ok"])
        rows = self.store.list_refresh_jobs(limit=10)
        statuses = {(row["job_type"], row["status"]) for row in rows}
        self.assertIn((serve_dashboard.REFRESH_JOB_TYPE_MARKET_DATA, "SKIPPED_FRESH"), statuses)
        self.assertIn((serve_dashboard.REFRESH_JOB_TYPE_INTRADAY_NOWCAST, "SKIPPED_FRESH"), statuses)
        self.assertIn((serve_dashboard.REFRESH_JOB_TYPE_NEWS_OVERLAY, "SKIPPED_FRESH"), statuses)

    def test_status_reports_database_scheduler_and_selected_portfolio_state(self):
        user, _ = self.register_user("status@example.com")
        portfolio = serve_dashboard.save_portfolio_for_user(user["id"], portfolio_payload("Status Portfolio"))
        serve_dashboard.SCHEDULER_STATE.update({"enabled": True, "running": True, "lastError": None})
        freshness = {
            "freshnessStatus": "FRESH",
            "marketDataFresh": True,
            "intradayNowcastFresh": True,
            "needsRefresh": False,
            "marketDataStaleTickers": [],
            "marketDataFailedTickers": [],
        }
        with mock.patch.object(serve_dashboard, "load_data_freshness", return_value=freshness), \
             mock.patch.object(serve_dashboard, "active_bundle_integrity", return_value={"missingArtifacts": []}), \
             mock.patch.object(serve_dashboard, "latest_intraday_news_overlay_status", return_value={"fresh": True}), \
             mock.patch.object(serve_dashboard, "read_product_manifest", return_value={"active_bundle": {}, "freshness_status": "FRESH"}):
            status = serve_dashboard.load_service_status(
                selected_portfolio_id=portfolio["portfolioId"],
                user_id=user["id"],
            )

        self.assertEqual(status["database"], "CONNECTED")
        self.assertEqual(status["scheduler"], "RUNNING")
        self.assertEqual(status["market_data"], "FRESH")
        self.assertEqual(status["intraday_nowcast"], "FRESH")
        self.assertEqual(status["news_overlay"], "FRESH")
        self.assertEqual(status["selected_portfolio"], "NEEDS_ANALYSIS")

    def test_status_uses_selected_portfolio_dashboard_status(self):
        user, _ = self.register_user("review-status@example.com")
        portfolio = serve_dashboard.save_portfolio_for_user(user["id"], portfolio_payload("Review Portfolio"))
        manifest_path = self.root / "outputs" / "analysis_cache" / "review_manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps({"active_bundle": {"hedgemate_run": "run-review"}}), encoding="utf-8")
        run_db_id = self.store.create_portfolio_run(
            user["id"],
            portfolio["portfolioId"],
            portfolio["portfolioHash"],
            "run-review",
            data_version="20260610",
            status="RUNNING",
        )
        self.store.update_portfolio_run(run_db_id, "SUCCESS", artifact_dir=str(manifest_path), finished=True)
        freshness = {
            "freshnessStatus": "FRESH",
            "marketDataFresh": True,
            "intradayNowcastFresh": True,
            "needsRefresh": False,
            "marketDataStaleTickers": [],
            "marketDataFailedTickers": [],
        }

        with mock.patch.object(serve_dashboard, "load_data_freshness", return_value=freshness), \
             mock.patch.object(serve_dashboard, "active_bundle_integrity", return_value={"missingArtifacts": []}), \
             mock.patch.object(serve_dashboard, "latest_intraday_news_overlay_status", return_value={"fresh": True}), \
             mock.patch.object(serve_dashboard, "read_product_manifest", return_value={"active_bundle": {}, "freshness_status": "FRESH"}), \
             mock.patch.object(
                 serve_dashboard,
                 "load_product_dashboard_data",
                 return_value={"productStatus": "REVIEW_ONLY", "dataFreshness": {}, "manifest": {}},
             ):
            status = serve_dashboard.load_service_status(
                selected_portfolio_id=portfolio["portfolioId"],
                user_id=user["id"],
            )

        self.assertEqual(status["selected_portfolio"], "REVIEW_ONLY")
        self.assertEqual(status["productStatus"], "REVIEW_ONLY")
        self.assertEqual(status["product_mode"], "REVIEW_ONLY")

    def test_runtime_debug_payload_reports_safe_runtime_state(self):
        scenario_manifest = serve_dashboard.SCENARIO_OUTPUT_DIR / "latest_manifest.json"
        scenario_manifest.parent.mkdir(parents=True, exist_ok=True)
        scenario_manifest.write_text(
            json.dumps(
                {
                    "active_scenario_run": "scenario-run",
                    "active_final_run": "final-run",
                    "secret": "scenario-secret-value",
                }
            ),
            encoding="utf-8",
        )
        product_manifest = self.root / "outputs" / "latest_manifest.json"
        product_manifest.parent.mkdir(parents=True, exist_ok=True)
        product_manifest.write_text(
            json.dumps(
                {
                    "active_hedgemate_run": "hedge-run",
                    "active_backtest_run": "backtest-run",
                    "active_bundle": {"hedgemate_run": "hedge-run", "scenario_run": "scenario-run"},
                    "webhookSecret": "product-secret-value",
                }
            ),
            encoding="utf-8",
        )

        payload = serve_dashboard.runtime_debug_payload()
        serialized = json.dumps(payload)

        self.assertEqual(payload["paths"]["ROOT"], str(self.root))
        self.assertTrue(payload["manifests"]["HEDGEMATE_MANIFEST_PATH"]["exists"])
        self.assertTrue(payload["manifests"]["SCENARIO_MANIFEST_PATH"]["exists"])
        self.assertTrue(payload["writable"]["hedgemateOutputs"]["writable"])
        self.assertTrue(payload["writable"]["hedgemateRunInputs"]["writable"])
        self.assertEqual(payload["runs"]["hedgemateManifest"]["activeHedgemateRun"], "hedge-run")
        self.assertEqual(payload["runs"]["scenarioManifest"]["activeFinalRun"], "final-run")
        self.assertEqual(payload["database"]["status"], "CONNECTED")
        self.assertIn(payload["scheduler"]["status"], {"STOPPED", "RUNNING", "DEGRADED"})
        self.assertNotIn("env", payload)
        self.assertNotIn("product-secret-value", serialized)
        self.assertNotIn("scenario-secret-value", serialized)


if __name__ == "__main__":
    unittest.main()
