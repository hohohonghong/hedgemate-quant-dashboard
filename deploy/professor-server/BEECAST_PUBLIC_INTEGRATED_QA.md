# Bee-cast Public Integrated QA

Date: 2026-06-11 KST

## Scope

Verified the live Bee-cast HedgeMate deployment at:

```text
https://hedgemate.eyefeet.com
https://hedgemate.eyefeet.com/api
```

The goal was to confirm that the public frontend and backend API are reachable and that scheduler-backed market data remains fresh after the 18:00 KST cycle.

## Current QA Status

Status: **failing freshness QA after 18:00 KST**.

The public API is reachable and most product data is alive, but the current market-state path is not fully fresh:

- `market_data=FRESH`
- `intraday_nowcast=STALE`
- primary market state source is `daily_final`, not `intraday_nowcast`
- daily final basis remains `2026-06-09`

## 18:00 KST Market Data Evidence

Refresh DB:

```text
market_data_only SUCCESS
started 2026-06-11 18:03:00 KST
finished 2026-06-11 18:03:59 KST
```

Raw manifest:

```text
dataVersion=20260611
latestMarketDate=2026-06-11
totalTickers=150
failedTickers=[]
staleTickers=[]
tickerCoverageRatio=1.0
```

So the market-data job did run. The issue is downstream market-state anchoring and nowcast refresh, not a missing market-data job.

## Latest Automated QA

Command:

```bash
python deploy/professor-server/qa_professor_server.py \
  --api-base https://hedgemate.eyefeet.com/api \
  --root /tmp/hedgemate-server-deploy-test/hedgemate-beecast-fix \
  --wait-seconds 180
```

Result: **FAIL 3/21 required checks**.

Failed:

- intraday nowcast fresh
- primary source is intraday nowcast
- news adjustment applied, due to market-state base-date mismatch

Passed:

- API health
- `serverSafeMode=false`
- scheduler running
- market data fresh
- news overlay fresh
- `productStatus=REVIEW_ONLY`
- 150 assets
- today KST display date
- Gemini news provider and real links
- candidate/backtest artifact rows
- same-origin runtime config
- forbidden placeholder/typo strings absent

## Root Cause Candidate

The scenario engine's daily final anchor is selected only when required market-state proxy tickers align on the same date. The required set includes `SOXX`, `UUP`, and `^VIX`. After the 18:03 KST refresh, `SOXX` and `UUP` still ended at `2026-06-09` in the scenario metadata, so the daily final anchor stayed at `2026-06-09`.

Also, no `intraday_nowcast` job was recorded after 18:00 KST. The latest nowcast artifact was still the 15:21 KST file, so after the 18:00 anchor the nowcast became stale.

## Fix Direction

Do not solve this by reducing assets or skipping heavy work.

Required fixes:

- Make required market-state proxy tickers refresh reliably, especially `SOXX` and `UUP`, even when they are not in the 150-asset universe.
- Chain or schedule `intraday_nowcast` after the 18:00 KST market-data refresh.
- Add QA that distinguishes market-data success from market-state anchor freshness.
- Keep the public deployment marked not fully QA-clean until this passes after 18:00 KST.

## Localfix Verification

The isolated restore copy was patched and verified locally without modifying the protected working copy:

```text
/tmp/hedgemate-server-deploy-test/hedgemate-beecast-fix
```

Fixes applied in the isolated copy:

- Scheduler wait now aligns to the next KST 3-hour anchor plus a 3-minute grace window, instead of drifting from process start time.
- Scheduled `intraday_nowcast` no longer uses `reuseRaw`, so a new 18:00/21:00 anchor fetch does not reuse the older 15:00 raw file.
- The market-state summary hides stale daily final dates in the daily TOP 3 chip when the primary display is fresh intraday nowcast.

Local nowcast refresh:

```text
latestTimestampKst=2026-06-11T18:14:31+09:00
requiredAnchorKst=2026-06-11T18:00:00+09:00
fresh=true
collection_mode=fetch_yahoo_intraday
fetched_ticker_count=20
```

Local API QA:

```bash
python deploy/professor-server/qa_professor_server.py \
  --api-base http://127.0.0.1:8876/api \
  --root /tmp/hedgemate-server-deploy-test/hedgemate-beecast-fix \
  --wait-seconds 180
```

Result: **PASS 21/21 required checks**.

This localfix has not yet been deployed to Bee-cast, so the public deployment should still be treated as pending until the same public QA passes at `https://hedgemate.eyefeet.com/api`.
