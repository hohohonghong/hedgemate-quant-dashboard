# HedgeMate Recommendation Status QA (Post-Backtest)

- generated_at_utc: 2026-06-05T09:04:58Z
- hedgemate_run_id: hedgemate-refresh-20260605
- backtest_run_id: backtest-refresh-20260605
- basis: post-backtest gated recommendation CSVs
- portfolio_1to1_gated_csv: C:\Users\석민\Documents\cau_2026_ss\금융인공지능실습1\project\HedgeMate\outputs\reports\portfolio_1to1_hedge_hedgemate-refresh-20260605_backtest_gated.csv
- portfolio_multi_gated_csv: C:\Users\석민\Documents\cau_2026_ss\금융인공지능실습1\project\HedgeMate\outputs\reports\portfolio_multi_hedge_hedgemate-refresh-20260605_backtest_gated.csv

## Status Counts

- PASS_RECOMMEND: 0
- REFERENCE_ONLY: 44
- FAIL_GATE: 133
- INSUFFICIENT_DATA: 0

## Backtest Gate Counts

- VALIDATION_INSUFFICIENT: 21
- VALIDATION_NOT_ELIGIBLE: 133
- VALIDATION_THIN: 23

## Formal Gate Blocker Counts

- fail_gate: 133
- validation_not_eligible: 133
- liquidity_below_formal: 119
- return_drag_reference: 55
- reference_only: 44
- bootstrap_not_robust: 23
- validation_thin: 23
- cash_bootstrap_not_robust: 22
- validation_insufficient: 21
- cash_baseline_lag: 9

## Backtest Attribution Summary

- attribution_csv: C:\Users\석민\Documents\cau_2026_ss\금융인공지능실습1\project\HedgeMate\outputs\reports\backtest_attribution_backtest-refresh-20260605.csv
- attribution_md: C:\Users\석민\Documents\cau_2026_ss\금융인공지능실습1\project\HedgeMate\outputs\reports\backtest_attribution_backtest-refresh-20260605.md
- evaluated_count: 381
- improved_count: 375
- worsened_count: 6

| candidate | scenario | evaluated | worsened | worsened_rate | worst_metric | worst_delta | worst_case |
|---|---|---:|---:|---:|---|---:|---|
| 005490.KS | acute_global_stress_liquidity_crunch | 3 | 3 | 1.0 | cost_adjusted_return_drag | -0.070262 | 2023 US Regional Bank / Credit Stress |
| 055550.KS | acute_global_stress_liquidity_crunch | 6 | 3 | 0.5 | cost_adjusted_return_drag | -0.357924 | 2023 US Regional Bank / Credit Stress |
| 005490.KS | china_trade_fragmentation_shock | 1 | 0 | 0.0 | net_stress_loss | -0.146182 | China Slowdown / Property Stress |
| 005490.KS | geopolitical_escalation_supply_shock | 1 | 0 | 0.0 | cost_adjusted_return_drag | -0.073375 | 2024 Middle East / Shipping Supply Shock |
| 005490.KS | higher_for_longer_long_rate_shock | 1 | 0 | 0.0 | cash_net_MDD | -0.00978 | 2022 Global Rate Shock |
| 005490.KS | semiconductor_ai_cycle_shock | 1 | 0 | 0.0 | cost_adjusted_return_drag | -0.035472 | 2024 AI Semiconductor Concentration / Pullback Risk |
| 005490.KS | stagflation_reinflation_energy_shock | 1 | 0 | 0.0 | cash_net_MDD | -0.012707 | Russia-Ukraine / War-Energy Shock |
| 005490.KS | usd_strength_krw_weakness | 1 | 0 | 0.0 | cash_net_stress_loss | -0.006401 | 2022 KRW Weakness / USD Strength |
| 011200.KS | acute_global_stress_liquidity_crunch | 3 | 0 | 0.0 | cost_adjusted_return_drag | -0.267695 | 2023 US Regional Bank / Credit Stress |
| 011200.KS | china_trade_fragmentation_shock | 1 | 0 | 0.0 | net_stress_loss | -0.135625 | China Slowdown / Property Stress |

## Zero Formal Recommendation Message

- 현재 검증 기준에서 정식 추천 가능한 후보는 없습니다. 참고용 후보는 있으나, backtest evidence가 부족하거나 일부 구간에서 위험 악화가 확인되어 정식 추천으로 분류하지 않았습니다.

## Policy Audit

- WORSENED candidates still marked PASS_RECOMMEND: 0
- INSUFFICIENT_HISTORY-only candidates marked as successful PASS_RECOMMEND: 0
- Missing backtest evidence is treated as validation missing and cannot upgrade a formal recommendation.
- Combination candidates require evidence for the same combination; component evidence alone is not used for upgrade.

## Examples By Final Status

| recommendation_status | candidate | backtest_gate_status | worsened | insufficient_history | reason |
|---|---|---|---:|---:|---|
| PASS_RECOMMEND | - | - | 0 | 0 | no rows in this run |
| REFERENCE_ONLY | FXY | VALIDATION_THIN | 0 | 0 | target-scenario backtest has only 1 evaluated stress case; 표본 부족 |
| REFERENCE_ONLY | FXF | VALIDATION_INSUFFICIENT | 0 | 0 | target-scenario historical validation has insufficient history; 검증 부족 |
| REFERENCE_ONLY | FXE | VALIDATION_THIN | 0 | 0 | target-scenario backtest has only 1 evaluated stress case; 표본 부족 |
| REFERENCE_ONLY | 068270.KS | VALIDATION_INSUFFICIENT | 0 | 0 | target-scenario historical validation has insufficient history; 검증 부족 |
| REFERENCE_ONLY | 017670.KS | VALIDATION_INSUFFICIENT | 0 | 0 | target-scenario historical validation has insufficient history; 검증 부족 |
| REFERENCE_ONLY | 055550.KS | VALIDATION_INSUFFICIENT | 0 | 0 | target-scenario historical validation has insufficient history; 검증 부족 |
| REFERENCE_ONLY | 011200.KS | VALIDATION_INSUFFICIENT | 0 | 0 | target-scenario historical validation has insufficient history; 검증 부족 |
| REFERENCE_ONLY | 005490.KS | VALIDATION_INSUFFICIENT | 0 | 0 | target-scenario historical validation has insufficient history; 검증 부족 |
| REFERENCE_ONLY | 114800.KS | VALIDATION_INSUFFICIENT | 0 | 0 | target-scenario historical validation has insufficient history; 검증 부족 |
| REFERENCE_ONLY | SH | VALIDATION_INSUFFICIENT | 0 | 0 | target-scenario historical validation has insufficient history; 검증 부족 |
| FAIL_GATE | 261240.KS | VALIDATION_NOT_ELIGIBLE | 0 | 0 | candidate was not eligible for the bounded scenario backtest run |
| FAIL_GATE | BTAL | VALIDATION_NOT_ELIGIBLE | 0 | 0 | candidate was not eligible for the bounded scenario backtest run |
| FAIL_GATE | 153130.KS | VALIDATION_NOT_ELIGIBLE | 0 | 0 | candidate was not eligible for the bounded scenario backtest run |
| FAIL_GATE | 132030.KS | VALIDATION_NOT_ELIGIBLE | 0 | 0 | candidate was not eligible for the bounded scenario backtest run |
| FAIL_GATE | SPLV | VALIDATION_NOT_ELIGIBLE | 0 | 0 | candidate was not eligible for the bounded scenario backtest run |
| FAIL_GATE | USMV | VALIDATION_NOT_ELIGIBLE | 0 | 0 | candidate was not eligible for the bounded scenario backtest run |
| FAIL_GATE | 207940.KS | VALIDATION_NOT_ELIGIBLE | 0 | 0 | candidate was not eligible for the bounded scenario backtest run |
| FAIL_GATE | 105560.KS | VALIDATION_NOT_ELIGIBLE | 0 | 0 | candidate was not eligible for the bounded scenario backtest run |
| FAIL_GATE | 032830.KS | VALIDATION_NOT_ELIGIBLE | 0 | 0 | candidate was not eligible for the bounded scenario backtest run |
| FAIL_GATE | BTC-USD | VALIDATION_NOT_ELIGIBLE | 0 | 0 | candidate was not eligible for the bounded scenario backtest run |
| INSUFFICIENT_DATA | - | - | 0 | 0 | no rows in this run |
