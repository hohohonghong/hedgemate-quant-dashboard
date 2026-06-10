# Backtest Gate Summary

- generated_at_utc: 2026-06-10T10:23:59Z
- hedgemate_run_id: 20260610T191953943306-da0898b3
- backtest_run_id: backtest-20260610T191953943306-da0898b3
- one_to_one_rows: 12
- multi_rows: 16
- one_to_one_status_counts: `{"FAIL_GATE": 5, "REFERENCE_ONLY": 7}`
- multi_status_counts: `{"FAIL_GATE": 13, "REFERENCE_ONLY": 3}`
- post_backtest_qa_md: C:\Users\석민\Documents\cau_2026_ss\금융인공지능실습1\project\HedgeMate\outputs\reports\recommendation_status_qa_post_backtest_20260610T191953943306-da0898b3_backtest_gated.md
- backtest_attribution_csv: C:\Users\석민\Documents\cau_2026_ss\금융인공지능실습1\project\HedgeMate\outputs\reports\backtest_attribution_backtest-20260610T191953943306-da0898b3.csv
- backtest_attribution_md: C:\Users\석민\Documents\cau_2026_ss\금융인공지능실습1\project\HedgeMate\outputs\reports\backtest_attribution_backtest-20260610T191953943306-da0898b3.md
- formal_gate_audit_csv: C:\Users\석민\Documents\cau_2026_ss\금융인공지능실습1\project\HedgeMate\outputs\reports\formal_gate_audit_20260610T191953943306-da0898b3_backtest_gated.csv
- formal_gate_audit_md: C:\Users\석민\Documents\cau_2026_ss\금융인공지능실습1\project\HedgeMate\outputs\reports\formal_gate_audit_20260610T191953943306-da0898b3_backtest_gated.md
- formal_gate_blocker_counts: `{"fail_gate": 18, "validation_not_eligible": 18, "liquidity_below_formal": 16, "reference_only": 10, "validation_insufficient": 8, "return_drag_reference": 6, "bootstrap_not_robust": 2, "cash_bootstrap_not_robust": 2, "validation_thin": 2}`

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
