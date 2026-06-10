# Phase 10E Rebalance-cost Path Walk-forward Backtest

- run_id: `backtest-20260610T191953943306-da0898b3`
- historical_validation_run_id: `phase10a-wave5-20260514`
- hedgemate_run_id: `20260610T191953943306-da0898b3`
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
- evaluated_rows: 90
- insufficient_history_rows: 0
- insufficient_evaluation_window_rows: 0
- out_of_price_range_rows: 0
- beats_cash_rows: 46
- lags_cash_rows: 44

## Verdict Counts
- IMPROVED: 88
- MIXED: 0
- WORSENED: 2
- INSUFFICIENT_HISTORY: 0

## Hedge vs Cash Baseline
- BEATS_CASH: 46
- MIXED_CASH: 0
- LAGS_CASH: 44

## Price Window Counts
- PRICE_WINDOW_AVAILABLE: 90

## Price Blocking Tickers
- 132030.KS: 2
- 153130.KS: 2
- 261240.KS: 2

## Pre-inception Tickers
- 132030.KS: 2
- 153130.KS: 2
- 261240.KS: 2

## Missing Price Tickers
- none

## Notes
- Verdict counts use cost-adjusted proposed returns.
- Bootstrap intervals resample paired daily base/proposed-net returns by candidate and stress case.
- Insufficient-history cases are never counted as successful detection or backtest wins.
