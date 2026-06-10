# Phase 10E Rebalance-cost Path Walk-forward Backtest

- run_id: `backtest-20260605T225345344426-c0d015ec`
- historical_validation_run_id: `phase10a-wave5-20260514`
- hedgemate_run_id: `20260605T225345344426-c0d015ec`
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
- evaluated_rows: 108
- insufficient_history_rows: 0
- insufficient_evaluation_window_rows: 0
- out_of_price_range_rows: 0
- beats_cash_rows: 55
- lags_cash_rows: 53

## Verdict Counts
- IMPROVED: 107
- MIXED: 0
- WORSENED: 1
- INSUFFICIENT_HISTORY: 0

## Hedge vs Cash Baseline
- BEATS_CASH: 55
- MIXED_CASH: 0
- LAGS_CASH: 53

## Price Window Counts
- PRICE_WINDOW_AVAILABLE: 108

## Price Blocking Tickers
- 114800.KS: 1

## Pre-inception Tickers
- 114800.KS: 1

## Missing Price Tickers
- none

## Notes
- Verdict counts use cost-adjusted proposed returns.
- Bootstrap intervals resample paired daily base/proposed-net returns by candidate and stress case.
- Insufficient-history cases are never counted as successful detection or backtest wins.
