# HedgeMate Recommendation Status QA (Post-Backtest)

- generated_at_utc: 2026-06-10T14:48:49Z
- hedgemate_run_id: 20260610T234722934082-d6e95bcc
- backtest_run_id: backtest-20260610T234722934082-d6e95bcc
- basis: post-backtest gated recommendation CSVs
- portfolio_1to1_gated_csv: C:\Users\석민\Documents\cau_2026_ss\금융인공지능실습1\deploy_beecast\HedgeMate\outputs\reports\portfolio_1to1_hedge_20260610T234722934082-d6e95bcc_backtest_gated.csv
- portfolio_multi_gated_csv: C:\Users\석민\Documents\cau_2026_ss\금융인공지능실습1\deploy_beecast\HedgeMate\outputs\reports\portfolio_multi_hedge_20260610T234722934082-d6e95bcc_backtest_gated.csv

## Status Counts

- PASS_RECOMMEND: 0
- REFERENCE_ONLY: 0
- FAIL_GATE: 27
- INSUFFICIENT_DATA: 0

## Backtest Gate Counts

- VALIDATION_NOT_ELIGIBLE: 27

## Formal Gate Blocker Counts

- fail_gate: 27
- validation_not_eligible: 27
- liquidity_below_formal: 20
- return_drag_reference: 7

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
| REFERENCE_ONLY | - | - | 0 | 0 | no rows in this run |
| FAIL_GATE | 153130.KS | VALIDATION_NOT_ELIGIBLE | 0 | 0 | candidate was not eligible for the bounded scenario backtest run |
| FAIL_GATE | 132030.KS | VALIDATION_NOT_ELIGIBLE | 0 | 0 | candidate was not eligible for the bounded scenario backtest run |
| FAIL_GATE | 114800.KS | VALIDATION_NOT_ELIGIBLE | 0 | 0 | candidate was not eligible for the bounded scenario backtest run |
| FAIL_GATE | 017670.KS | VALIDATION_NOT_ELIGIBLE | 0 | 0 | candidate was not eligible for the bounded scenario backtest run |
| FAIL_GATE | 005930.KS | VALIDATION_NOT_ELIGIBLE | 0 | 0 | candidate was not eligible for the bounded scenario backtest run |
| FAIL_GATE | 105560.KS | VALIDATION_NOT_ELIGIBLE | 0 | 0 | candidate was not eligible for the bounded scenario backtest run |
| FAIL_GATE | 000810.KS | VALIDATION_NOT_ELIGIBLE | 0 | 0 | candidate was not eligible for the bounded scenario backtest run |
| FAIL_GATE | 032830.KS | VALIDATION_NOT_ELIGIBLE | 0 | 0 | candidate was not eligible for the bounded scenario backtest run |
| FAIL_GATE | 055550.KS | VALIDATION_NOT_ELIGIBLE | 0 | 0 | candidate was not eligible for the bounded scenario backtest run |
| FAIL_GATE | 035420.KS | VALIDATION_NOT_ELIGIBLE | 0 | 0 | candidate was not eligible for the bounded scenario backtest run |
| INSUFFICIENT_DATA | - | - | 0 | 0 | no rows in this run |
