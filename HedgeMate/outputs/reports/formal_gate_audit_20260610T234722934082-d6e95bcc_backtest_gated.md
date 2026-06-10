# Formal Gate Audit

- candidate_rows: 27
- status_counts: `{"PASS_RECOMMEND": 0, "REFERENCE_ONLY": 0, "FAIL_GATE": 27, "INSUFFICIENT_DATA": 0}`

## Blocker Counts

- fail_gate: 27 - 하드 게이트 실패 - Candidate failed a hard gate. Next action: Do not promote until the failing gate is resolved.
- validation_not_eligible: 27 - validation not eligible - Candidate is not eligible for backtest validation. Next action: Keep blocked or rebuild the candidate with valid backtest inputs.
- liquidity_below_formal: 20 - 유동성 기준 미달 - 60-day ADV evidence is missing or below the formal threshold. Next action: Refresh ADV evidence or exclude the candidate from formal recommendations.
- return_drag_reference: 7 - 수익률 훼손 검토 필요 - Pre-backtest scoring kept the candidate reference-only because of return drag. Next action: Confirm risk reduction compensates for return drag before promotion.

## Liquidity Capacity Audit

- MISSING_ADV: 20
- ORDER_SIZE_ADV_USAGE_OK: 7

| candidate | source | status | ADV KRW | order KRW | ADV usage % | capacity status |
|---|---|---|---:|---:|---:|---|
| 000810.KS | one_to_one | FAIL_GATE |  | 167099.0 |  | MISSING_ADV |
| 005930.KS | one_to_one | FAIL_GATE |  | 167099.0 |  | MISSING_ADV |
| 032830.KS | one_to_one | FAIL_GATE |  | 167099.0 |  | MISSING_ADV |
| 035420.KS | one_to_one | FAIL_GATE |  | 167099.0 |  | MISSING_ADV |
| 068270.KS | one_to_one | FAIL_GATE |  | 167099.0 |  | MISSING_ADV |
| 114800.KS + 000810.KS | multi | FAIL_GATE |  | 167099.0 |  | MISSING_ADV |
| 114800.KS + 005930.KS | multi | FAIL_GATE |  | 167099.0 |  | MISSING_ADV |
| 114800.KS + 017670.KS | multi | FAIL_GATE |  | 167099.0 |  | MISSING_ADV |
| 114800.KS + 032830.KS | multi | FAIL_GATE |  | 167099.0 |  | MISSING_ADV |
| 114800.KS + 105560.KS | multi | FAIL_GATE |  | 167099.0 |  | MISSING_ADV |
| 132030.KS + 000810.KS | multi | FAIL_GATE |  | 167099.0 |  | MISSING_ADV |
| 132030.KS + 005930.KS | multi | FAIL_GATE |  | 167099.0 |  | MISSING_ADV |

## Highest-friction Candidates

| candidate | source | status | readiness | blockers | target eval | cash lags | robust/boot | min p | cash robust/boot | cash min p | min cash stress | reason |
|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| 000810.KS | one_to_one | FAIL_GATE | 10.0 | fail_gate, validation_not_eligible, liquidity_below_formal | 0 | 0 | 0/0 |  | 0/0 |  |  | candidate was not eligible for the bounded scenario backtest run |
| 005930.KS | one_to_one | FAIL_GATE | 10.0 | fail_gate, validation_not_eligible, liquidity_below_formal | 0 | 0 | 0/0 |  | 0/0 |  |  | candidate was not eligible for the bounded scenario backtest run |
| 032830.KS | one_to_one | FAIL_GATE | 10.0 | fail_gate, validation_not_eligible, liquidity_below_formal | 0 | 0 | 0/0 |  | 0/0 |  |  | candidate was not eligible for the bounded scenario backtest run |
| 035420.KS | one_to_one | FAIL_GATE | 10.0 | fail_gate, validation_not_eligible, liquidity_below_formal | 0 | 0 | 0/0 |  | 0/0 |  |  | candidate was not eligible for the bounded scenario backtest run |
| 068270.KS | one_to_one | FAIL_GATE | 10.0 | fail_gate, validation_not_eligible, liquidity_below_formal | 0 | 0 | 0/0 |  | 0/0 |  |  | candidate was not eligible for the bounded scenario backtest run |
| 114800.KS + 000810.KS | multi | FAIL_GATE | 10.0 | fail_gate, validation_not_eligible, liquidity_below_formal | 0 | 0 | 0/0 |  | 0/0 |  |  | candidate was not eligible for the bounded scenario backtest run |
| 114800.KS + 005930.KS | multi | FAIL_GATE | 10.0 | fail_gate, validation_not_eligible, liquidity_below_formal | 0 | 0 | 0/0 |  | 0/0 |  |  | candidate was not eligible for the bounded scenario backtest run |
| 114800.KS + 017670.KS | multi | FAIL_GATE | 10.0 | fail_gate, validation_not_eligible, liquidity_below_formal | 0 | 0 | 0/0 |  | 0/0 |  |  | candidate was not eligible for the bounded scenario backtest run |
| 114800.KS + 032830.KS | multi | FAIL_GATE | 10.0 | fail_gate, validation_not_eligible, liquidity_below_formal | 0 | 0 | 0/0 |  | 0/0 |  |  | candidate was not eligible for the bounded scenario backtest run |
| 114800.KS + 105560.KS | multi | FAIL_GATE | 10.0 | fail_gate, validation_not_eligible, liquidity_below_formal | 0 | 0 | 0/0 |  | 0/0 |  |  | candidate was not eligible for the bounded scenario backtest run |
| 132030.KS + 000810.KS | multi | FAIL_GATE | 10.0 | fail_gate, validation_not_eligible, liquidity_below_formal | 0 | 0 | 0/0 |  | 0/0 |  |  | candidate was not eligible for the bounded scenario backtest run |
| 132030.KS + 005930.KS | multi | FAIL_GATE | 10.0 | fail_gate, validation_not_eligible, liquidity_below_formal | 0 | 0 | 0/0 |  | 0/0 |  |  | candidate was not eligible for the bounded scenario backtest run |

## Closest Formal Near-misses

| candidate | source | status | readiness | blockers | target eval | cash lags | robust/boot | min p | cash robust/boot | cash min p | avg cash stress | reason |
|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
