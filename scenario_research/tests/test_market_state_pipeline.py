import unittest

from scripts.market_state_engine import (
    ENGINE_VERSION,
    GEOPOLITICAL_EVENT_OVERLAY,
    SCENARIO_STATE_FIELDS,
    SCENARIO_VECTOR_FIELDS,
    build_current_scenario_vector_rows,
    build_market_state_phase1_to4,
    build_scenario_registry_rows,
    scenario_display_state,
)
from scripts.run_market_state_pipeline import (
    apply_anchor_forward_fills,
    build_low_frequency_indicator_series,
    build_synthetic_basket_series,
)


class MarketStatePipelineTest(unittest.TestCase):
    def test_forward_fills_fx_anchor_gap_when_next_observation_exists(self):
        series_map = {
            "KRW=X": [
                ("2026-05-05", 1473.959961, "hedgemate_fx_raw"),
                ("2026-05-07", 1449.079956, "hedgemate_fx_raw"),
            ]
        }

        filled_map, fill_rows = apply_anchor_forward_fills(series_map, "2026-05-06")

        self.assertEqual(
            filled_map["KRW=X"],
            [
                ("2026-05-05", 1473.959961, "hedgemate_fx_raw"),
                ("2026-05-06", 1473.959961, "anchor_forward_fill"),
                ("2026-05-07", 1449.079956, "hedgemate_fx_raw"),
            ],
        )
        self.assertEqual(len(fill_rows), 1)
        self.assertEqual(fill_rows[0]["ticker"], "KRW=X")
        self.assertEqual(fill_rows[0]["filled_date"], "2026-05-06")
        self.assertEqual(fill_rows[0]["source_date"], "2026-05-05")

    def test_does_not_fill_when_future_observation_is_missing(self):
        series_map = {
            "KRW=X": [
                ("2026-05-05", 1473.959961, "hedgemate_fx_raw"),
            ]
        }

        filled_map, fill_rows = apply_anchor_forward_fills(series_map, "2026-05-06")

        self.assertEqual(filled_map["KRW=X"], series_map["KRW=X"])
        self.assertEqual(fill_rows, [])

    def test_scenario_registry_contains_v2_scenarios(self):
        rows = build_scenario_registry_rows()
        codes = {row["scenario_code"] for row in rows}

        self.assertEqual(len(codes), 10)
        self.assertIn("semiconductor_ai_cycle_shock", codes)
        self.assertIn("korea_domestic_financial_stress", codes)
        self.assertIn("geopolitical_escalation_supply_shock", codes)

    def test_current_scenario_vector_uses_v2_schema_and_latest_full_date(self):
        registry_rows = build_scenario_registry_rows()
        partial_old_rows = [
            {
                "date": "2026-05-10",
                "scenario_code": registry_rows[0]["scenario_code"],
                "scenario_name": registry_rows[0]["scenario_name"],
                "structured_score": 55.0,
                "coverage_ratio": 0.9,
                "confidence": 65.0,
                "raw_state": "WATCH",
                "state_label": "WATCH",
                "display_state": "WATCH",
            }
        ]
        full_latest_rows = []
        for idx, registry_row in enumerate(registry_rows):
            raw_state = "OFF" if idx % 3 == 0 else "WATCH"
            full_latest_rows.append(
                {
                    "date": "2026-05-11",
                    "scenario_code": registry_row["scenario_code"],
                    "scenario_name": registry_row["scenario_name"],
                    "structured_score": 25.0 + idx,
                    "coverage_ratio": 0.8,
                    "confidence": 60.0,
                    "raw_state": raw_state,
                    "state_label": raw_state,
                    "display_state": "OFF" if raw_state == "OFF" else "WATCH",
                }
            )

        vector_rows = build_current_scenario_vector_rows(partial_old_rows + full_latest_rows, [])

        self.assertEqual(len(vector_rows), 10)
        self.assertEqual(set(vector_rows[0].keys()), set(SCENARIO_VECTOR_FIELDS))
        self.assertTrue(all(row["as_of_date"] == "2026-05-11" for row in vector_rows))
        self.assertTrue(all(0.0 <= row["score"] <= 100.0 for row in vector_rows))
        self.assertTrue(all(0.0 <= row["confidence"] <= 100.0 for row in vector_rows))
        self.assertTrue(all(0.0 <= row["coverage"] <= 1.0 for row in vector_rows))
        self.assertTrue(all(row["engine_version"] == ENGINE_VERSION for row in vector_rows))
        self.assertTrue(
            all(row["display_state"] == "OFF" for row in vector_rows if row["raw_state"] == "OFF")
        )

    def test_off_state_is_not_promoted_to_provisional(self):
        row = {
            "scenario_code": "korea_domestic_financial_stress",
            "raw_state": "OFF",
            "coverage_ratio": 0.65,
            "confidence": 35.0,
        }

        self.assertEqual(scenario_display_state(row), "OFF")

    def test_non_off_low_trust_state_can_be_provisional(self):
        row = {
            "scenario_code": "korea_domestic_financial_stress",
            "raw_state": "WATCH",
            "coverage_ratio": 0.65,
            "confidence": 35.0,
        }

        self.assertEqual(scenario_display_state(row), "PROVISIONAL")

    def test_builds_equal_weight_synthetic_basket_series(self):
        series_map = {
            "A": [("2026-05-01", 100.0), ("2026-05-02", 110.0), ("2026-05-03", 121.0)],
            "B": [("2026-05-01", 50.0), ("2026-05-02", 50.0), ("2026-05-03", 55.0)],
        }

        basket_map, metadata = build_synthetic_basket_series(
            series_map,
            basket_specs=[
                {
                    "ticker": "TEST_BASKET",
                    "label": "Test basket",
                    "members": ["A", "B"],
                    "min_count": 2,
                }
            ],
        )

        self.assertEqual(len(basket_map["TEST_BASKET"]), 2)
        self.assertAlmostEqual(basket_map["TEST_BASKET"][0][1], 105.0)
        self.assertAlmostEqual(basket_map["TEST_BASKET"][1][1], 115.5)
        self.assertEqual(metadata[0]["loaded_members"], "A|B")

    def test_low_frequency_indicators_forward_fill_with_staleness_metadata(self):
        calendar_dates = ["2026-05-01", "2026-05-02", "2026-05-03"]
        observations = {
            "KR_CREDIT_SPREAD_AA3Y_GOV3Y": [
                {"date": "2026-04-30", "value": 0.82, "source": "test"},
                {"date": "2026-05-02", "value": 0.95, "source": "test"},
            ]
        }

        series_map, metadata = build_low_frequency_indicator_series(
            calendar_dates,
            anchor_date="2026-05-03",
            observations_by_ticker=observations,
        )

        self.assertEqual(
            series_map["KR_CREDIT_SPREAD_AA3Y_GOV3Y"],
            [("2026-05-01", 0.82), ("2026-05-02", 0.95), ("2026-05-03", 0.95)],
        )
        row = next(item for item in metadata if item["ticker"] == "KR_CREDIT_SPREAD_AA3Y_GOV3Y")
        self.assertEqual(row["last_observed_date"], "2026-05-02")
        self.assertEqual(row["staleness_days"], 1)
        self.assertEqual(row["source_quality"], "manual")

    def test_low_frequency_seed_source_quality_is_preserved(self):
        calendar_dates = ["2026-05-01"]
        observations = {
            "KR_CREDIT_SPREAD_AA3Y_GOV3Y": [
                {"date": "2026-04-30", "value": 0.82, "source": "BOK_ECOS_SEED"},
            ]
        }

        _, metadata = build_low_frequency_indicator_series(
            calendar_dates,
            anchor_date="2026-05-01",
            observations_by_ticker=observations,
        )

        row = next(item for item in metadata if item["ticker"] == "KR_CREDIT_SPREAD_AA3Y_GOV3Y")
        self.assertEqual(row["source_quality"], "seed")

    def test_event_overlay_uses_bounded_score_normalization(self):
        outputs = build_market_state_phase1_to4(
            {
                GEOPOLITICAL_EVENT_OVERLAY: [
                    ("2026-05-01", 75.0),
                ]
            }
        )

        event_feature = next(
            row for row in outputs["feature_rows"] if row["signal_name"] == "event_overlay_score"
        )
        self.assertEqual(event_feature["metric_type"], "bounded_score")
        self.assertAlmostEqual(event_feature["normalized_value"], 1.0)
        state_row = next(
            row for row in outputs["state_rows"] if row["scenario_code"] == "geopolitical_escalation_supply_shock"
        )
        self.assertTrue(set(["source_quality", "event_or_seed_dependent", "top_positive_drivers", "top_negative_drivers"]).issubset(SCENARIO_STATE_FIELDS))
        self.assertEqual(state_row["source_quality"], "manual")
        self.assertEqual(state_row["event_or_seed_dependent"], "Y")
        self.assertIn("Geopolitical event overlay score", state_row["top_positive_drivers"])


if __name__ == "__main__":
    unittest.main()
