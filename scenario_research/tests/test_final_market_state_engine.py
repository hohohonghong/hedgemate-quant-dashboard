import unittest

from scripts.final_market_state_engine import (
    build_final_market_state_rows,
    build_scenario_vector_rows_from_final,
    build_top_active_scenarios_payload,
)


class FinalMarketStateEngineTest(unittest.TestCase):
    def test_merges_structured_and_overlay_scores(self):
        state_rows = [
            {
                "date": "2026-05-06",
                "scenario_code": "higher_for_longer_long_rate_shock",
                "scenario_name": "Higher-for-Longer / Long-Rate Shock",
                "scenario_name_ko": "장기금리 부담장",
                "lens": "us_global",
                "related_lenses": "korea_semiconductor|fx_krw",
                "structured_score": "60",
                "confidence": "50",
                "coverage_ratio": "0.90",
                "raw_state": "ACTIVE",
                "display_state": "ACTIVE",
            }
        ]
        overlay_rows = [
            {
                "date": "2026-05-06",
                "scenario_code": "higher_for_longer_long_rate_shock",
                "event_overlay_score": "80",
                "overlay_confidence": "70",
                "event_count": "2",
            }
        ]

        final_rows, confidence_rows = build_final_market_state_rows(state_rows, overlay_rows)

        self.assertEqual(final_rows[0]["overlay_applied"], "Y")
        self.assertAlmostEqual(final_rows[0]["final_score"], 63.0)
        self.assertAlmostEqual(final_rows[0]["final_confidence"], 53.0)
        self.assertEqual(confidence_rows[0]["overlay_applied"], "Y")

    def test_preserves_structured_score_without_overlay(self):
        state_rows = [
            {
                "date": "2026-05-06",
                "scenario_code": "soft_landing_goldilocks",
                "scenario_name": "Soft Landing / Goldilocks",
                "scenario_name_ko": "우호적 위험선호장",
                "lens": "us_global",
                "related_lenses": "korea_market",
                "structured_score": "78",
                "confidence": "66",
                "coverage_ratio": "0.92",
                "raw_state": "STRESS",
                "display_state": "STRONG",
            }
        ]

        final_rows, _ = build_final_market_state_rows(state_rows, [])
        payload = build_top_active_scenarios_payload(final_rows)

        self.assertEqual(final_rows[0]["overlay_applied"], "N")
        self.assertAlmostEqual(final_rows[0]["final_score"], 78.0)
        self.assertEqual(final_rows[0]["final_display_state"], "STRONG")
        self.assertEqual(payload["top_active_scenarios"][0]["scenario_code"], "soft_landing_goldilocks")

    def test_preserves_structured_display_state_without_overlay_even_below_active_threshold(self):
        state_rows = [
            {
                "date": "2026-05-06",
                "scenario_code": "soft_landing_goldilocks",
                "scenario_name": "Soft Landing / Goldilocks",
                "scenario_name_ko": "Soft landing",
                "lens": "us_global",
                "related_lenses": "korea_market",
                "structured_score": "72.62",
                "confidence": "66",
                "coverage_ratio": "0.92",
                "raw_state": "STRESS",
                "display_state": "STRONG",
            }
        ]

        final_rows, _ = build_final_market_state_rows(state_rows, [])

        self.assertEqual(final_rows[0]["overlay_applied"], "N")
        self.assertEqual(final_rows[0]["final_state"], "STRESS")
        self.assertEqual(final_rows[0]["final_display_state"], "STRONG")

    def test_final_off_state_is_not_promoted_to_provisional_or_watch(self):
        state_rows = [
            {
                "date": "2026-05-06",
                "scenario_code": "korea_domestic_financial_stress",
                "scenario_name": "Korea Domestic Financial Stress",
                "scenario_name_ko": "한국 내수 금융스트레스장",
                "lens": "korea_market",
                "related_lenses": "fx_krw|credit|real_estate",
                "structured_score": "42",
                "confidence": "35",
                "coverage_ratio": "0.65",
                "raw_state": "OFF",
                "display_state": "OFF",
            }
        ]

        final_rows, _ = build_final_market_state_rows(state_rows, [])

        self.assertEqual(final_rows[0]["final_state"], "OFF")
        self.assertEqual(final_rows[0]["final_display_state"], "OFF")

    def test_final_vector_export_maps_latest_full_date(self):
        state_rows = [
            {
                "date": "2026-05-10",
                "scenario_code": "soft_landing_goldilocks",
                "scenario_name": "Soft Landing / Goldilocks",
                "scenario_name_ko": "Soft landing",
                "lens": "us_global",
                "related_lenses": "korea_market",
                "structured_score": "50",
                "confidence": "60",
                "coverage_ratio": "1.0",
                "raw_state": "WATCH",
                "display_state": "WATCH",
            },
            {
                "date": "2026-05-11",
                "scenario_code": "soft_landing_goldilocks",
                "scenario_name": "Soft Landing / Goldilocks",
                "scenario_name_ko": "Soft landing",
                "lens": "us_global",
                "related_lenses": "korea_market",
                "structured_score": "70",
                "confidence": "80",
                "coverage_ratio": "1.0",
                "raw_state": "ACTIVE",
                "display_state": "ACTIVE",
            },
            {
                "date": "2026-05-11",
                "scenario_code": "korea_domestic_financial_stress",
                "scenario_name": "Korea Domestic Financial Stress",
                "scenario_name_ko": "Korea stress",
                "lens": "korea_market",
                "related_lenses": "credit",
                "structured_score": "30",
                "confidence": "80",
                "coverage_ratio": "1.0",
                "raw_state": "OFF",
                "display_state": "OFF",
            },
        ]

        final_rows, _ = build_final_market_state_rows(state_rows, [])
        vector_rows = build_scenario_vector_rows_from_final(final_rows)

        self.assertEqual(len(vector_rows), 2)
        self.assertTrue(all(row["as_of_date"] == "2026-05-11" for row in vector_rows))
        self.assertEqual({row["scenario_code"] for row in vector_rows}, {"soft_landing_goldilocks", "korea_domestic_financial_stress"})
        off_row = next(row for row in vector_rows if row["scenario_code"] == "korea_domestic_financial_stress")
        self.assertEqual(off_row["raw_state"], "OFF")
        self.assertEqual(off_row["display_state"], "OFF")

    def test_final_vector_preserves_source_quality_and_driver_context(self):
        state_rows = [
            {
                "date": "2026-05-11",
                "scenario_code": "geopolitical_escalation_supply_shock",
                "scenario_name": "Geopolitical Escalation / Supply Shock",
                "scenario_name_ko": "Geo stress",
                "lens": "geopolitical",
                "related_lenses": "commodity|fx_krw",
                "structured_score": "55",
                "confidence": "70",
                "coverage_ratio": "1.0",
                "raw_state": "WATCH",
                "display_state": "WATCH",
                "source_quality": "manual",
                "event_or_seed_dependent": "Y",
                "top_positive_drivers": "event overlay",
                "top_negative_drivers": "oil relief",
                "market_interpretation_ko": "Manual event context only.",
            }
        ]

        final_rows, _ = build_final_market_state_rows(state_rows, [])
        vector_rows = build_scenario_vector_rows_from_final(final_rows)

        self.assertEqual(final_rows[0]["source_quality"], "manual")
        self.assertEqual(final_rows[0]["event_or_seed_dependent"], "Y")
        self.assertEqual(vector_rows[0]["source_quality"], "manual")
        self.assertEqual(vector_rows[0]["event_or_seed_dependent"], "Y")
        self.assertEqual(vector_rows[0]["top_positive_drivers"], "event overlay")
        self.assertEqual(vector_rows[0]["market_interpretation_ko"], "Manual event context only.")


if __name__ == "__main__":
    unittest.main()
