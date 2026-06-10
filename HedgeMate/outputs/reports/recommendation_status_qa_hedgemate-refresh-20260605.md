# HedgeMate Pre-Backtest Candidate QA

- run_id: hedgemate-refresh-20260605
- scope: pre_backtest_candidate_screen
- formal_recommendation_gate: post_backtest_required
- note: PASS_RECOMMEND below is a pre-backtest candidate label only; it must not be shown as a formal recommendation until the backtest gate has run.
- 목적: 추천/참고/실패 상태를 사유별로 검증하기 위한 QA 요약입니다.

## Portfolio

### Counts
- scope: pre_backtest_candidate_screen; PASS_RECOMMEND in this report is a model candidate label, not a formal recommendation. Use the post-backtest gated QA/report for user-facing recommendation status.
- status: FAIL 133, PASS 44
- recommendation_status: PASS_RECOMMEND 7, REFERENCE_ONLY 37, FAIL_GATE 133, INSUFFICIENT_DATA 0
- candidate_role: UNKNOWN 38, benchmark_candidate 8, conditional_candidate 6, diagnostic_only 38, hedge_candidate 51, mixed_candidate_roles 30, research_only 6
- DQ WARN affected rows: 127
- DQ blocking affected rows: 0
- DQ non-blocking warning rows: 127

### Status Bucket Summary (Pre-Backtest Candidate Labels)
- PASS_RECOMMEND: 7
- REFERENCE_ONLY: 37
- FAIL_GATE: 133
- INSUFFICIENT_DATA: 0

### Top Gate Fail Reasons
- beta/corr 감소 미달: 58
- Stress 개선 미달: 50
- downside beta 증가 하드 게이트: 41
- 연환산 수익률 훼손 하드 게이트: 8
- MDD 개선 미달: 6
- active adverse scenario 민감도 증가: 2
- Sharpe 악화 하드 게이트: 2
- FAIL: 단일 자산 최대 20.0% 초과 - 261240.KS=30.0000%: 1
- FAIL: 단일 자산 최대 20.0% 초과 - FXY=30.0000%: 1
- FAIL: 단일 자산 최대 20.0% 초과 - BTAL=30.0000%: 1

### Top Reference Reasons
- annual return drag soft warning: 55
- Sharpe soft warning: 5
- 068270.KS: 장세 해석용 자산으로 기본 헤지 후보에서 제외: 2
- 017670.KS: 장세 해석용 자산으로 기본 헤지 후보에서 제외: 2
- 055550.KS: 장세 해석용 자산으로 기본 헤지 후보에서 제외: 2
- IAU: 범용 방어 benchmark입니다: 2
- GLD: 범용 방어 benchmark입니다: 2
- FXY: 핵심 취약점 직접 완화 후보 | 132030.KS: 범용 방어 benchmark입니다: 2
- FXF: 핵심 취약점 직접 완화 후보 | 132030.KS: 범용 방어 benchmark입니다: 2
- FXE: 핵심 취약점 직접 완화 후보 | 132030.KS: 범용 방어 benchmark입니다: 2

### Top DQ Non-Blocking Warnings
- DQ WARN non-blocking - BTAL: extreme_return_outlier_warn: 20
- DQ WARN non-blocking - 261240.KS: calendar_coverage_warn: 17
- DQ WARN non-blocking - FXY: fx_missing_warn: 17
- DQ WARN non-blocking - FXF: fx_missing_warn: 17
- DQ WARN non-blocking - FXE: fx_missing_warn: 17
- DQ WARN non-blocking - 153130.KS: calendar_coverage_warn: 17
- DQ WARN non-blocking - 132030.KS: calendar_coverage_warn: 17
- DQ WARN non-blocking - 068270.KS: calendar_coverage_warn: 2
- DQ WARN non-blocking - 017670.KS: calendar_coverage_warn: 2
- DQ WARN non-blocking - 055550.KS: calendar_coverage_warn: 2

### Top Pre-Backtest PASS Candidate Audit
| candidate | final_score | CVaR improve % | MDD improve % | stress improve | scenario reduction | return drag % | Sharpe improve % | DQ penalty | role |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 261240.KS + FXF | 0.846453 | 32.890087 | 32.00667 | 0.000834 | 0.113102 | 2.315407 | 41.051744 | 0.1 | hedge_candidate |
| 261240.KS + FXE | 0.841005 | 32.843408 | 30.331686 | 0.000844 | 0.11138 | 3.08928 | 39.468624 | 0.1 | hedge_candidate |
| 261240.KS + FXF | 0.740663 | 23.236836 | 21.65874 | 0.00035 | 0.067037 | 0.0 | 38.328442 | 0.1 | hedge_candidate |
| 261240.KS + FXE | 0.738949 | 23.199576 | 21.152113 | 0.000353 | 0.066463 | 0.0 | 37.848787 | 0.1 | hedge_candidate |
| 261240.KS + FXY | 0.738506 | 23.484334 | 20.706642 | 0.000361 | 0.067966 | 0.0 | 37.085106 | 0.1 | hedge_candidate |
| 261240.KS + BTAL | 0.73847 | 24.249067 | 26.228155 | 0.000257 | 0.066949 | 0.0 | 34.84182 | 0.1 | hedge_candidate |
| 261240.KS | 0.736239 | 23.394967 | 22.296942 | 0.000418 | 0.058672 | 0.0 | 38.754628 | 0.1 | hedge_candidate |

### Representative Pre-Backtest PASS Candidates by Bucket
| bucket | candidate | final_score | scenario reduction | return drag % | reason |
|---|---|---:|---:|---:|---|
| equity_etf|kr_etf | 261240.KS + BTAL | 0.73847 | 0.066949 | 0.0 | 핵심 취약점 직접 완화, Downside beta reduction, Sharpe 개선 / 달러강세/원화약세장, 중국·무역분절 충격장, 장기금리 부담장 기준 취약도를 낮추는 후보입니다. |
| fx_etf|kr_etf | 261240.KS + FXF | 0.846453 | 0.113102 | 2.315407 | 핵심 취약점 직접 완화, Stress 방어, Sharpe 개선 / 달러강세/원화약세장, 중국·무역분절 충격장, 장기금리 부담장 기준 취약도를 낮추는 후보입니다. |
| kr_etf | 261240.KS | 0.736239 | 0.058672 | 0.0 | 핵심 취약점 직접 완화, factor 집중 완화, MDD 개선 / 달러강세/원화약세장, 중국·무역분절 충격장, 장기금리 부담장 기준 취약도를 낮추는 후보입니다. |

### Examples
| recommendation_status | candidate | status | scenario_delta | gate_delta | reason |
|---|---|---|---:|---:|---|
| PASS_RECOMMEND | 261240.KS | PASS | -0.058672 | -0.040095 | DQ WARN non-blocking - 261240.KS: calendar_coverage_warn |
| PASS_RECOMMEND | 261240.KS + FXY | PASS | -0.067966 | -0.055396 | DQ WARN non-blocking - 261240.KS: calendar_coverage_warn; DQ WARN non-blocking - FXY: fx_missing_warn |
| PASS_RECOMMEND | 261240.KS + BTAL | PASS | -0.066949 | -0.08484 | DQ WARN non-blocking - 261240.KS: calendar_coverage_warn; DQ WARN non-blocking - BTAL: extreme_return_outlier_warn |
| PASS_RECOMMEND | 261240.KS + FXF | PASS | -0.067037 | -0.055396 | DQ WARN non-blocking - 261240.KS: calendar_coverage_warn; DQ WARN non-blocking - FXF: fx_missing_warn |
| PASS_RECOMMEND | 261240.KS + FXE | PASS | -0.066463 | -0.055396 | DQ WARN non-blocking - 261240.KS: calendar_coverage_warn; DQ WARN non-blocking - FXE: fx_missing_warn |
| PASS_RECOMMEND | 261240.KS + FXF | PASS | -0.113102 | -0.106045 | DQ WARN non-blocking - 261240.KS: calendar_coverage_warn; DQ WARN non-blocking - FXF: fx_missing_warn |
| PASS_RECOMMEND | 261240.KS + FXE | PASS | -0.11138 | -0.106045 | DQ WARN non-blocking - 261240.KS: calendar_coverage_warn; DQ WARN non-blocking - FXE: fx_missing_warn |
| REFERENCE_ONLY | FXY | PASS | -0.052572 | -0.0583 | annual return drag soft warning |
| REFERENCE_ONLY | FXF | PASS | -0.050247 | -0.0583 | annual return drag soft warning |
| REFERENCE_ONLY | FXE | PASS | -0.048813 | -0.0583 | annual return drag soft warning |
| REFERENCE_ONLY | 068270.KS | PASS | -0.014025 | -0.006078 | 068270.KS: 장세 해석용 자산으로 기본 헤지 후보에서 제외 |
| REFERENCE_ONLY | 017670.KS | PASS | -0.026266 | -0.007689 | 017670.KS: 장세 해석용 자산으로 기본 헤지 후보에서 제외 |
| REFERENCE_ONLY | 055550.KS | PASS | -0.010527 | -0.003916 | annual return drag soft warning; 055550.KS: 장세 해석용 자산으로 기본 헤지 후보에서 제외 |
| REFERENCE_ONLY | 011200.KS | PASS | -0.026368 | -0.008585 | Sharpe soft warning; annual return drag soft warning; 011200.KS: 장세 해석용 자산으로 기본 헤지 후보에서 제외 |
| REFERENCE_ONLY | 005490.KS | PASS | -0.020216 | -0.001745 | annual return drag soft warning; 005490.KS: 장세 해석용 자산으로 기본 헤지 후보에서 제외 |
| REFERENCE_ONLY | 114800.KS | PASS | -0.01296 | -0.012218 | annual return drag soft warning; 114800.KS: 리서치 전용 후보 |
| REFERENCE_ONLY | SH | PASS | -0.034921 | -0.048776 | annual return drag soft warning; SH: 리서치 전용 후보 |
| FAIL_GATE | 261240.KS | FAIL | -0.029336 | -0.020047 | Stress 개선 미달; beta/corr 감소 미달 |
| FAIL_GATE | BTAL | FAIL | -0.034509 | -0.048013 | Stress 개선 미달 |
| FAIL_GATE | 153130.KS | FAIL | -0.020701 | -0.01615 | Stress 개선 미달 |
| FAIL_GATE | 132030.KS | FAIL | -0.026094 | -0.007371 | Stress 개선 미달 |
| FAIL_GATE | SPLV | FAIL | -0.018242 | -0.039437 | Stress 개선 미달; beta/corr 감소 미달; downside beta 증가 하드 게이트 |
| FAIL_GATE | USMV | FAIL | -0.017507 | -0.039116 | Stress 개선 미달; beta/corr 감소 미달; downside beta 증가 하드 게이트 |
| FAIL_GATE | 207940.KS | FAIL | -0.013975 | -0.005508 | Stress 개선 미달 |
| FAIL_GATE | 105560.KS | FAIL | -0.008258 | -0.001345 | MDD 개선 미달; Stress 개선 미달 |
| FAIL_GATE | 032830.KS | FAIL | -0.007833 | 0.001774 | Stress 개선 미달; downside beta 증가 하드 게이트; active adverse scenario 민감도 증가 |
| FAIL_GATE | BTC-USD | FAIL | -0.04547 | -0.0583 | MDD 개선 미달; Stress 개선 미달; downside beta 증가 하드 게이트 |
| INSUFFICIENT_DATA | - | - | - | - | no rows in this run |
