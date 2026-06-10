# Formal Gate Audit

- candidate_rows: 59
- status_counts: `{"PASS_RECOMMEND": 0, "REFERENCE_ONLY": 13, "FAIL_GATE": 46, "INSUFFICIENT_DATA": 0}`

## Blocker Counts

- fail_gate: 46 - 하드 게이트 실패 - Candidate failed a hard gate. Next action: Do not promote until the failing gate is resolved.
- validation_not_eligible: 46 - validation not eligible - Candidate is not eligible for backtest validation. Next action: Keep blocked or rebuild the candidate with valid backtest inputs.
- liquidity_below_formal: 22 - 유동성 기준 미달 - 60-day ADV evidence is missing or below the formal threshold. Next action: Refresh ADV evidence or exclude the candidate from formal recommendations.
- reference_only: 13 - 참고 후보 - Candidate remains reference-only after formal gate checks. Next action: Use as research context, not an execution recommendation.
- return_drag_reference: 13 - 수익률 훼손 검토 필요 - Pre-backtest scoring kept the candidate reference-only because of return drag. Next action: Confirm risk reduction compensates for return drag before promotion.
- validation_insufficient: 9 - 검증 이력 부족 - Target stress validation has insufficient history. Next action: Add enough target stress validation history before formal promotion.
- bootstrap_not_robust: 3 - 부트스트랩 신뢰도 부족 - Target stress bootstrap confidence is not robust. Next action: Increase sample coverage or downgrade fragile candidates.
- cash_bootstrap_not_robust: 3 - 현금 기준 부트스트랩 부족 - Cash-baseline bootstrap confidence is not robust. Next action: Add stronger cash-baseline evidence before formal use.
- validation_thin: 3 - 검증 표본 부족 - Target stress validation sample is too small for formal use. Next action: Keep review-only until the stress sample is thick enough.
- cash_baseline_lag: 2 - 현금 기준 대비 열위 - The hedge lags a cash-only de-risking baseline in target stress. Next action: Improve the cash-baseline comparison or keep the candidate review-only.
- validation_skipped: 1 - validation skipped - Candidate was not selected for the bounded backtest run. Next action: Run a full backtest before any formal promotion.

## Liquidity Capacity Audit

- MISSING_ADV: 22
- ORDER_SIZE_ADV_USAGE_OK: 37

| candidate | source | status | ADV KRW | order KRW | ADV usage % | capacity status |
|---|---|---|---:|---:|---:|---|
| 005490.KS | one_to_one | FAIL_GATE |  | 230332.0 |  | MISSING_ADV |
| 032830.KS | one_to_one | FAIL_GATE |  | 230332.0 |  | MISSING_ADV |
| 207940.KS | one_to_one | FAIL_GATE |  | 230332.0 |  | MISSING_ADV |
| 261240.KS + FXE | multi | FAIL_GATE |  | 230332.0 |  | MISSING_ADV |
| 261240.KS + FXF | multi | FAIL_GATE |  | 230332.0 |  | MISSING_ADV |
| AAPL | one_to_one | FAIL_GATE |  | 230332.0 |  | MISSING_ADV |
| AMZN | one_to_one | FAIL_GATE |  | 230332.0 |  | MISSING_ADV |
| BTAL + FXE | multi | FAIL_GATE |  | 230332.0 |  | MISSING_ADV |
| BTAL + FXF | multi | FAIL_GATE |  | 230332.0 |  | MISSING_ADV |
| BTC-USD | one_to_one | FAIL_GATE |  | 230332.0 |  | MISSING_ADV |
| FXE + 132030.KS | multi | FAIL_GATE |  | 230332.0 |  | MISSING_ADV |
| FXE + 153130.KS | multi | FAIL_GATE |  | 230332.0 |  | MISSING_ADV |

## Highest-friction Candidates

| candidate | source | status | readiness | blockers | target eval | cash lags | robust/boot | min p | cash robust/boot | cash min p | min cash stress | reason |
|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| FXY | one_to_one | REFERENCE_ONLY | 51.1 | validation_thin, cash_baseline_lag, bootstrap_not_robust, cash_bootstrap_not_robust, return_drag_reference, reference_only | 1 | 1 | 0/1 | 0.825 | 0/1 | 0.055 | -0.006928 | target-scenario backtest has only 1 evaluated stress case; 표본 부족 |
| FXE | one_to_one | REFERENCE_ONLY | 52.7 | validation_thin, cash_baseline_lag, bootstrap_not_robust, cash_bootstrap_not_robust, return_drag_reference, reference_only | 1 | 1 | 0/1 | 0.875 | 0/1 | 0.135 | -0.004014 | target-scenario backtest has only 1 evaluated stress case; 표본 부족 |
| IAU | one_to_one | REFERENCE_ONLY | 71.3 | validation_thin, bootstrap_not_robust, cash_bootstrap_not_robust, return_drag_reference, reference_only | 1 | 0 | 0/1 | 0.065 | 0/1 | 0.85 | 0.018689 | target-scenario backtest has only 1 evaluated stress case; 표본 부족 |
| 005490.KS | one_to_one | FAIL_GATE | 10.0 | fail_gate, validation_not_eligible, liquidity_below_formal | 0 | 0 | 0/0 |  | 0/0 |  |  | candidate was not eligible for the bounded scenario backtest run |
| 032830.KS | one_to_one | FAIL_GATE | 10.0 | fail_gate, validation_not_eligible, liquidity_below_formal | 0 | 0 | 0/0 |  | 0/0 |  |  | candidate was not eligible for the bounded scenario backtest run |
| 207940.KS | one_to_one | FAIL_GATE | 10.0 | fail_gate, validation_not_eligible, liquidity_below_formal | 0 | 0 | 0/0 |  | 0/0 |  |  | candidate was not eligible for the bounded scenario backtest run |
| 261240.KS + FXE | multi | FAIL_GATE | 10.0 | fail_gate, validation_not_eligible, liquidity_below_formal | 0 | 0 | 0/0 |  | 0/0 |  |  | candidate was not eligible for the bounded scenario backtest run |
| 261240.KS + FXF | multi | FAIL_GATE | 10.0 | fail_gate, validation_not_eligible, liquidity_below_formal | 0 | 0 | 0/0 |  | 0/0 |  |  | candidate was not eligible for the bounded scenario backtest run |
| AAPL | one_to_one | FAIL_GATE | 10.0 | fail_gate, validation_not_eligible, liquidity_below_formal | 0 | 0 | 0/0 |  | 0/0 |  |  | candidate was not eligible for the bounded scenario backtest run |
| AMZN | one_to_one | FAIL_GATE | 10.0 | fail_gate, validation_not_eligible, liquidity_below_formal | 0 | 0 | 0/0 |  | 0/0 |  |  | candidate was not eligible for the bounded scenario backtest run |
| BTAL + FXE | multi | FAIL_GATE | 10.0 | fail_gate, validation_not_eligible, liquidity_below_formal | 0 | 0 | 0/0 |  | 0/0 |  |  | candidate was not eligible for the bounded scenario backtest run |
| BTAL + FXF | multi | FAIL_GATE | 10.0 | fail_gate, validation_not_eligible, liquidity_below_formal | 0 | 0 | 0/0 |  | 0/0 |  |  | candidate was not eligible for the bounded scenario backtest run |

## Closest Formal Near-misses

| candidate | source | status | readiness | blockers | target eval | cash lags | robust/boot | min p | cash robust/boot | cash min p | avg cash stress | reason |
|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| IAU | one_to_one | REFERENCE_ONLY | 71.3 | validation_thin, bootstrap_not_robust, cash_bootstrap_not_robust, return_drag_reference, reference_only | 1 | 0 | 0/1 | 0.065 | 0/1 | 0.85 | 0.018689 | target-scenario backtest has only 1 evaluated stress case; 표본 부족 |
| FXE | one_to_one | REFERENCE_ONLY | 52.7 | validation_thin, cash_baseline_lag, bootstrap_not_robust, cash_bootstrap_not_robust, return_drag_reference, reference_only | 1 | 1 | 0/1 | 0.875 | 0/1 | 0.135 | -0.004014 | target-scenario backtest has only 1 evaluated stress case; 표본 부족 |
| FXY | one_to_one | REFERENCE_ONLY | 51.1 | validation_thin, cash_baseline_lag, bootstrap_not_robust, cash_bootstrap_not_robust, return_drag_reference, reference_only | 1 | 1 | 0/1 | 0.825 | 0/1 | 0.055 | -0.006928 | target-scenario backtest has only 1 evaluated stress case; 표본 부족 |
| 017670.KS | one_to_one | REFERENCE_ONLY | 40.0 | validation_insufficient, reference_only | 0 | 0 | 0/0 |  | 0/0 |  |  | target-scenario historical validation has insufficient history; 검증 부족 |
| 055550.KS | one_to_one | REFERENCE_ONLY | 40.0 | validation_insufficient, reference_only | 0 | 0 | 0/0 |  | 0/0 |  |  | target-scenario historical validation has insufficient history; 검증 부족 |
| 068270.KS | one_to_one | REFERENCE_ONLY | 40.0 | validation_insufficient, reference_only | 0 | 0 | 0/0 |  | 0/0 |  |  | target-scenario historical validation has insufficient history; 검증 부족 |
| 011200.KS | one_to_one | REFERENCE_ONLY | 40.0 | validation_insufficient, return_drag_reference, reference_only | 0 | 0 | 0/0 |  | 0/0 |  |  | target-scenario historical validation has insufficient history; 검증 부족 |
| 105560.KS | one_to_one | REFERENCE_ONLY | 40.0 | validation_insufficient, return_drag_reference, reference_only | 0 | 0 | 0/0 |  | 0/0 |  |  | target-scenario historical validation has insufficient history; 검증 부족 |
| 114800.KS | one_to_one | REFERENCE_ONLY | 40.0 | validation_insufficient, return_drag_reference, reference_only | 0 | 0 | 0/0 |  | 0/0 |  |  | target-scenario historical validation has insufficient history; 검증 부족 |
| FXF | one_to_one | REFERENCE_ONLY | 40.0 | validation_insufficient, return_drag_reference, reference_only | 0 | 0 | 0/0 |  | 0/0 |  |  | target-scenario historical validation has insufficient history; 검증 부족 |
| PSQ | one_to_one | REFERENCE_ONLY | 40.0 | validation_insufficient, return_drag_reference, reference_only | 0 | 0 | 0/0 |  | 0/0 |  |  | target-scenario historical validation has insufficient history; 검증 부족 |
| SH | one_to_one | REFERENCE_ONLY | 40.0 | validation_insufficient, return_drag_reference, reference_only | 0 | 0 | 0/0 |  | 0/0 |  |  | target-scenario historical validation has insufficient history; 검증 부족 |
