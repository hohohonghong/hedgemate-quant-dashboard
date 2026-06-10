# HedgeMate Final Product Runbook

## Active Bundle

- data_version: 20260605
- generated_at_utc: 2026-06-05T09:04:58Z
- scenario_run: scenario-refresh-20260605
- final_market_state_run: final-refresh-20260605
- hedgemate_run: hedgemate-refresh-20260605
- backtest_run: backtest-refresh-20260605
- freshness_status: FRESH
- stale_reasons: none

## User Workflow

1. Open the HedgeMate dashboard.
2. Enter assets by Korean name, English name, or ticker. Mixed quantity and KRW amount input is supported.
3. Use price/FX preview before analysis. The preview shows resolved ticker, cached/live mode, price as-of, FX as-of, KRW value, weight, warnings, and row errors.
4. Use market-data refresh only when freshness says stale. If the active bundle is already current for the day, the refresh endpoint returns skipped_latest and avoids the heavy pipeline.
5. Run portfolio analysis after preview passes validation. Recommendations must be read with their recommendation_status, backtest gate, DQ status, and failure/reference reasons.

## API Surface

- GET /api/product-dashboard
- GET /api/active-bundle
- GET /api/data-freshness
- GET /api/scenario-sensitivities
- POST /api/price-lookup
- POST /api/portfolio/preview
- POST /api/refresh-market-data
- POST /api/run
- GET /api/run-status

## Evidence And Artifacts

- assetScenarioSensitivity: HedgeMate/outputs/processed/asset_scenario_sensitivity_hedgemate-refresh-20260605.csv
- backtestAttributionCsv: HedgeMate/outputs/reports/backtest_attribution_backtest-refresh-20260605.csv
- backtestAttributionSummary: HedgeMate/outputs/reports/backtest_attribution_backtest-refresh-20260605.md
- backtestCsv: HedgeMate/outputs/validation/walk_forward_backtest_backtest-refresh-20260605.csv
- backtestGateSummary: HedgeMate/outputs/reports/backtest_gate_summary_hedgemate-refresh-20260605_backtest_gated.md
- backtestSummary: HedgeMate/outputs/reports/walk_forward_backtest_summary_backtest-refresh-20260605.md
- eventOverlayMetadata: scenario_research/outputs/reports/event_overlay_metadata_event-refresh-20260605.json
- features: HedgeMate/outputs/processed/features_summary_hedgemate-refresh-20260605.csv
- finalMarketState: scenario_research/outputs/final/final_market_state_daily_final-refresh-20260605.csv
- finalMetadata: scenario_research/outputs/reports/final_market_state_metadata_final-refresh-20260605.json
- finalScenarioVector: scenario_research/outputs/scenario_vectors/current_scenario_vector_final-refresh-20260605.csv
- formalGateAuditCsv: HedgeMate/outputs/reports/formal_gate_audit_hedgemate-refresh-20260605_backtest_gated.csv
- formalGateAuditSummary: HedgeMate/outputs/reports/formal_gate_audit_hedgemate-refresh-20260605_backtest_gated.md
- hedgeActionCandidates: HedgeMate/outputs/reports/hedge_action_candidates_hedgemate-refresh-20260605.csv
- hedgeActionPlan: HedgeMate/outputs/reports/hedge_action_plan_hedgemate-refresh-20260605.json
- hedgeActionPlanSummary: HedgeMate/outputs/reports/hedge_action_plan_summary_hedgemate-refresh-20260605.md
- portfolio1to1: HedgeMate/outputs/reports/portfolio_1to1_hedge_hedgemate-refresh-20260605_backtest_gated.csv
- portfolioInput: HedgeMate/inputs/portfolio_weights.csv
- portfolioMulti: HedgeMate/outputs/reports/portfolio_multi_hedge_hedgemate-refresh-20260605_backtest_gated.csv
- portfolioVulnerabilityAttribution: HedgeMate/outputs/processed/portfolio_vulnerability_attribution_hedgemate-refresh-20260605.csv
- portfolioVulnerabilitySummary: HedgeMate/outputs/reports/portfolio_vulnerability_summary_hedgemate-refresh-20260605.json
- recommendationStatusQa: HedgeMate/outputs/reports/recommendation_status_qa_post_backtest_hedgemate-refresh-20260605_backtest_gated.md
- scenarioConfidence: scenario_research/outputs/final/scenario_confidence_final-refresh-20260605.csv
- scenarioVector: scenario_research/outputs/scenario_vectors/current_scenario_vector_scenario-refresh-20260605.csv
- topActiveScenarios: scenario_research/outputs/final/top_active_scenarios_final-refresh-20260605.json

## Decision Safety Rules

- WORSENED backtest evidence cannot remain PASS_RECOMMEND.
- INSUFFICIENT_HISTORY is validation-insufficient evidence, not success evidence.
- A combination hedge requires combination-level evidence; component evidence alone cannot upgrade it to a formal recommendation.
- Zero formal recommendations is a valid output when backtest or data evidence is insufficient.
- Cache, fixture, stale, missing-artifact, DQ WARN/FAIL, and API-key-required states must stay visible to the user.

## Known Non-Automated Items

- event_overlay_mode: reviewed_fixture
- live_gemini_extraction: implemented_api_key_required
- recommendation_usage: fixture_context_only
- trade_gate_usage: disabled_for_fixture
- I cannot issue external API keys, connect paid real-time market-data feeds, or configure brokerage credentials without user-provided access.
- HedgeMate is a decision-support dashboard, not an auto-trading or order-routing system.
