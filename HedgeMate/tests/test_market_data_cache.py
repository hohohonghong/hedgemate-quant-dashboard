import csv
import importlib.util
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "market_data_cache.py"
spec = importlib.util.spec_from_file_location("market_data_cache", MODULE_PATH)
market_data_cache = importlib.util.module_from_spec(spec)
spec.loader.exec_module(market_data_cache)


class MarketDataCacheTests(unittest.TestCase):
    def write_raw(self, path, rows):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=market_data_cache.RAW_MARKET_COLUMNS)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    def test_incremental_update_fetches_only_missing_dates_and_writes_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            source = output_dir / "raw_market_daily_20260521.csv"
            self.write_raw(
                source,
                [
                    {
                        "date": "2026-05-20",
                        "ticker": "SPY",
                        "asset_class": "etf",
                        "source": "yahoo",
                        "open": 100,
                        "high": 101,
                        "low": 99,
                        "close": 100,
                        "adj_close": 100,
                        "volume": 1000,
                        "currency": "USD",
                        "ingested_at": "2026-05-21T00:00:00+00:00",
                    },
                    {
                        "date": "2026-05-21",
                        "ticker": "SPY",
                        "asset_class": "etf",
                        "source": "yahoo",
                        "open": 101,
                        "high": 102,
                        "low": 100,
                        "close": 101,
                        "adj_close": 101,
                        "volume": 1100,
                        "currency": "USD",
                        "ingested_at": "2026-05-21T00:00:00+00:00",
                    },
                ],
            )
            calls = []

            def fake_fetcher(ticker, start_date, end_date):
                calls.append((ticker, start_date, end_date))
                return [
                    {
                        "date": "2026-05-22",
                        "open": 102,
                        "high": 103,
                        "low": 101,
                        "close": 102,
                        "adj_close": 102,
                        "volume": 1200,
                    }
                ]

            result = market_data_cache.incremental_update_raw_market_data(
                [{"ticker": "SPY", "asset_class": "etf", "currency": "USD"}],
                output_dir,
                data_version="20260522",
                target_latest_date="2026-05-22",
                fetcher=fake_fetcher,
            )

            self.assertEqual(calls, [("SPY", date(2026, 5, 22), date(2026, 5, 22))])
            self.assertTrue(result["rawPath"].exists())
            self.assertTrue(result["manifestPath"].exists())
            manifest = result["manifest"]
            self.assertEqual(manifest["rowsAdded"], 1)
            self.assertEqual(manifest["latestMarketDate"], "2026-05-22")
            self.assertEqual(manifest["failedTickers"], [])
            self.assertEqual(manifest["refreshMode"], "market_data_only")
            self.assertEqual(list(output_dir.glob("*.tmp-*")), [])

    def test_incremental_update_keeps_partial_failures_as_warnings(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            source = output_dir / "raw_market_daily_20260521.csv"
            self.write_raw(
                source,
                [
                    {
                        "date": "2026-05-21",
                        "ticker": "SPY",
                        "asset_class": "etf",
                        "source": "yahoo",
                        "open": 100,
                        "high": 101,
                        "low": 99,
                        "close": 100,
                        "adj_close": 100,
                        "volume": 1000,
                        "currency": "USD",
                        "ingested_at": "2026-05-21T00:00:00+00:00",
                    }
                ],
            )

            result = market_data_cache.incremental_update_raw_market_data(
                [
                    {"ticker": "SPY", "asset_class": "etf", "currency": "USD"},
                    {"ticker": "MISSING", "asset_class": "etf", "currency": "USD"},
                ],
                output_dir,
                data_version="20260522",
                target_latest_date="2026-05-22",
                fetcher=lambda *_args, **_kwargs: [],
            )

            manifest = result["manifest"]
            self.assertTrue(result["rawPath"].exists())
            self.assertTrue(any(row["ticker"] == "MISSING" for row in manifest["failedTickers"]))
            self.assertTrue(any(row["ticker"] == "SPY" for row in manifest["failedTickers"]))


if __name__ == "__main__":
    unittest.main()
