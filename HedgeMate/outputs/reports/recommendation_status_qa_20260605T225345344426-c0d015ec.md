# HedgeMate Pre-Backtest Candidate QA

- run_id: 20260605T225345344426-c0d015ec
- scope: pre_backtest_candidate_screen
- formal_recommendation_gate: post_backtest_required
- note: PASS_RECOMMEND below is a pre-backtest candidate label only; it must not be shown as a formal recommendation until the backtest gate has run.
- 목적: 추천/참고/실패 상태를 사유별로 검증하기 위한 QA 요약입니다.

## Portfolio

### Counts
- scope: pre_backtest_candidate_screen; PASS_RECOMMEND in this report is a model candidate label, not a formal recommendation. Use the post-backtest gated QA/report for user-facing recommendation status.
- status: FAIL 46, PASS 13
- recommendation_status: PASS_RECOMMEND 0, REFERENCE_ONLY 13, FAIL_GATE 46, INSUFFICIENT_DATA 0
- candidate_role: UNKNOWN 22, benchmark_candidate 3, conditional_candidate 2, diagnostic_only 9, hedge_candidate 14, mixed_candidate_roles 6, research_only 3
- DQ WARN affected rows: 33
- DQ blocking affected rows: 0
- DQ non-blocking warning rows: 33

### Status Bucket Summary (Pre-Backtest Candidate Labels)
- PASS_RECOMMEND: 0
- REFERENCE_ONLY: 13
- FAIL_GATE: 46
- INSUFFICIENT_DATA: 0

### Top Gate Fail Reasons
- Stress 개선 미달: 19
- beta/corr 감소 미달: 19
- downside beta 증가 하드 게이트: 12
- FAIL: 예산 부족 - FXF 1주 매수 불가: 5
- FAIL: 예산 부족 - FXE 1주 매수 불가: 5
- FAIL: 예산 부족 - 207940.KS 1주 매수 불가: 1
- FAIL: 예산 부족 - 005490.KS 1주 매수 불가: 1
- FAIL: 예산 부족 - 032830.KS 1주 매수 불가: 1
- FAIL: 예산 부족 - BTC-USD 1주 매수 불가: 1
- FAIL: 예산 부족 - ORCL 1주 매수 불가: 1

### Top Reference Reasons
- annual return drag soft warning: 13
- 068270.KS: 장세 해석용 자산으로 기본 헤지 후보에서 제외: 1
- 017670.KS: 장세 해석용 자산으로 기본 헤지 후보에서 제외: 1
- 055550.KS: 장세 해석용 자산으로 기본 헤지 후보에서 제외: 1
- Sharpe soft warning: 1
- 011200.KS: 장세 해석용 자산으로 기본 헤지 후보에서 제외: 1
- 114800.KS: 리서치 전용 후보: 1
- 105560.KS: 장세 해석용 자산으로 기본 헤지 후보에서 제외: 1
- SH: 리서치 전용 후보: 1
- PSQ: 리서치 전용 후보: 1

### Top DQ Non-Blocking Warnings
- DQ WARN non-blocking - FXY: fx_missing_warn: 6
- DQ WARN non-blocking - BTAL: extreme_return_outlier_warn: 5
- DQ WARN non-blocking - 261240.KS: calendar_coverage_warn: 4
- DQ WARN non-blocking - 153130.KS: calendar_coverage_warn: 4
- DQ WARN non-blocking - 132030.KS: calendar_coverage_warn: 4
- DQ WARN non-blocking - FXF: fx_missing_warn: 1
- DQ WARN non-blocking - FXE: fx_missing_warn: 1
- DQ WARN non-blocking - 068270.KS: calendar_coverage_warn: 1
- DQ WARN non-blocking - 017670.KS: calendar_coverage_warn: 1
- DQ WARN non-blocking - 055550.KS: calendar_coverage_warn: 1

### Top Pre-Backtest PASS Candidate Audit
- none

### Representative Pre-Backtest PASS Candidates by Bucket
- none

### Examples
| recommendation_status | candidate | status | scenario_delta | gate_delta | reason |
|---|---|---|---:|---:|---|
| PASS_RECOMMEND | - | - | - | - | no rows in this run |
| REFERENCE_ONLY | FXY | PASS | -0.034578 | -0.038852 | annual return drag soft warning |
| REFERENCE_ONLY | FXF | PASS | -0.032237 | -0.037908 | annual return drag soft warning |
| REFERENCE_ONLY | FXE | PASS | -0.03011 | -0.036453 | annual return drag soft warning |
| REFERENCE_ONLY | 068270.KS | PASS | -0.009128 | -0.00433 | 068270.KS: 장세 해석용 자산으로 기본 헤지 후보에서 제외 |
| REFERENCE_ONLY | 017670.KS | PASS | -0.020982 | -0.006564 | 017670.KS: 장세 해석용 자산으로 기본 헤지 후보에서 제외 |
| REFERENCE_ONLY | 055550.KS | PASS | -0.007647 | -0.003253 | 055550.KS: 장세 해석용 자산으로 기본 헤지 후보에서 제외 |
| REFERENCE_ONLY | 011200.KS | PASS | -0.020889 | -0.007227 | Sharpe soft warning; annual return drag soft warning; 011200.KS: 장세 해석용 자산으로 기본 헤지 후보에서 제외 |
| REFERENCE_ONLY | 114800.KS | PASS | -0.010739 | -0.010731 | annual return drag soft warning; 114800.KS: 리서치 전용 후보 |
| REFERENCE_ONLY | 105560.KS | PASS | -0.004947 | -0.001106 | annual return drag soft warning; 105560.KS: 장세 해석용 자산으로 기본 헤지 후보에서 제외 |
| REFERENCE_ONLY | SH | PASS | -0.025994 | -0.036946 | annual return drag soft warning; SH: 리서치 전용 후보 |
| FAIL_GATE | 261240.KS | FAIL | -0.02364 | -0.016675 | Stress 개선 미달; beta/corr 감소 미달 |
| FAIL_GATE | BTAL | FAIL | -0.028939 | -0.040981 | Stress 개선 미달 |
| FAIL_GATE | 153130.KS | FAIL | -0.017097 | -0.013897 | Stress 개선 미달; beta/corr 감소 미달; downside beta 증가 하드 게이트 |
| FAIL_GATE | 132030.KS | FAIL | -0.021668 | -0.006557 | Stress 개선 미달; downside beta 증가 하드 게이트 |
| FAIL_GATE | SPLV | FAIL | -0.014733 | -0.032735 | Stress 개선 미달; beta/corr 감소 미달; downside beta 증가 하드 게이트 |
| FAIL_GATE | USMV | FAIL | -0.009694 | -0.022279 | Stress 개선 미달; beta/corr 감소 미달; downside beta 증가 하드 게이트 |
| FAIL_GATE | 207940.KS | FAIL |  |  | FAIL: 예산 부족 - 207940.KS 1주 매수 불가 |
| FAIL_GATE | 005490.KS | FAIL |  |  | FAIL: 예산 부족 - 005490.KS 1주 매수 불가 |
| FAIL_GATE | 032830.KS | FAIL |  |  | FAIL: 예산 부족 - 032830.KS 1주 매수 불가 |
| FAIL_GATE | BTC-USD | FAIL |  |  | FAIL: 예산 부족 - BTC-USD 1주 매수 불가 |
| INSUFFICIENT_DATA | - | - | - | - | no rows in this run |
