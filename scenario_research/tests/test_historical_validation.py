import unittest
import csv
from pathlib import Path

from scripts.run_historical_validation import HISTORICAL_CASES, build_validation_rows


class HistoricalValidationTest(unittest.TestCase):
    def test_builds_case_summary_for_available_history(self):
        state_rows = [
            {
                "date": "2022-02-01",
                "scenario_code": "stagflation_reinflation_energy_shock",
                "structured_score": "48",
                "display_state": "WATCH",
            },
            {
                "date": "2022-03-01",
                "scenario_code": "stagflation_reinflation_energy_shock",
                "structured_score": "77",
                "display_state": "STRESS",
            },
            {
                "date": "2022-02-01",
                "scenario_code": "soft_landing_goldilocks",
                "structured_score": "41",
                "display_state": "OFF",
            },
            {
                "date": "2022-03-01",
                "scenario_code": "soft_landing_goldilocks",
                "structured_score": "44",
                "display_state": "OFF",
            },
        ]
        cases = [
            {
                "case_code": "war_energy_shock_2022",
                "case_name": "Russia-Ukraine / War-Energy Shock",
                "start_date": "2022-02-01",
                "end_date": "2022-10-31",
                "scenario_code": "stagflation_reinflation_energy_shock",
            }
        ]

        rows = build_validation_rows(state_rows, cases=cases)

        self.assertEqual(rows[0]["validation_status"], "OK")
        self.assertEqual(rows[0]["case_id"], "war_energy_shock_2022")
        self.assertEqual(rows[0]["expected_scenario_code"], "stagflation_reinflation_energy_shock")
        self.assertIn(rows[0]["detection_status"], {"DETECTED", "LATE"})
        self.assertIn(rows[0]["data_sufficiency"], {"SUFFICIENT", "PARTIAL"})
        self.assertEqual(rows[0]["peak_date"], "2022-03-01")
        self.assertEqual(rows[0]["first_watch_date"], "2022-02-01")
        self.assertEqual(rows[0]["first_stress_date"], "2022-03-01")
        self.assertEqual(rows[0]["top_non_target_scenario"], "soft_landing_goldilocks")

    def test_marks_case_as_insufficient_without_history(self):
        rows = build_validation_rows([], cases=[{
            "case_code": "gfc_global_financial_crisis",
            "case_name": "GFC (글로벌 금융위기)",
            "start_date": "2007-10-01",
            "end_date": "2009-03-31",
            "scenario_code": "acute_global_stress_liquidity_crunch",
        }])

        self.assertEqual(rows[0]["validation_status"], "INSUFFICIENT_HISTORY")
        self.assertEqual(rows[0]["detection_status"], "INSUFFICIENT_HISTORY")
        self.assertEqual(rows[0]["data_sufficiency"], "INSUFFICIENT_HISTORY")
        self.assertEqual(rows[0]["observation_count"], 0)

    def test_wave1_case_registry_has_required_seed_contract(self):
        registry_path = (
            Path(__file__).resolve().parents[1]
            / "validation"
            / "historical_validation_case_registry_v1.csv"
        )
        with registry_path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))

        required_fields = {
            "case_id",
            "case_name",
            "expected_scenario_code",
            "start_date",
            "watch_date",
            "active_date",
            "stress_date",
            "peak_date",
            "end_date",
            "data_sufficiency",
            "detection_status",
            "detection_lag_days",
            "coverage_ratio",
            "notes",
        }
        self.assertGreaterEqual(len(rows), 8)
        self.assertEqual(set(rows[0].keys()), required_fields)
        self.assertTrue(all(row["case_id"] for row in rows))
        self.assertTrue(all(row["expected_scenario_code"] for row in rows))
        self.assertTrue(
            {row["data_sufficiency"] for row in rows}
            <= {"SUFFICIENT", "PARTIAL", "INSUFFICIENT_HISTORY"}
        )
        self.assertTrue(all(row["detection_status"] for row in rows))
        self.assertGreaterEqual(len(HISTORICAL_CASES), 8)


if __name__ == "__main__":
    unittest.main()
