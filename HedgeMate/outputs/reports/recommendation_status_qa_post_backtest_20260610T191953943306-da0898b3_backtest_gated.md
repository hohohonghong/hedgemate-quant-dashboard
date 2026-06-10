# HedgeMate Recommendation Status QA (Post-Backtest)

- generated_at_utc: 2026-06-10T10:23:59Z
- hedgemate_run_id: 20260610T191953943306-da0898b3
- backtest_run_id: backtest-20260610T191953943306-da0898b3
- basis: post-backtest gated recommendation CSVs
- portfolio_1to1_gated_csv: C:\Users\석민\Documents\cau_2026_ss\금융인공지능실습1\project\HedgeMate\outputs\reports\portfolio_1to1_hedge_20260610T191953943306-da0898b3_backtest_gated.csv
- portfolio_multi_gated_csv: C:\Users\석민\Documents\cau_2026_ss\금융인공지능실습1\project\HedgeMate\outputs\reports\portfolio_multi_hedge_20260610T191953943306-da0898b3_backtest_gated.csv

## Status Counts

- PASS_RECOMMEND: 0
- REFERENCE_ONLY: 10
- FAIL_GATE: 18
- INSUFFICIENT_DATA: 0

## Backtest Gate Counts

- VALIDATION_INSUFFICIENT: 8
- VALIDATION_NOT_ELIGIBLE: 18
- VALIDATION_THIN: 2

## Formal Gate Blocker Counts

- fail_gate: 18
- validation_not_eligible: 18
- liquidity_below_formal: 16
- reference_only: 10
- validation_insufficient: 8
- return_drag_reference: 6
- bootstrap_not_robust: 2
- cash_bootstrap_not_robust: 2
- validation_thin: 2

## Backtest Attribution Summary

- attribution_csv: C:\Users\석민\Documents\cau_2026_ss\금융인공지능실습1\project\HedgeMate\outputs\reports\backtest_attribution_backtest-20260610T191953943306-da0898b3.csv
- attribution_md: C:\Users\석민\Documents\cau_2026_ss\금융인공지능실습1\project\HedgeMate\outputs\reports\backtest_attribution_backtest-20260610T191953943306-da0898b3.md
- evaluated_count: 90
- improved_count: 88
- worsened_count: 2

| candidate | scenario | evaluated | worsened | worsened_rate | worst_metric | worst_delta | worst_case |
|---|---|---:|---:|---:|---|---:|---|
| 000270.KS | acute_global_stress_liquidity_crunch | 3 | 1 | 0.3333 | cost_adjusted_return_drag | -0.07747 | 2023 US Regional Bank / Credit Stress |
| 055550.KS | acute_global_stress_liquidity_crunch | 3 | 1 | 0.3333 | cost_adjusted_return_drag | -0.16085 | 2023 US Regional Bank / Credit Stress |
| 000270.KS | china_trade_fragmentation_shock | 1 | 0 | 0.0 | net_stress_loss | -0.082805 | China Slowdown / Property Stress |
| 000270.KS | geopolitical_escalation_supply_shock | 1 | 0 | 0.0 | cost_adjusted_return_drag | -0.008615 | 2024 Middle East / Shipping Supply Shock |
| 000270.KS | higher_for_longer_long_rate_shock | 1 | 0 | 0.0 | cash_net_stress_loss | -0.012613 | 2022 Global Rate Shock |
| 000270.KS | semiconductor_ai_cycle_shock | 1 | 0 | 0.0 | cash_net_MDD | -0.01285 | 2024 AI Semiconductor Concentration / Pullback Risk |
| 000270.KS | stagflation_reinflation_energy_shock | 1 | 0 | 0.0 | cash_net_stress_loss | -0.012944 | Russia-Ukraine / War-Energy Shock |
| 000270.KS | usd_strength_krw_weakness | 1 | 0 | 0.0 | cash_net_stress_loss | -0.012847 | 2022 KRW Weakness / USD Strength |
| 017670.KS | acute_global_stress_liquidity_crunch | 3 | 0 | 0.0 | cost_adjusted_return_drag | -0.088033 | 2023 US Regional Bank / Credit Stress |
| 017670.KS | china_trade_fragmentation_shock | 1 | 0 | 0.0 | net_stress_loss | -0.063745 | China Slowdown / Property Stress |

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
| REFERENCE_ONLY | 261240.KS | VALIDATION_THIN | 0 | 0 | target-scenario backtest has only 1 evaluated stress case; 표본 부족 |
| REFERENCE_ONLY | 153130.KS | VALIDATION_INSUFFICIENT | 0 | 0 | target-scenario historical validation has insufficient history; 검증 부족 |
| REFERENCE_ONLY | 132030.KS | VALIDATION_INSUFFICIENT | 0 | 0 | target-scenario historical validation has insufficient history; 검증 부족 |
| REFERENCE_ONLY | 017670.KS | VALIDATION_INSUFFICIENT | 0 | 0 | target-scenario historical validation has insufficient history; 검증 부족 |
| REFERENCE_ONLY | 000270.KS | VALIDATION_INSUFFICIENT | 0 | 0 | target-scenario historical validation has insufficient history; 검증 부족 |
| REFERENCE_ONLY | 105560.KS | VALIDATION_INSUFFICIENT | 0 | 0 | target-scenario historical validation has insufficient history; 검증 부족 |
| REFERENCE_ONLY | 055550.KS | VALIDATION_INSUFFICIENT | 0 | 0 | target-scenario historical validation has insufficient history; 검증 부족 |
| REFERENCE_ONLY | 261240.KS + 017670.KS | VALIDATION_THIN | 0 | 0 | target-scenario backtest has only 1 evaluated stress case; 표본 부족 |
| REFERENCE_ONLY | 153130.KS + 017670.KS | VALIDATION_INSUFFICIENT | 0 | 0 | target-scenario historical validation has insufficient history; 검증 부족 |
| REFERENCE_ONLY | 132030.KS + 017670.KS | VALIDATION_INSUFFICIENT | 0 | 0 | target-scenario historical validation has insufficient history; 검증 부족 |
| FAIL_GATE | 114800.KS | VALIDATION_NOT_ELIGIBLE | 0 | 0 | candidate was not eligible for the bounded scenario backtest run |
| FAIL_GATE | 005380.KS | VALIDATION_NOT_ELIGIBLE | 0 | 0 | candidate was not eligible for the bounded scenario backtest run |
| FAIL_GATE | 000810.KS | VALIDATION_NOT_ELIGIBLE | 0 | 0 | candidate was not eligible for the bounded scenario backtest run |
| FAIL_GATE | 032830.KS | VALIDATION_NOT_ELIGIBLE | 0 | 0 | candidate was not eligible for the bounded scenario backtest run |
| FAIL_GATE | 066570.KS | VALIDATION_NOT_ELIGIBLE | 0 | 0 | candidate was not eligible for the bounded scenario backtest run |
| FAIL_GATE | 261240.KS + 005380.KS | VALIDATION_NOT_ELIGIBLE | 0 | 0 | candidate was not eligible for the bounded scenario backtest run |
| FAIL_GATE | 261240.KS + 000270.KS | VALIDATION_NOT_ELIGIBLE | 0 | 0 | candidate was not eligible for the bounded scenario backtest run |
| FAIL_GATE | 261240.KS + 105560.KS | VALIDATION_NOT_ELIGIBLE | 0 | 0 | candidate was not eligible for the bounded scenario backtest run |
| FAIL_GATE | 153130.KS + 005380.KS | VALIDATION_NOT_ELIGIBLE | 0 | 0 | candidate was not eligible for the bounded scenario backtest run |
| FAIL_GATE | 153130.KS + 000270.KS | VALIDATION_NOT_ELIGIBLE | 0 | 0 | candidate was not eligible for the bounded scenario backtest run |
| INSUFFICIENT_DATA | - | - | 0 | 0 | no rows in this run |
