# Formal Gate Audit

- candidate_rows: 28
- status_counts: `{"PASS_RECOMMEND": 0, "REFERENCE_ONLY": 10, "FAIL_GATE": 18, "INSUFFICIENT_DATA": 0}`

## Blocker Counts

- fail_gate: 18 - 하드 게이트 실패 - Candidate failed a hard gate. Next action: Do not promote until the failing gate is resolved.
- validation_not_eligible: 18 - validation not eligible - Candidate is not eligible for backtest validation. Next action: Keep blocked or rebuild the candidate with valid backtest inputs.
- liquidity_below_formal: 16 - 유동성 기준 미달 - 60-day ADV evidence is missing or below the formal threshold. Next action: Refresh ADV evidence or exclude the candidate from formal recommendations.
- reference_only: 10 - 참고 후보 - Candidate remains reference-only after formal gate checks. Next action: Use as research context, not an execution recommendation.
- validation_insufficient: 8 - 검증 이력 부족 - Target stress validation has insufficient history. Next action: Add enough target stress validation history before formal promotion.
- return_drag_reference: 6 - 수익률 훼손 검토 필요 - Pre-backtest scoring kept the candidate reference-only because of return drag. Next action: Confirm risk reduction compensates for return drag before promotion.
- bootstrap_not_robust: 2 - 부트스트랩 신뢰도 부족 - Target stress bootstrap confidence is not robust. Next action: Increase sample coverage or downgrade fragile candidates.
- cash_bootstrap_not_robust: 2 - 현금 기준 부트스트랩 부족 - Cash-baseline bootstrap confidence is not robust. Next action: Add stronger cash-baseline evidence before formal use.
- validation_thin: 2 - 검증 표본 부족 - Target stress validation sample is too small for formal use. Next action: Keep review-only until the stress sample is thick enough.

## Liquidity Capacity Audit

- MISSING_ADV: 16
- ORDER_SIZE_ADV_USAGE_OK: 12

| candidate | source | status | ADV KRW | order KRW | ADV usage % | capacity status |
|---|---|---|---:|---:|---:|---|
| 000810.KS | one_to_one | FAIL_GATE |  | 230332.0 |  | MISSING_ADV |
| 005380.KS | one_to_one | FAIL_GATE |  | 230332.0 |  | MISSING_ADV |
| 032830.KS | one_to_one | FAIL_GATE |  | 230332.0 |  | MISSING_ADV |
| 066570.KS | one_to_one | FAIL_GATE |  | 230332.0 |  | MISSING_ADV |
| 114800.KS + 000270.KS | multi | FAIL_GATE |  | 230332.0 |  | MISSING_ADV |
| 114800.KS + 005380.KS | multi | FAIL_GATE |  | 230332.0 |  | MISSING_ADV |
| 114800.KS + 105560.KS | multi | FAIL_GATE |  | 230332.0 |  | MISSING_ADV |
| 132030.KS + 000270.KS | multi | FAIL_GATE |  | 230332.0 |  | MISSING_ADV |
| 132030.KS + 005380.KS | multi | FAIL_GATE |  | 230332.0 |  | MISSING_ADV |
| 132030.KS + 105560.KS | multi | FAIL_GATE |  | 230332.0 |  | MISSING_ADV |
| 153130.KS + 000270.KS | multi | FAIL_GATE |  | 230332.0 |  | MISSING_ADV |
| 153130.KS + 005380.KS | multi | FAIL_GATE |  | 230332.0 |  | MISSING_ADV |

## Highest-friction Candidates

| candidate | source | status | readiness | blockers | target eval | cash lags | robust/boot | min p | cash robust/boot | cash min p | min cash stress | reason |
|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| 261240.KS + 017670.KS | multi | REFERENCE_ONLY | 82.1 | validation_thin, bootstrap_not_robust, cash_bootstrap_not_robust, return_drag_reference, reference_only | 1 | 0 | 0/1 | 0.95 | 0/1 | 0.605 | 0.001086 | target-scenario backtest has only 1 evaluated stress case; 표본 부족 |
| 261240.KS | one_to_one | REFERENCE_ONLY | 89.0 | validation_thin, bootstrap_not_robust, cash_bootstrap_not_robust, return_drag_reference, reference_only | 1 | 0 | 0/1 | 0.95 | 0/1 | 0.97 | 0.010173 | target-scenario backtest has only 1 evaluated stress case; 표본 부족 |
| 000810.KS | one_to_one | FAIL_GATE | 10.0 | fail_gate, validation_not_eligible, liquidity_below_formal | 0 | 0 | 0/0 |  | 0/0 |  |  | candidate was not eligible for the bounded scenario backtest run |
| 005380.KS | one_to_one | FAIL_GATE | 10.0 | fail_gate, validation_not_eligible, liquidity_below_formal | 0 | 0 | 0/0 |  | 0/0 |  |  | candidate was not eligible for the bounded scenario backtest run |
| 032830.KS | one_to_one | FAIL_GATE | 10.0 | fail_gate, validation_not_eligible, liquidity_below_formal | 0 | 0 | 0/0 |  | 0/0 |  |  | candidate was not eligible for the bounded scenario backtest run |
| 066570.KS | one_to_one | FAIL_GATE | 10.0 | fail_gate, validation_not_eligible, liquidity_below_formal | 0 | 0 | 0/0 |  | 0/0 |  |  | candidate was not eligible for the bounded scenario backtest run |
| 114800.KS + 000270.KS | multi | FAIL_GATE | 10.0 | fail_gate, validation_not_eligible, liquidity_below_formal | 0 | 0 | 0/0 |  | 0/0 |  |  | candidate was not eligible for the bounded scenario backtest run |
| 114800.KS + 005380.KS | multi | FAIL_GATE | 10.0 | fail_gate, validation_not_eligible, liquidity_below_formal | 0 | 0 | 0/0 |  | 0/0 |  |  | candidate was not eligible for the bounded scenario backtest run |
| 114800.KS + 105560.KS | multi | FAIL_GATE | 10.0 | fail_gate, validation_not_eligible, liquidity_below_formal | 0 | 0 | 0/0 |  | 0/0 |  |  | candidate was not eligible for the bounded scenario backtest run |
| 132030.KS + 000270.KS | multi | FAIL_GATE | 10.0 | fail_gate, validation_not_eligible, liquidity_below_formal | 0 | 0 | 0/0 |  | 0/0 |  |  | candidate was not eligible for the bounded scenario backtest run |
| 132030.KS + 005380.KS | multi | FAIL_GATE | 10.0 | fail_gate, validation_not_eligible, liquidity_below_formal | 0 | 0 | 0/0 |  | 0/0 |  |  | candidate was not eligible for the bounded scenario backtest run |
| 132030.KS + 105560.KS | multi | FAIL_GATE | 10.0 | fail_gate, validation_not_eligible, liquidity_below_formal | 0 | 0 | 0/0 |  | 0/0 |  |  | candidate was not eligible for the bounded scenario backtest run |

## Closest Formal Near-misses

| candidate | source | status | readiness | blockers | target eval | cash lags | robust/boot | min p | cash robust/boot | cash min p | avg cash stress | reason |
|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| 261240.KS | one_to_one | REFERENCE_ONLY | 89.0 | validation_thin, bootstrap_not_robust, cash_bootstrap_not_robust, return_drag_reference, reference_only | 1 | 0 | 0/1 | 0.95 | 0/1 | 0.97 | 0.010173 | target-scenario backtest has only 1 evaluated stress case; 표본 부족 |
| 261240.KS + 017670.KS | multi | REFERENCE_ONLY | 82.1 | validation_thin, bootstrap_not_robust, cash_bootstrap_not_robust, return_drag_reference, reference_only | 1 | 0 | 0/1 | 0.95 | 0/1 | 0.605 | 0.001086 | target-scenario backtest has only 1 evaluated stress case; 표본 부족 |
| 000270.KS | one_to_one | REFERENCE_ONLY | 40.0 | validation_insufficient, reference_only | 0 | 0 | 0/0 |  | 0/0 |  |  | target-scenario historical validation has insufficient history; 검증 부족 |
| 017670.KS | one_to_one | REFERENCE_ONLY | 40.0 | validation_insufficient, reference_only | 0 | 0 | 0/0 |  | 0/0 |  |  | target-scenario historical validation has insufficient history; 검증 부족 |
| 055550.KS | one_to_one | REFERENCE_ONLY | 40.0 | validation_insufficient, reference_only | 0 | 0 | 0/0 |  | 0/0 |  |  | target-scenario historical validation has insufficient history; 검증 부족 |
| 105560.KS | one_to_one | REFERENCE_ONLY | 40.0 | validation_insufficient, reference_only | 0 | 0 | 0/0 |  | 0/0 |  |  | target-scenario historical validation has insufficient history; 검증 부족 |
| 132030.KS | one_to_one | REFERENCE_ONLY | 40.0 | validation_insufficient, return_drag_reference, reference_only | 0 | 0 | 0/0 |  | 0/0 |  |  | target-scenario historical validation has insufficient history; 검증 부족 |
| 132030.KS + 017670.KS | multi | REFERENCE_ONLY | 40.0 | validation_insufficient, return_drag_reference, reference_only | 0 | 0 | 0/0 |  | 0/0 |  |  | target-scenario historical validation has insufficient history; 검증 부족 |
| 153130.KS | one_to_one | REFERENCE_ONLY | 40.0 | validation_insufficient, return_drag_reference, reference_only | 0 | 0 | 0/0 |  | 0/0 |  |  | target-scenario historical validation has insufficient history; 검증 부족 |
| 153130.KS + 017670.KS | multi | REFERENCE_ONLY | 40.0 | validation_insufficient, return_drag_reference, reference_only | 0 | 0 | 0/0 |  | 0/0 |  |  | target-scenario historical validation has insufficient history; 검증 부족 |
