import unittest
import json
import os
import tempfile
from pathlib import Path

from scripts.event_overlay_providers import EventProviderError, GeminiEventProvider, build_event_provider, parse_gemini_event_response
from scripts.event_overlay_engine import render_event_review_markdown
from scripts.run_event_overlay_pipeline import build_overlay_metadata


class RunEventOverlayPipelineTest(unittest.TestCase):
    def test_overlay_metadata_marks_fixture_stage_and_phase6_gap(self):
        metadata = build_overlay_metadata(
            run_id="phase5-sample",
            input_path=Path("inputs/event_overlay_sample.csv"),
            article_rows=[{"needs_review": "N"}],
            daily_rows=[{"scenario_code": "higher_for_longer_long_rate_shock"}],
            article_path=Path("outputs/events/article.csv"),
            daily_path=Path("outputs/events/daily.csv"),
            review_path=Path("outputs/reports/review.md"),
            dashboard_path=Path("outputs/reports/dashboard.html"),
        )

        self.assertEqual(metadata["pipeline_phase"], "phase5_structured_overlay")
        self.assertEqual(metadata["input_mode"], "reviewed_local_fixture")
        self.assertEqual(metadata["provider"], "fixture")
        self.assertFalse(metadata["provider_requires_api_key"])
        self.assertIsNone(metadata["provider_model"])
        self.assertEqual(metadata["extraction_schema_version"], "phase5_event_extraction_schema_v1")
        self.assertFalse(metadata["live_research_attached"])
        self.assertFalse(metadata["phase6_final_merge_ready"])
        self.assertEqual(metadata["phase6_gap"], "structured_and_unstructured_not_merged")

    def test_overlay_metadata_records_schema_errors(self):
        metadata = build_overlay_metadata(
            run_id="phase5-sample",
            input_path=Path("inputs/event_overlay_sample.csv"),
            article_rows=[],
            daily_rows=[],
            article_path=Path("outputs/events/article.csv"),
            daily_path=Path("outputs/events/daily.csv"),
            review_path=Path("outputs/reports/review.md"),
            dashboard_path=Path("outputs/reports/dashboard.html"),
            schema_errors=[{"field": "scenario_links", "severity": "review"}],
        )

        self.assertEqual(metadata["schema_error_count"], 1)
        self.assertEqual(metadata["fatal_schema_error_count"], 0)
        self.assertEqual(metadata["schema_errors_sample"][0]["field"], "scenario_links")

    def test_review_markdown_calls_out_fixture_scope(self):
        markdown = render_event_review_markdown([], [], "phase5-sample")

        self.assertIn("reviewed local fixture 기반 샘플", markdown)
        self.assertIn("Phase 6 최종 병합", markdown)

    def test_fixture_provider_loads_csv_without_api_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.csv"
            path.write_text(
                "date,source,title,evidence_span,scenario_links\n"
                "2026-05-06,fixture,US yields stay elevated,Yields remain high,higher_for_longer_long_rate_shock\n",
                encoding="utf-8",
            )

            provider = build_event_provider("fixture", path)
            rows = provider.load_events()

            self.assertEqual(provider.name, "fixture")
            self.assertFalse(provider.requires_api_key)
            self.assertEqual(rows[0]["title"], "US yields stay elevated")

    def test_gemini_provider_requires_api_key(self):
        provider = build_event_provider("gemini", Path("events.csv"))

        self.assertTrue(provider.requires_api_key)
        with self.assertRaises(EventProviderError):
            provider.load_events()

    def test_gemini_provider_extracts_schema_rows_with_api_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "events.csv"
            input_path.write_text(
                "date,source,title,evidence_span\n"
                "2026-05-06,news,US yields stay elevated,Yields remain high\n",
                encoding="utf-8",
            )
            env_name = "HEDGEMATE_TEST_GEMINI_KEY"
            old_value = os.environ.get(env_name)
            os.environ[env_name] = "test-key"
            calls = []

            def fake_request(url, payload, headers, timeout_seconds):
                calls.append((url, payload, headers, timeout_seconds))
                return {
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {
                                        "text": json.dumps(
                                            {
                                                "events": [
                                                    {
                                                        "date": "2026-05-06",
                                                        "source": "news",
                                                        "title": "US yields stay elevated",
                                                        "event_type": "rate",
                                                        "region": "us",
                                                        "affected_assets": "UST|USD",
                                                        "direction": "rate_up",
                                                        "severity": 72,
                                                        "novelty": 45,
                                                        "time_horizon": "weeks",
                                                        "scenario_links": ["higher_for_longer_long_rate_shock"],
                                                        "evidence_span": "Yields remain high",
                                                        "extract_confidence": 86,
                                                    }
                                                ]
                                            }
                                        )
                                    }
                                ]
                            }
                        }
                    ]
                }

            try:
                provider = GeminiEventProvider(
                    input_path,
                    api_key_env=env_name,
                    model_name="gemini-test",
                    request_fn=fake_request,
                )
                rows = provider.load_events()
            finally:
                if old_value is None:
                    os.environ.pop(env_name, None)
                else:
                    os.environ[env_name] = old_value

            self.assertEqual(rows[0]["scenario_links"], "higher_for_longer_long_rate_shock")
            self.assertEqual(rows[0]["event_type"], "rate")
            self.assertEqual(calls[0][0], "https://generativelanguage.googleapis.com/v1beta/models/gemini-test:generateContent")
            self.assertEqual(calls[0][2]["x-goog-api-key"], "test-key")
            self.assertEqual(calls[0][1]["generationConfig"]["responseMimeType"], "application/json")

    def test_gemini_response_parser_rejects_missing_events(self):
        with self.assertRaises(EventProviderError):
            parse_gemini_event_response({"candidates": [{"content": {"parts": [{"text": "{}"}]}}]})

    def test_overlay_metadata_marks_live_gemini_provider(self):
        metadata = build_overlay_metadata(
            run_id="phase5-live",
            input_path=Path("inputs/live_events.csv"),
            article_rows=[{"needs_review": "N"}],
            daily_rows=[{"scenario_code": "higher_for_longer_long_rate_shock"}],
            article_path=Path("outputs/events/article.csv"),
            daily_path=Path("outputs/events/daily.csv"),
            review_path=Path("outputs/reports/review.md"),
            dashboard_path=Path("outputs/reports/dashboard.html"),
            provider_name="gemini",
            provider_requires_api_key=True,
            provider_api_key_env="GEMINI_API_KEY",
            provider_model="gemini-2.5-flash",
            live_research_attached=True,
        )

        self.assertEqual(metadata["input_mode"], "gemini")
        self.assertEqual(metadata["provider"], "gemini")
        self.assertTrue(metadata["provider_requires_api_key"])
        self.assertEqual(metadata["provider_model"], "gemini-2.5-flash")
        self.assertTrue(metadata["live_research_attached"])


if __name__ == "__main__":
    unittest.main()
