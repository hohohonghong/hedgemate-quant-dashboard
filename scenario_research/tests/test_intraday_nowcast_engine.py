import unittest
from datetime import datetime, timedelta, timezone

from scripts.intraday_nowcast_engine import build_nowcast_outputs


def make_rows(ticker, closes, *, start=None, label=None, asset_class="kr_stock", lens="korea_market"):
    start = start or datetime(2026, 5, 7, 0, 0, tzinfo=timezone.utc)
    rows = []
    for index, close in enumerate(closes):
        ts = start + timedelta(hours=index)
        kst = ts + timedelta(hours=9)
        rows.append(
            {
                "timestamp_utc": ts.isoformat(),
                "timestamp_kst": kst.isoformat(),
                "date_kst": kst.date().isoformat(),
                "hour_kst": kst.strftime("%H:%M"),
                "ticker": ticker,
                "label": label or ticker,
                "asset_class": asset_class,
                "lens": lens,
                "open": close,
                "high": close,
                "low": close,
                "close": close,
                "volume": 1000 + index,
                "currency": "KRW",
                "source": "fixture",
                "ingested_at": ts.isoformat(),
            }
        )
    return rows


class IntradayNowcastEngineTest(unittest.TestCase):
    def test_builds_risk_on_nowcast_from_hourly_rows(self):
        rows = []
        rows += make_rows("^KS200", [100, 100.5, 101.0, 102.0, 103.0], asset_class="kr_index")
        rows += make_rows("005930.KS", [100, 101, 102, 103, 104], lens="korea_semiconductor")
        rows += make_rows("000660.KS", [100, 101, 102, 103, 105], lens="korea_semiconductor")
        rows += make_rows("035420.KS", [100, 100.2, 100.5, 101, 102], lens="korea_growth")
        rows += make_rows("068270.KS", [100, 100.1, 100.2, 100.3, 100.4], lens="korea_defensive")
        rows += make_rows("207940.KS", [100, 100.1, 100.2, 100.3, 100.4], lens="korea_defensive")
        rows += make_rows("KRW=X", [1400, 1398, 1395, 1392, 1390], asset_class="fx", lens="fx_krw")
        rows += make_rows("EWY", [100, 100.3, 100.7, 101.0, 101.3], asset_class="us_etf", lens="korea_adr_proxy")
        rows += make_rows("SOXX", [100, 100.4, 100.8, 101.2, 101.6], asset_class="us_etf", lens="global_semiconductor")
        rows += make_rows("QQQ", [100, 100.2, 100.4, 100.6, 100.9], asset_class="us_etf", lens="global_growth")
        rows += make_rows("SPY", [100, 100.2, 100.4, 100.6, 100.8], asset_class="us_etf", lens="global_risk")

        ticker_features, signal_rows, vector_rows = build_nowcast_outputs(rows)

        self.assertGreaterEqual(len(ticker_features), 10)
        self.assertEqual(len(vector_rows), 5)
        risk_on = next(row for row in vector_rows if row["nowcast_code"] == "kr_risk_on_intraday")
        self.assertGreater(risk_on["score"], 70)
        self.assertEqual(risk_on["status"], "RISK_ON")
        self.assertGreaterEqual(risk_on["coverage"], 0.8)
        self.assertTrue(any(row["nowcast_code"] == "kr_risk_on_intraday" for row in signal_rows))

    def test_missing_core_tickers_marks_low_coverage(self):
        rows = make_rows("KRW=X", [1400, 1401, 1402, 1403, 1404], asset_class="fx", lens="fx_krw")

        _, _, vector_rows = build_nowcast_outputs(rows)

        risk_on = next(row for row in vector_rows if row["nowcast_code"] == "kr_risk_on_intraday")
        self.assertLess(risk_on["coverage"], 0.5)
        self.assertEqual(risk_on["status"], "INSUFFICIENT")


if __name__ == "__main__":
    unittest.main()
