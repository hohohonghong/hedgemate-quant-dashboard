# Phase 10E Rebalance-cost Path Walk-forward Backtest

- run_id: `backtest-20260610T234722934082-d6e95bcc`
- historical_validation_run_id: `phase10a-wave5-20260514`
- hedgemate_run_id: `20260610T234722934082-d6e95bcc`
- engine_version: `phase10e_rebalance_cost_path_walk_forward_v1`
- data_mode: API-free cached raw market prices
- transaction_cost_bps: 10
- slippage_bps: 5
- rebalance_frequency: `formation_only`
- bootstrap_iterations: 200
- bootstrap_ci_level: 0.95
- return_path_model: formation_only uses buy-and-hold weights; monthly/daily modes rebalance to target weights
- implementation_cost_model: one-time formation turnover cost deducted from proposed returns
- recurring_rebalance_cost_model: monthly/daily modes deduct turnover cost at each scheduled rebalance
- evaluated_rows: 0
- insufficient_history_rows: 0
- insufficient_evaluation_window_rows: 0
- out_of_price_range_rows: 0
- beats_cash_rows: 0
- lags_cash_rows: 0

## Verdict Counts
- IMPROVED: 0
- MIXED: 0
- WORSENED: 0
- INSUFFICIENT_HISTORY: 0

## Hedge vs Cash Baseline
- BEATS_CASH: 0
- MIXED_CASH: 0
- LAGS_CASH: 0

## Price Window Counts

## Price Blocking Tickers
- none

## Pre-inception Tickers
- none

## Missing Price Tickers
- none

## Notes
- Verdict counts use cost-adjusted proposed returns.
- Bootstrap intervals resample paired daily base/proposed-net returns by candidate and stress case.
- Insufficient-history cases are never counted as successful detection or backtest wins.
- Historical validation cases were not available in this deployment; backtest evidence was not evaluated and downstream gates must keep recommendations review-only.
- missing_historical_validation_path: `C:\Users\석민\Documents\cau_2026_ss\금융인공지능실습1\deploy_beecast\scenario_research\outputs\validation\historical_validation_cases_phase10a-wave5-20260514.csv`
