import unittest

from scripts.event_overlay_engine import (
    build_daily_overlay_rows,
    normalize_article_events,
    validate_provider_event_payload,
    validate_article_rows,
)


class EventOverlayEngineTest(unittest.TestCase):
    def test_normalizes_dedupes_and_aggregates_events(self):
        raw_rows = [
            {
                "date": "2026-05-06",
                "source": "fixture",
                "title": "US yields stay elevated",
                "event_type": "rate",
                "region": "us",
                "direction": "rate_up",
                "severity": "70",
                "novelty": "60",
                "time_horizon": "weeks",
                "scenario_links": "higher_for_longer_long_rate_shock",
                "evidence_span": "Long-end yield pressure remains visible",
                "extract_confidence": "80",
            },
            {
                "date": "2026-05-06",
                "source": "fixture",
                "title": "US yields stay elevated",
                "event_type": "rate",
                "region": "us",
                "direction": "rate_up",
                "severity": "40",
                "novelty": "30",
                "time_horizon": "weeks",
                "scenario_links": "higher_for_longer_long_rate_shock",
                "evidence_span": "duplicate with lower signal",
                "extract_confidence": "50",
            },
            {
                "date": "2026-05-06",
                "source": "fixture",
                "title": "Won weakness returns",
                "event_type": "fx",
                "region": "korea",
                "direction": "fx_pressure",
                "severity": "64",
                "novelty": "55",
                "time_horizon": "days",
                "scenario_links": "usd_strength_krw_weakness",
                "evidence_span": "USD/KRW pressure remains separate from US risk-on",
                "extract_confidence": "82",
            },
        ]

        articles = normalize_article_events(raw_rows)
        validate_article_rows(articles)
        daily = build_daily_overlay_rows(articles)

        self.assertEqual(len(articles), 2)
        self.assertTrue(all(row["needs_review"] == "N" for row in articles))
        self.assertEqual({row["scenario_code"] for row in daily}, {"higher_for_longer_long_rate_shock", "usd_strength_krw_weakness"})
        rates = next(row for row in daily if row["scenario_code"] == "higher_for_longer_long_rate_shock")
        self.assertGreater(rates["event_overlay_score"], 70)

    def test_missing_evidence_is_queued_for_review_and_not_aggregated(self):
        raw_rows = [
            {
                "date": "2026-05-06",
                "source": "fixture",
                "title": "Oil shock worries markets",
                "event_type": "commodity",
                "region": "global",
                "direction": "inflation_up",
                "severity": "75",
                "novelty": "70",
                "scenario_links": "stagflation_reinflation_energy_shock",
                "extract_confidence": "75",
            }
        ]

        articles = normalize_article_events(raw_rows)
        validate_article_rows(articles)
        daily = build_daily_overlay_rows(articles)

        self.assertEqual(articles[0]["needs_review"], "Y")
        self.assertIn("missing_evidence_span", articles[0]["review_reason"])
        self.assertEqual(daily, [])

    def test_provider_schema_validation_records_reviewable_errors(self):
        raw_rows = [
            {
                "date": "2026-05-06",
                "source": "fixture",
                "title": "Policy headline",
                "event_type": "not-a-real-type",
                "region": "us",
                "direction": "rate_up",
                "severity": "101",
                "novelty": "55",
                "time_horizon": "weeks",
                "scenario_links": "unknown_scenario",
                "extract_confidence": "70",
            }
        ]

        errors = validate_provider_event_payload(raw_rows)

        self.assertGreaterEqual(len(errors), 3)
        self.assertTrue(all(error["severity"] == "review" for error in errors))
        self.assertIn("event_type", {error["field"] for error in errors})
        self.assertIn("scenario_links", {error["field"] for error in errors})

    def test_provider_schema_validation_can_fail_strictly(self):
        raw_rows = [{"source": "fixture", "title": "", "severity": "10"}]

        errors = validate_provider_event_payload(raw_rows, strict=True)

        self.assertTrue(any(error["severity"] == "fatal" for error in errors))
        self.assertIn("date", {error["field"] for error in errors})

    def test_v2_scenario_links_are_valid_provider_links(self):
        raw_rows = [
            {
                "date": "2026-05-11",
                "source": "fixture",
                "title": "AI semiconductor and geopolitical stress fixture",
                "event_type": "semiconductor",
                "region": "korea",
                "direction": "semiconductor_down",
                "severity": "70",
                "novelty": "60",
                "time_horizon": "days",
                "scenario_links": "semiconductor_ai_cycle_shock|korea_domestic_financial_stress|geopolitical_escalation_supply_shock",
                "evidence_span": "Reviewed fixture links all V2 scenarios.",
                "extract_confidence": "80",
            }
        ]

        errors = validate_provider_event_payload(raw_rows, strict=True)

        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
