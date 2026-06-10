# Formal Gate Audit

- candidate_rows: 177
- status_counts: `{"PASS_RECOMMEND": 0, "REFERENCE_ONLY": 44, "FAIL_GATE": 133, "INSUFFICIENT_DATA": 0}`

## Blocker Counts

- fail_gate: 133 - 하드 게이트 실패 - Candidate failed a hard gate. Next action: Do not promote until the failing gate is resolved.
- validation_not_eligible: 133 - validation not eligible - Candidate is not eligible for backtest validation. Next action: Keep blocked or rebuild the candidate with valid backtest inputs.
- liquidity_below_formal: 119 - 유동성 기준 미달 - 60-day ADV evidence is missing or below the formal threshold. Next action: Refresh ADV evidence or exclude the candidate from formal recommendations.
- return_drag_reference: 55 - 수익률 훼손 검토 필요 - Pre-backtest scoring kept the candidate reference-only because of return drag. Next action: Confirm risk reduction compensates for return drag before promotion.
- reference_only: 44 - 참고 후보 - Candidate remains reference-only after formal gate checks. Next action: Use as research context, not an execution recommendation.
- bootstrap_not_robust: 23 - 부트스트랩 신뢰도 부족 - Target stress bootstrap confidence is not robust. Next action: Increase sample coverage or downgrade fragile candidates.
- validation_thin: 23 - 검증 표본 부족 - Target stress validation sample is too small for formal use. Next action: Keep review-only until the stress sample is thick enough.
- cash_bootstrap_not_robust: 22 - 현금 기준 부트스트랩 부족 - Cash-baseline bootstrap confidence is not robust. Next action: Add stronger cash-baseline evidence before formal use.
- validation_insufficient: 21 - 검증 이력 부족 - Target stress validation has insufficient history. Next action: Add enough target stress validation history before formal promotion.
- cash_baseline_lag: 9 - 현금 기준 대비 열위 - The hedge lags a cash-only de-risking baseline in target stress. Next action: Improve the cash-baseline comparison or keep the candidate review-only.

## Liquidity Capacity Audit

- BELOW_FORMAL_ADV_FLOOR_NO_ORDER_SIZE: 81
- MISSING_ADV: 38
- OK_ADV_FLOOR_NO_ORDER_SIZE: 58

| candidate | source | status | ADV KRW | order KRW | ADV usage % | capacity status |
|---|---|---|---:|---:|---:|---|
| 011200.KS | one_to_one | REFERENCE_ONLY | 31112268062.333332 |  |  | BELOW_FORMAL_ADV_FLOOR_NO_ORDER_SIZE |
| 011200.KS | one_to_one | FAIL_GATE | 31112268062.333332 |  |  | BELOW_FORMAL_ADV_FLOOR_NO_ORDER_SIZE |
| 132030.KS | one_to_one | REFERENCE_ONLY | 5987808271.5 |  |  | BELOW_FORMAL_ADV_FLOOR_NO_ORDER_SIZE |
| 132030.KS | one_to_one | FAIL_GATE | 5987808271.5 |  |  | BELOW_FORMAL_ADV_FLOOR_NO_ORDER_SIZE |
| 132030.KS + SPLV | multi | REFERENCE_ONLY | 5987808271.5 |  |  | BELOW_FORMAL_ADV_FLOOR_NO_ORDER_SIZE |
| 132030.KS + SPLV | multi | REFERENCE_ONLY | 5987808271.5 |  |  | BELOW_FORMAL_ADV_FLOOR_NO_ORDER_SIZE |
| 132030.KS + SPLV | multi | FAIL_GATE | 5987808271.5 |  |  | BELOW_FORMAL_ADV_FLOOR_NO_ORDER_SIZE |
| 153130.KS | one_to_one | FAIL_GATE | 4021733917.271337 |  |  | BELOW_FORMAL_ADV_FLOOR_NO_ORDER_SIZE |
| 153130.KS | one_to_one | FAIL_GATE | 4021733917.271337 |  |  | BELOW_FORMAL_ADV_FLOOR_NO_ORDER_SIZE |
| 153130.KS + SPLV | multi | FAIL_GATE | 4021733917.271337 |  |  | BELOW_FORMAL_ADV_FLOOR_NO_ORDER_SIZE |
| 153130.KS + SPLV | multi | FAIL_GATE | 4021733917.271337 |  |  | BELOW_FORMAL_ADV_FLOOR_NO_ORDER_SIZE |
| 153130.KS + SPLV | multi | FAIL_GATE | 4021733917.271337 |  |  | BELOW_FORMAL_ADV_FLOOR_NO_ORDER_SIZE |

## Highest-friction Candidates

| candidate | source | status | readiness | blockers | target eval | cash lags | robust/boot | min p | cash robust/boot | cash min p | min cash stress | reason |
|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| FXY + 132030.KS | multi | REFERENCE_ONLY | 30.3 | validation_thin, cash_baseline_lag, bootstrap_not_robust, cash_bootstrap_not_robust, liquidity_below_formal, return_drag_reference, reference_only | 1 | 1 | 0/1 | 0.79 | 0/1 | 0.015 | -0.035241 | target-scenario backtest has only 1 evaluated stress case; 표본 부족 |
| FXY + 132030.KS | multi | REFERENCE_ONLY | 30.7 | validation_thin, cash_baseline_lag, bootstrap_not_robust, cash_bootstrap_not_robust, liquidity_below_formal, return_drag_reference, reference_only | 1 | 1 | 0/1 | 0.73 | 0/1 | 0.035 | -0.021822 | target-scenario backtest has only 1 evaluated stress case; 표본 부족 |
| FXY | one_to_one | REFERENCE_ONLY | 31.2 | validation_thin, cash_baseline_lag, bootstrap_not_robust, cash_bootstrap_not_robust, liquidity_below_formal, return_drag_reference, reference_only | 1 | 1 | 0/1 | 0.725 | 0/1 | 0.06 | -0.01065 | target-scenario backtest has only 1 evaluated stress case; 표본 부족 |
| FXE + 132030.KS | multi | REFERENCE_ONLY | 31.4 | validation_thin, cash_baseline_lag, bootstrap_not_robust, cash_bootstrap_not_robust, liquidity_below_formal, return_drag_reference, reference_only | 1 | 1 | 0/1 | 0.79 | 0/1 | 0.07 | -0.027915 | target-scenario backtest has only 1 evaluated stress case; 표본 부족 |
| FXY | one_to_one | REFERENCE_ONLY | 31.4 | validation_thin, cash_baseline_lag, bootstrap_not_robust, cash_bootstrap_not_robust, liquidity_below_formal, return_drag_reference, reference_only | 1 | 1 | 0/1 | 0.775 | 0/1 | 0.07 | -0.020906 | target-scenario backtest has only 1 evaluated stress case; 표본 부족 |
| FXY + SPLV | multi | REFERENCE_ONLY | 31.4 | validation_thin, cash_baseline_lag, bootstrap_not_robust, cash_bootstrap_not_robust, liquidity_below_formal, return_drag_reference, reference_only | 1 | 1 | 0/1 | 0.785 | 0/1 | 0.07 | -0.018289 | target-scenario backtest has only 1 evaluated stress case; 표본 부족 |
| FXE | one_to_one | REFERENCE_ONLY | 32.1 | validation_thin, cash_baseline_lag, bootstrap_not_robust, cash_bootstrap_not_robust, liquidity_below_formal, return_drag_reference, reference_only | 1 | 1 | 0/1 | 0.825 | 0/1 | 0.105 | -0.006579 | target-scenario backtest has only 1 evaluated stress case; 표본 부족 |
| FXE | one_to_one | REFERENCE_ONLY | 32.8 | validation_thin, cash_baseline_lag, bootstrap_not_robust, cash_bootstrap_not_robust, liquidity_below_formal, return_drag_reference, reference_only | 1 | 1 | 0/1 | 0.785 | 0/1 | 0.14 | -0.012765 | target-scenario backtest has only 1 evaluated stress case; 표본 부족 |
| FXE + 132030.KS | multi | REFERENCE_ONLY | 31.3 | validation_thin, cash_baseline_lag, bootstrap_not_robust, cash_bootstrap_not_robust, liquidity_below_formal, reference_only | 1 | 1 | 0/1 | 0.795 | 0/1 | 0.065 | -0.01531 | target-scenario backtest has only 1 evaluated stress case; 표본 부족 |
| BTAL + FXE | multi | REFERENCE_ONLY | 54.8 | validation_thin, bootstrap_not_robust, cash_bootstrap_not_robust, liquidity_below_formal, return_drag_reference, reference_only | 1 | 0 | 0/1 | 0.795 | 0/1 | 0.24 | -0.009851 | target-scenario backtest has only 1 evaluated stress case; 표본 부족 |
| 261240.KS + FXY | multi | REFERENCE_ONLY | 63.9 | validation_thin, bootstrap_not_robust, cash_bootstrap_not_robust, liquidity_below_formal, return_drag_reference, reference_only | 1 | 0 | 0/1 | 0.91 | 0/1 | 0.695 | 0.008028 | target-scenario backtest has only 1 evaluated stress case; 표본 부족 |
| 261240.KS + BTAL | multi | REFERENCE_ONLY | 64.1 | validation_thin, bootstrap_not_robust, cash_bootstrap_not_robust, liquidity_below_formal, return_drag_reference, reference_only | 1 | 0 | 0/1 | 0.885 | 0/1 | 0.705 | 0.012277 | target-scenario backtest has only 1 evaluated stress case; 표본 부족 |

## Closest Formal Near-misses

| candidate | source | status | readiness | blockers | target eval | cash lags | robust/boot | min p | cash robust/boot | cash min p | avg cash stress | reason |
|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| GLD | one_to_one | REFERENCE_ONLY | 73.4 | validation_thin, bootstrap_not_robust, cash_bootstrap_not_robust, return_drag_reference, reference_only | 1 | 0 | 0/1 | 0.17 | 0/1 | 0.93 | 0.078126 | target-scenario backtest has only 1 evaluated stress case; 표본 부족 |
| GLD | one_to_one | REFERENCE_ONLY | 72.9 | validation_thin, bootstrap_not_robust, cash_bootstrap_not_robust, reference_only | 1 | 0 | 0/1 | 0.145 | 0/1 | 0.865 | 0.039051 | target-scenario backtest has only 1 evaluated stress case; 표본 부족 |
| IAU | one_to_one | REFERENCE_ONLY | 72.5 | validation_thin, bootstrap_not_robust, cash_bootstrap_not_robust, reference_only | 1 | 0 | 0/1 | 0.125 | 0/1 | 0.91 | 0.03947 | target-scenario backtest has only 1 evaluated stress case; 표본 부족 |
| IAU | one_to_one | REFERENCE_ONLY | 72.3 | validation_thin, bootstrap_not_robust, cash_bootstrap_not_robust, return_drag_reference, reference_only | 1 | 0 | 0/1 | 0.115 | 0/1 | 0.885 | 0.078963 | target-scenario backtest has only 1 evaluated stress case; 표본 부족 |
| 261240.KS | one_to_one | REFERENCE_ONLY | 69.1 | validation_thin, bootstrap_not_robust, liquidity_below_formal, reference_only | 1 | 0 | 0/1 | 0.955 | 1/1 | 0.995 | 0.023889 | target-scenario backtest has only 1 evaluated stress case; 표본 부족 |
| 261240.KS + FXF | multi | REFERENCE_ONLY | 68.8 | validation_thin, bootstrap_not_robust, cash_bootstrap_not_robust, liquidity_below_formal, reference_only | 1 | 0 | 0/1 | 0.94 | 0/1 | 0.95 | 0.018612 | target-scenario backtest has only 1 evaluated stress case; 표본 부족 |
| 261240.KS + FXF | multi | REFERENCE_ONLY | 68.8 | validation_thin, bootstrap_not_robust, cash_bootstrap_not_robust, liquidity_below_formal, reference_only | 1 | 0 | 0/1 | 0.94 | 0/1 | 0.94 | 0.018515 | target-scenario backtest has only 1 evaluated stress case; 표본 부족 |
| 261240.KS + FXE | multi | REFERENCE_ONLY | 68.2 | validation_thin, bootstrap_not_robust, cash_bootstrap_not_robust, liquidity_below_formal, reference_only | 1 | 0 | 0/1 | 0.94 | 0/1 | 0.91 | 0.016744 | target-scenario backtest has only 1 evaluated stress case; 표본 부족 |
| 261240.KS + FXY | multi | REFERENCE_ONLY | 67.7 | validation_thin, bootstrap_not_robust, cash_bootstrap_not_robust, liquidity_below_formal, reference_only | 1 | 0 | 0/1 | 0.9 | 0/1 | 0.885 | 0.015116 | target-scenario backtest has only 1 evaluated stress case; 표본 부족 |
| 261240.KS + FXE | multi | REFERENCE_ONLY | 65.8 | validation_thin, bootstrap_not_robust, cash_bootstrap_not_robust, liquidity_below_formal, reference_only | 1 | 0 | 0/1 | 0.91 | 0/1 | 0.79 | 0.012911 | target-scenario backtest has only 1 evaluated stress case; 표본 부족 |
| 261240.KS + BTAL | multi | REFERENCE_ONLY | 64.1 | validation_thin, bootstrap_not_robust, cash_bootstrap_not_robust, liquidity_below_formal, return_drag_reference, reference_only | 1 | 0 | 0/1 | 0.885 | 0/1 | 0.705 | 0.012277 | target-scenario backtest has only 1 evaluated stress case; 표본 부족 |
| 261240.KS + FXY | multi | REFERENCE_ONLY | 63.9 | validation_thin, bootstrap_not_robust, cash_bootstrap_not_robust, liquidity_below_formal, return_drag_reference, reference_only | 1 | 0 | 0/1 | 0.91 | 0/1 | 0.695 | 0.008028 | target-scenario backtest has only 1 evaluated stress case; 표본 부족 |
