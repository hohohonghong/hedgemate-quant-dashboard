# HedgeMate Pre-Backtest Candidate QA

- run_id: 20260610T191953943306-da0898b3
- scope: pre_backtest_candidate_screen
- formal_recommendation_gate: post_backtest_required
- note: PASS_RECOMMEND below is a pre-backtest candidate label only; it must not be shown as a formal recommendation until the backtest gate has run.
- 목적: 추천/참고/실패 상태를 사유별로 검증하기 위한 QA 요약입니다.

## Portfolio

### Counts
- scope: pre_backtest_candidate_screen; PASS_RECOMMEND in this report is a model candidate label, not a formal recommendation. Use the post-backtest gated QA/report for user-facing recommendation status.
- status: FAIL 18, PASS 10
- recommendation_status: PASS_RECOMMEND 0, REFERENCE_ONLY 10, FAIL_GATE 18, INSUFFICIENT_DATA 0
- candidate_role: UNKNOWN 16, benchmark_candidate 2, diagnostic_only 4, hedge_candidate 1, mixed_candidate_roles 4, research_only 1
- DQ WARN affected rows: 12
- DQ blocking affected rows: 0
- DQ non-blocking warning rows: 12

### Status Bucket Summary (Pre-Backtest Candidate Labels)
- PASS_RECOMMEND: 0
- REFERENCE_ONLY: 10
- FAIL_GATE: 18
- INSUFFICIENT_DATA: 0

### Top Gate Fail Reasons
- FAIL: 예산 부족 - 005380.KS 1주 매수 불가: 5
- FAIL: 예산 부족 - 000270.KS 1주 매수 불가: 4
- FAIL: 예산 부족 - 105560.KS 1주 매수 불가: 4
- 연환산 수익률 훼손 하드 게이트: 2
- Sharpe 악화 하드 게이트: 1
- FAIL: 예산 부족 - 000810.KS 1주 매수 불가: 1
- FAIL: 예산 부족 - 032830.KS 1주 매수 불가: 1
- FAIL: 예산 부족 - 066570.KS 1주 매수 불가: 1

### Top Reference Reasons
- annual return drag soft warning: 6
- Sharpe soft warning: 5
- 153130.KS: 범용 방어 benchmark입니다: 1
- 132030.KS: 범용 방어 benchmark입니다: 1
- 017670.KS: 장세 해석용 자산으로 기본 헤지 후보에서 제외: 1
- 000270.KS: 장세 해석용 자산으로 기본 헤지 후보에서 제외: 1
- 105560.KS: 장세 해석용 자산으로 기본 헤지 후보에서 제외: 1
- 055550.KS: 장세 해석용 자산으로 기본 헤지 후보에서 제외: 1
- 261240.KS: 핵심 취약점 직접 완화 후보 | 017670.KS: 장세 해석용 자산으로 기본 헤지 후보에서 제외: 1
- 153130.KS: 범용 방어 benchmark입니다 | 017670.KS: 장세 해석용 자산으로 기본 헤지 후보에서 제외: 1

### Top DQ Non-Blocking Warnings
- DQ WARN non-blocking - 017670.KS: calendar_coverage_warn: 5
- DQ WARN non-blocking - 261240.KS: calendar_coverage_warn: 2
- DQ WARN non-blocking - 153130.KS: calendar_coverage_warn: 2
- DQ WARN non-blocking - 132030.KS: calendar_coverage_warn: 2
- DQ WARN non-blocking - 114800.KS: calendar_coverage_warn: 2
- DQ WARN non-blocking - 000270.KS: calendar_coverage_warn: 1
- DQ WARN non-blocking - 105560.KS: calendar_coverage_warn: 1
- DQ WARN non-blocking - 055550.KS: calendar_coverage_warn: 1

### Top Pre-Backtest PASS Candidate Audit
- none

### Representative Pre-Backtest PASS Candidates by Bucket
- none

### Examples
| recommendation_status | candidate | status | scenario_delta | gate_delta | reason |
|---|---|---|---:|---:|---|
| PASS_RECOMMEND | - | - | - | - | no rows in this run |
| REFERENCE_ONLY | 261240.KS | PASS | -0.032759 | -0.035414 | annual return drag soft warning |
| REFERENCE_ONLY | 153130.KS | PASS | -0.032023 | -0.027553 | Sharpe soft warning; annual return drag soft warning; 153130.KS: 범용 방어 benchmark입니다 |
| REFERENCE_ONLY | 132030.KS | PASS | -0.030691 | -0.031168 | Sharpe soft warning; annual return drag soft warning; 132030.KS: 범용 방어 benchmark입니다 |
| REFERENCE_ONLY | 017670.KS | PASS | -0.033511 | -0.03212 | 017670.KS: 장세 해석용 자산으로 기본 헤지 후보에서 제외 |
| REFERENCE_ONLY | 000270.KS | PASS | -0.017323 | -0.019468 | 000270.KS: 장세 해석용 자산으로 기본 헤지 후보에서 제외 |
| REFERENCE_ONLY | 105560.KS | PASS | -0.012814 | -0.011818 | 105560.KS: 장세 해석용 자산으로 기본 헤지 후보에서 제외 |
| REFERENCE_ONLY | 055550.KS | PASS | -0.016343 | -0.014927 | 055550.KS: 장세 해석용 자산으로 기본 헤지 후보에서 제외 |
| REFERENCE_ONLY | 261240.KS + 017670.KS | PASS | -0.033135 | -0.033767 | annual return drag soft warning; 261240.KS: 핵심 취약점 직접 완화 후보 / 017670.KS: 장세 해석용 자산으로 기본 헤지 후보에서 제외 |
| REFERENCE_ONLY | 153130.KS + 017670.KS | PASS | -0.032766 | -0.029832 | Sharpe soft warning; annual return drag soft warning; 153130.KS: 범용 방어 benchmark입니다 / 017670.KS: 장세 해석용 자산으로 기본 헤지 후보에서 제외 |
| REFERENCE_ONLY | 132030.KS + 017670.KS | PASS | -0.030542 | -0.030057 | Sharpe soft warning; annual return drag soft warning; 132030.KS: 범용 방어 benchmark입니다 / 017670.KS: 장세 해석용 자산으로 기본 헤지 후보에서 제외 |
| FAIL_GATE | 114800.KS | FAIL | -0.025489 | -0.018822 | Sharpe 악화 하드 게이트; 연환산 수익률 훼손 하드 게이트 |
| FAIL_GATE | 005380.KS | FAIL |  |  | FAIL: 예산 부족 - 005380.KS 1주 매수 불가 |
| FAIL_GATE | 000810.KS | FAIL |  |  | FAIL: 예산 부족 - 000810.KS 1주 매수 불가 |
| FAIL_GATE | 032830.KS | FAIL |  |  | FAIL: 예산 부족 - 032830.KS 1주 매수 불가 |
| FAIL_GATE | 066570.KS | FAIL |  |  | FAIL: 예산 부족 - 066570.KS 1주 매수 불가 |
| FAIL_GATE | 261240.KS + 005380.KS | FAIL |  |  | FAIL: 예산 부족 - 005380.KS 1주 매수 불가 |
| FAIL_GATE | 261240.KS + 000270.KS | FAIL |  |  | FAIL: 예산 부족 - 000270.KS 1주 매수 불가 |
| FAIL_GATE | 261240.KS + 105560.KS | FAIL |  |  | FAIL: 예산 부족 - 105560.KS 1주 매수 불가 |
| FAIL_GATE | 153130.KS + 005380.KS | FAIL |  |  | FAIL: 예산 부족 - 005380.KS 1주 매수 불가 |
| FAIL_GATE | 153130.KS + 000270.KS | FAIL |  |  | FAIL: 예산 부족 - 000270.KS 1주 매수 불가 |
| INSUFFICIENT_DATA | - | - | - | - | no rows in this run |
