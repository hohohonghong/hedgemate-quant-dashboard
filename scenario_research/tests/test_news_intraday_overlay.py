import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from scripts import news_intraday_overlay as news


class IntradayNewsOverlayTest(unittest.TestCase):
    def test_key_loader_supports_file_env_default_and_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            explicit = root / "explicit_key.txt"
            explicit.write_text("file-secret", encoding="utf-8")
            default = root / ".secrets" / "gemini_api_key.txt"
            default.parent.mkdir(parents=True)
            default.write_text("default-secret", encoding="utf-8")

            self.assertEqual(
                news.load_gemini_api_key(project_root=root, env={"GEMINI_API_KEY_FILE": str(explicit)}),
                ("file-secret", "GEMINI_API_KEY_FILE"),
            )
            self.assertEqual(
                news.load_gemini_api_key(project_root=root, env={}),
                ("default-secret", "project/.secrets/gemini_api_key.txt"),
            )
            self.assertEqual(
                news.load_gemini_api_key(project_root=root / "empty", env={"GEMINI_API_KEY": "env-secret"}),
                ("env-secret", "GEMINI_API_KEY"),
            )
            self.assertEqual(news.load_gemini_api_key(project_root=root / "empty", env={}), (None, "missing"))

    def test_openai_key_loader_supports_file_env_default_and_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            explicit = root / "explicit_openai_key.txt"
            explicit.write_text("file-secret", encoding="utf-8")
            default = root / ".secrets" / "openai_api_key.txt"
            default.parent.mkdir(parents=True)
            default.write_text("default-secret", encoding="utf-8")

            self.assertEqual(
                news.load_openai_api_key(project_root=root, env={"OPENAI_API_KEY_FILE": str(explicit)}),
                ("file-secret", "OPENAI_API_KEY_FILE"),
            )
            self.assertEqual(
                news.load_openai_api_key(project_root=root, env={}),
                ("default-secret", "project/.secrets/openai_api_key.txt"),
            )
            self.assertEqual(
                news.load_openai_api_key(project_root=root / "empty", env={"OPENAI_API_KEY": "env-secret"}),
                ("env-secret", "OPENAI_API_KEY"),
            )
            self.assertEqual(news.load_openai_api_key(project_root=root / "empty", env={}), (None, "missing"))

    def test_fallback_pipeline_writes_only_news_intraday_outputs_and_preserves_event_metadata(self):
        original_project_root = news.PROJECT_ROOT
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_dir = root / "scenario_research" / "outputs" / "news_intraday"
            manifest_path = root / "HedgeMate" / "outputs" / "latest_manifest.json"
            manifest_path.parent.mkdir(parents=True)
            manifest_path.write_text(
                json.dumps({"eventOverlayMetadata": "scenario_research/outputs/reports/event_overlay_metadata_keep.json"}),
                encoding="utf-8",
            )
            news.PROJECT_ROOT = root
            try:
                outputs = news.run_pipeline(
                    run_id="unit-news",
                    data_version="20260608",
                    trigger_reason="unit_test",
                    allow_network=False,
                    output_dir=output_dir,
                    manifest_path=manifest_path,
                )
            finally:
                news.PROJECT_ROOT = original_project_root

            self.assertFalse(outputs["reused"])
            self.assertTrue((output_dir / "news_candidates_unit-news.csv").exists())
            self.assertTrue((output_dir / "news_ranked_unit-news.csv").exists())
            self.assertTrue((output_dir / "news_overlay_article_unit-news.csv").exists())
            self.assertTrue((output_dir / "news_overlay_daily_unit-news.csv").exists())
            self.assertTrue((output_dir / "news_top5_unit-news.json").exists())
            self.assertFalse(list((root / "scenario_research" / "outputs" / "events").glob("event_overlay_daily_*.csv")))

            metadata = json.loads((output_dir / "news_overlay_metadata_unit-news.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["provider"], "fallback_fixture")
            self.assertTrue(metadata["fallback_used"])
            self.assertEqual(metadata["ai_provider"], "gemini")
            self.assertEqual(metadata["provider_model"], news.GEMINI_DEFAULT_MODEL)
            self.assertEqual(metadata["gemini_model"], news.GEMINI_DEFAULT_MODEL)
            self.assertEqual(metadata["allowed_refresh_hours_kst"], [9, 15, 21])
            self.assertLessEqual(metadata["top5_count"], 5)

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["eventOverlayMetadata"], "scenario_research/outputs/reports/event_overlay_metadata_keep.json")
            self.assertIn("latestIntradayNewsOverlay", manifest)
            self.assertIn("intradayNewsOverlayStatus", manifest)
            self.assertLessEqual(len(manifest["intradayNewsTop5"]), 5)

    def test_openai_pipeline_records_openai_provider_metadata_without_key(self):
        original_project_root = news.PROJECT_ROOT
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_dir = root / "scenario_research" / "outputs" / "news_intraday"
            manifest_path = root / "HedgeMate" / "outputs" / "latest_manifest.json"
            manifest_path.parent.mkdir(parents=True)
            manifest_path.write_text("{}", encoding="utf-8")
            news.PROJECT_ROOT = root
            try:
                news.run_pipeline(
                    run_id="unit-openai-news",
                    data_version="20260608",
                    trigger_reason="unit_test",
                    allow_network=False,
                    output_dir=output_dir,
                    manifest_path=manifest_path,
                    provider_name="openai",
                    model_name=news.OPENAI_DEFAULT_NEWS_MODEL,
                )
            finally:
                news.PROJECT_ROOT = original_project_root

            metadata = json.loads((output_dir / "news_overlay_metadata_unit-openai-news.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["ai_provider"], "openai")
            self.assertEqual(metadata["provider_model"], news.OPENAI_DEFAULT_NEWS_MODEL)
            self.assertEqual(metadata["provider_key_source"], "missing")
            self.assertEqual(metadata["provider"], "fallback_fixture")
            self.assertEqual(metadata["fallback_reason"], "missing_openai_api_key")
            self.assertEqual(metadata["openai_model"], news.OPENAI_DEFAULT_NEWS_MODEL)
            self.assertEqual(metadata["openai_key_source"], "missing")
            self.assertIsNone(metadata["gemini_model"])

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            status = manifest["intradayNewsOverlayStatus"]
            self.assertEqual(status["aiProvider"], "openai")
            self.assertEqual(status["providerModel"], news.OPENAI_DEFAULT_NEWS_MODEL)
            self.assertEqual(status["openaiKeySource"], "missing")

    def test_dedupe_source_limit_gemini_input_and_top5_limits(self):
        rows = []
        for index in range(20):
            rows.append(
                news.candidate_row(
                    source="unit",
                    title=f"Fed rate risk headline {index}",
                    summary="US treasury yield and KRW risk",
                    url=f"https://example.test/{index}",
                    provider="gdelt_doc_api",
                    source_rank=index + 1,
                )
            )
        rows.append(dict(rows[0]))
        ranked = news.rank_candidates(rows)
        gemini_input = news.select_gemini_input_candidates(ranked)
        raw_events = [news.infer_fallback_event(row) for row in gemini_input]
        articles, _ = news.validate_and_normalize_events(raw_events)
        top5 = news.build_top5(articles)

        self.assertEqual(len(ranked), 20)
        self.assertGreaterEqual(len(gemini_input), 5)
        self.assertLessEqual(len(gemini_input), 10)
        self.assertLessEqual(len(top5), 5)
        self.assertTrue(all(row.get("displayTitleKo") for row in top5))
        self.assertTrue(all(row.get("displaySummaryKo") for row in top5))
        self.assertTrue(all(news.has_hangul(row.get("displayTitleKo")) for row in top5))

    def test_top5_infers_fx_scenario_link_for_dollar_or_krw_news(self):
        event = news.infer_fallback_event(
            news.candidate_row(
                source="unit",
                title="US yields and dollar remain key intraday cross-asset risk checks",
                summary="USD/KRW pressure remains visible",
                provider="fallback_fixture",
            )
        )
        top5 = news.build_top5([event])

        self.assertIn("usd_strength_krw_weakness", top5[0]["scenarioLinks"])
        self.assertIn("higher_for_longer_long_rate_shock", top5[0]["scenarioLinks"])

    def test_google_news_rss_uses_item_source_and_url(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss><channel><item>
          <title>KOSPI semiconductor KRW risk</title>
          <source url="https://example.test">Reuters</source>
          <link>https://news.google.com/rss/articles/example</link>
          <pubDate>Mon, 08 Jun 2026 22:06:23 GMT</pubDate>
          <description>Market risk summary</description>
        </item></channel></rss>"""

        def fake_request_text(_url):
            return xml

        original = news.request_text
        news.request_text = fake_request_text
        try:
            rows = news.fetch_rss_feed_candidates(
                {
                    "source": "Google News",
                    "url": "https://news.google.com/rss/search?q=test",
                    "provider": "google_news_rss",
                    "use_item_source": True,
                }
            )
        finally:
            news.request_text = original

        self.assertEqual(rows[0]["source"], "Reuters")
        self.assertEqual(rows[0]["provider"], "google_news_rss")
        self.assertTrue(str(rows[0]["url"]).startswith("https://news.google.com/rss/articles/"))

    def test_google_news_candidates_are_limited_to_trusted_sources(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss><channel>
        <item>
          <title>Reuters trusted headline</title>
          <source url="https://example.test">Reuters</source>
          <link>https://news.google.com/rss/articles/reuters</link>
          <pubDate>Mon, 08 Jun 2026 22:06:23 GMT</pubDate>
          <description>Trusted market risk summary</description>
        </item>
        <item>
          <title>Alpha Economy headline</title>
          <source url="https://example.test">알파경제</source>
          <link>https://news.google.com/rss/articles/alpha</link>
          <pubDate>Mon, 08 Jun 2026 22:07:23 GMT</pubDate>
          <description>Blocked source summary</description>
        </item>
        <item>
          <title>Random blog headline</title>
          <source url="https://example.test">Random Finance Blog</source>
          <link>https://news.google.com/rss/articles/blog</link>
          <pubDate>Mon, 08 Jun 2026 22:08:23 GMT</pubDate>
          <description>Untrusted source summary</description>
        </item>
        </channel></rss>"""

        def fake_request_text(_url):
            return xml

        original = news.request_text
        news.request_text = fake_request_text
        try:
            rows = news.fetch_google_news_rss_candidates(limit=10)
        finally:
            news.request_text = original

        sources = {row["source"] for row in rows}
        self.assertEqual(sources, {"Reuters"})
        self.assertTrue(all(news.trusted_news_source(row["source"]) for row in rows))

    def test_gdelt_and_naver_candidates_drop_untrusted_sources(self):
        gdelt_payload = {
            "articles": [
                {
                    "sourceCommonName": "Reuters",
                    "title": "Trusted GDELT headline",
                    "url": "https://www.reuters.com/markets/example",
                    "seendate": "20260608T220623Z",
                },
                {
                    "sourceCommonName": "Random Finance Blog",
                    "title": "Untrusted GDELT headline",
                    "url": "https://blog.example.test/markets",
                    "seendate": "20260608T220723Z",
                },
            ]
        }
        naver_payload = {
            "items": [
                {
                    "title": "Trusted Naver headline",
                    "description": "Trusted original link",
                    "originallink": "https://www.mk.co.kr/news/stock/123",
                    "pubDate": "Mon, 08 Jun 2026 22:06:23 GMT",
                },
                {
                    "title": "Untrusted Naver headline",
                    "description": "Untrusted original link",
                    "originallink": "https://blog.example.test/news/123",
                    "pubDate": "Mon, 08 Jun 2026 22:07:23 GMT",
                },
            ]
        }

        def fake_request_json(url, headers=None):
            if "gdeltproject" in url:
                return gdelt_payload
            return naver_payload

        with patch.dict("os.environ", {"NAVER_CLIENT_ID": "id", "NAVER_CLIENT_SECRET": "secret"}):
            with patch.object(news, "request_json", side_effect=fake_request_json):
                gdelt_rows = news.fetch_gdelt_candidates(limit=10)
                naver_rows = news.fetch_naver_candidates(limit=10)

        self.assertEqual([row["source"] for row in gdelt_rows], ["Reuters"])
        self.assertEqual([row["source"] for row in naver_rows], ["매일경제"])

    def test_stale_network_candidates_are_filtered_without_fallback_when_today_news_exists(self):
        reference = datetime(2026, 6, 9, 12, 0, tzinfo=timezone.utc)
        stale = news.candidate_row(
            source="Federal Reserve",
            title="Minutes of the Federal Open Market Committee, April 28-29, 2026",
            summary="Old meeting minutes should not drive an intraday overlay.",
            url="https://example.test/old-fed-minutes",
            published_at=reference - timedelta(days=14),
            provider="official_rss",
        )
        fresh = news.candidate_row(
            source="unit",
            title="US yields rise during Asia trading",
            summary="Treasury yields and KRW pressure are visible intraday.",
            url="https://example.test/fresh",
            published_at=reference - timedelta(hours=2),
            provider="gdelt_doc_api",
        )
        yesterday_kst = news.candidate_row(
            source="unit",
            title="Yesterday KST headline should not be used today",
            summary="Less than 24 hours old but previous KST date.",
            url="https://example.test/yesterday",
            published_at=datetime(2026, 6, 8, 14, 59, tzinfo=timezone.utc),
            provider="google_news_rss",
        )

        with (
            patch.object(news, "fetch_gdelt_candidates", return_value=[fresh, yesterday_kst]),
            patch.object(news, "fetch_google_news_rss_candidates", return_value=[]),
            patch.object(news, "fetch_official_rss_candidates", return_value=[stale]),
            patch.object(news, "fetch_naver_candidates", return_value=[]),
        ):
            rows, statuses = news.collect_news_candidates(
                source_limit=10,
                allow_network=True,
                reference_dt=reference,
            )

        titles = [str(row.get("title")) for row in rows]
        self.assertIn("US yields rise during Asia trading", titles)
        self.assertNotIn("Yesterday KST headline should not be used today", titles)
        self.assertNotIn("Minutes of the Federal Open Market Committee, April 28-29, 2026", titles)
        self.assertTrue(all(news.is_recent_candidate(row, reference_dt=reference) for row in rows))

        filtered = [row for row in [stale, fresh, yesterday_kst] if news.is_recent_candidate(row, reference_dt=reference)]
        self.assertEqual(filtered, [fresh])
        self.assertFalse(any(status["source"] == "fallback_fixture" for status in statuses))
        official_status = next(status for status in statuses if status["source"] == "official_rss")
        self.assertEqual(official_status["stale_candidate_count"], 1)

    def test_missing_today_network_candidates_use_fallback_rows(self):
        reference = datetime(2026, 6, 9, 12, 0, tzinfo=timezone.utc)
        stale = news.candidate_row(
            source="Federal Reserve",
            title="Minutes of the Federal Open Market Committee, April 28-29, 2026",
            summary="Old meeting minutes should not drive an intraday overlay.",
            url="https://example.test/old-fed-minutes",
            published_at=reference - timedelta(days=14),
            provider="official_rss",
        )

        with (
            patch.object(news, "fetch_gdelt_candidates", return_value=[]),
            patch.object(news, "fetch_google_news_rss_candidates", return_value=[]),
            patch.object(news, "fetch_official_rss_candidates", return_value=[stale]),
            patch.object(news, "fetch_naver_candidates", return_value=[]),
        ):
            rows, statuses = news.collect_news_candidates(
                source_limit=10,
                allow_network=True,
                reference_dt=reference,
            )

        self.assertEqual(len(rows), news.GEMINI_INPUT_MIN)
        self.assertTrue(all(str(row.get("provider")) == "fallback_fixture" for row in rows))
        fallback_status = next(status for status in statuses if status["source"] == "fallback_fixture")
        self.assertEqual(fallback_status["status"], "fallback_no_today_news")

    def test_schema_validation_failure_blocks_bad_rows(self):
        with self.assertRaises(ValueError):
            news.validate_and_normalize_events([{"source": "bad", "title": ""}])

    def test_gemini_events_are_reconciled_to_candidate_kst_date_source_and_url(self):
        row = news.candidate_row(
            source="서울경제",
            title="환율 1550원 시대",
            summary="원화 약세와 금리 부담이 커졌다.",
            url="https://news.google.com/rss/articles/example",
            published_at=datetime(2026, 6, 8, 21, 0, tzinfo=timezone.utc),
            provider="google_news_rss",
        )
        event = news.infer_fallback_event(row)
        event.update(
            {
                "date": "2026-06-08",
                "source": "Wrong Source",
                "url_or_ref": "https://news.google.com/rss/articles/example",
                "evidence_span": '<a href="https://example.test">원화 약세</a> 부담 확대',
            }
        )

        def request(_api_key, _payload, model_name):
            return {"candidates": [{"content": {"parts": [{"text": json.dumps({"events": [event]})}]}}]}

        events, status = news.extract_events_with_gemini([row], api_key="secret", request_fn=request)

        self.assertFalse(status["fallback_used"])
        self.assertEqual(events[0]["date"], "2026-06-09")
        self.assertEqual(events[0]["source"], "서울경제")
        self.assertEqual(events[0]["url_or_ref"], "https://news.google.com/rss/articles/example")
        self.assertEqual(events[0]["evidence_span"], "원화 약세 부담 확대")

    def test_openai_events_are_reconciled_to_candidate_kst_date_source_and_url(self):
        row = news.candidate_row(
            source="한국경제",
            title="반도체 투자심리 약화",
            summary="삼성전자와 SK하이닉스가 약세를 보였다.",
            url="https://news.google.com/rss/articles/openai-example",
            published_at=datetime(2026, 6, 8, 21, 0, tzinfo=timezone.utc),
            provider="google_news_rss",
        )
        event = news.infer_fallback_event(row)
        event.update(
            {
                "date": "2026-06-08",
                "source": "Wrong Source",
                "url_or_ref": "https://news.google.com/rss/articles/openai-example",
                "evidence_span": '<b>반도체</b> 투자심리 약화',
            }
        )

        def request(_api_key, payload, model_name):
            self.assertEqual(model_name, news.OPENAI_DEFAULT_NEWS_MODEL)
            self.assertEqual(len(payload["rows"]), 1)
            return {
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": json.dumps({"events": [event]}),
                            }
                        ],
                    }
                ]
            }

        events, status = news.extract_events_with_openai(
            [row],
            api_key="secret",
            model_name=news.OPENAI_DEFAULT_NEWS_MODEL,
            request_fn=request,
        )

        self.assertFalse(status["fallback_used"])
        self.assertEqual(status["provider"], "openai")
        self.assertEqual(events[0]["date"], "2026-06-09")
        self.assertEqual(events[0]["source"], "한국경제")
        self.assertEqual(events[0]["url_or_ref"], "https://news.google.com/rss/articles/openai-example")
        self.assertEqual(events[0]["evidence_span"], "반도체 투자심리 약화")

    def test_openai_missing_key_falls_back_to_valid_rows(self):
        rows = [
            news.candidate_row(
                source="unit",
                title="KRW risk headline",
                summary="USD/KRW pressure remains visible",
                provider="gdelt_doc_api",
            )
        ]

        raw_events, status = news.extract_events_with_openai(rows, api_key=None)
        articles, errors = news.validate_and_normalize_events(raw_events)

        self.assertTrue(status["fallback_used"])
        self.assertEqual(status["fallback_reason"], "missing_openai_api_key")
        self.assertEqual(errors, [])
        self.assertEqual(len(articles), 1)

    def test_gemini_invalid_response_falls_back_to_valid_rows(self):
        rows = [
            news.candidate_row(
                source="unit",
                title="KRW risk headline",
                summary="USD/KRW pressure remains visible",
                provider="gdelt_doc_api",
            )
        ]

        def bad_request(_api_key, _payload, model_name):
            return {"candidates": [{"content": {"parts": [{"text": "{\"events\": [{\"title\": \"bad\"}]}"}]}}]}

        raw_events, status = news.extract_events_with_gemini(rows, api_key="secret", request_fn=bad_request)
        articles, errors = news.validate_and_normalize_events(raw_events)

        self.assertTrue(status["fallback_used"])
        self.assertEqual(errors, [])
        self.assertEqual(len(articles), 1)


if __name__ == "__main__":
    unittest.main()
