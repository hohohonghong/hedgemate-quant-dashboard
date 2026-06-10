# Backtest Gate Summary

- generated_at_utc: 2026-06-05T09:04:58Z
- hedgemate_run_id: hedgemate-refresh-20260605
- backtest_run_id: backtest-refresh-20260605
- one_to_one_rows: 114
- multi_rows: 63
- one_to_one_status_counts: `{"FAIL_GATE": 91, "REFERENCE_ONLY": 23}`
- multi_status_counts: `{"FAIL_GATE": 42, "REFERENCE_ONLY": 21}`
- post_backtest_qa_md: C:\Users\석민\Documents\cau_2026_ss\금융인공지능실습1\project\HedgeMate\outputs\reports\recommendation_status_qa_post_backtest_hedgemate-refresh-20260605_backtest_gated.md
- backtest_attribution_csv: C:\Users\석민\Documents\cau_2026_ss\금융인공지능실습1\project\HedgeMate\outputs\reports\backtest_attribution_backtest-refresh-20260605.csv
- backtest_attribution_md: C:\Users\석민\Documents\cau_2026_ss\금융인공지능실습1\project\HedgeMate\outputs\reports\backtest_attribution_backtest-refresh-20260605.md
- formal_gate_audit_csv: C:\Users\석민\Documents\cau_2026_ss\금융인공지능실습1\project\HedgeMate\outputs\reports\formal_gate_audit_hedgemate-refresh-20260605_backtest_gated.csv
- formal_gate_audit_md: C:\Users\석민\Documents\cau_2026_ss\금융인공지능실습1\project\HedgeMate\outputs\reports\formal_gate_audit_hedgemate-refresh-20260605_backtest_gated.md
- formal_gate_blocker_counts: `{"fail_gate": 133, "validation_not_eligible": 133, "liquidity_below_formal": 119, "return_drag_reference": 55, "reference_only": 44, "bootstrap_not_robust": 23, "validation_thin": 23, "cash_bootstrap_not_robust": 22, "validation_insufficient": 21, "cash_baseline_lag": 9}`

## Policy

- Backtest verdicts are treated as cost-adjusted when cost fields are present.
- WORSENED candidates are not allowed to remain PASS_RECOMMEND.
- INSUFFICIENT_HISTORY is shown as validation insufficient, never as success.
- Formal recommendations require at least 2 evaluated target stress cases.
- Formal recommendations must beat a cash-only de-risking baseline in target stress cases.
- If portfolio and cash-baseline bootstrap confidence fields are present, every evaluated target stress case must be ROBUST_IMPROVE for a formal recommendation.
- Formal recommendations require combo_min_adv_60 of at least 100,000,000,000 KRW.
- Formal recommendations require target max turnover no higher than 0.50.
- Candidates without matching backtest evidence are downgraded from formal recommendation to reference-only.
