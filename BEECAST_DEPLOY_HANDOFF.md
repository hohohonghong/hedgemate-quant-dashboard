# HedgeMate Bee-cast Deploy Handoff

Last verified: 2026-06-11 KST

This package preserves the currently working HedgeMate deployment state:

- Frontend build target: `hedge-front/dist`
- Backend entrypoint: `HedgeMate/scripts/serve_dashboard.py`
- Backend default local API URL for QA: `http://127.0.0.1:8766/api`
- Public frontend URL used in QA: `https://hedgemate.eyefeet.com`
- Bee-cast/admin context: `admin.eyefeet.com`

## What Is Included

- Full backend/frontend source.
- Current frontend `dist` build.
- Current HedgeMate and scenario output artifacts needed to reproduce the latest working state.
- QA/report artifacts under `HedgeMate/outputs/reports`.

## What Is Not Included

Secrets are intentionally excluded. Recreate them on each machine.

Required Gemini key file:

```bash
mkdir -p .secrets
printf '%s\n' 'PASTE_GEMINI_API_KEY_HERE' > .secrets/gemini_api_key.txt
chmod 600 .secrets/gemini_api_key.txt
```

Do not commit or upload `.secrets`.

## Backend Startup

From the package root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python HedgeMate/scripts/serve_dashboard.py --host 127.0.0.1 --port 8766
```

Expected health checks:

```bash
curl -fsS http://127.0.0.1:8766/api/health
curl -fsS http://127.0.0.1:8766/api/assets
curl -fsS http://127.0.0.1:8766/api/scenario-dashboard
```

Important expected values:

- `/api/assets` returns 150 assets.
- `/api/status` has `serverSafeMode=false`.
- `/api/scenario-dashboard` has today's intraday nowcast date.
- News overlay has `provider=gemini`, `fallbackUsed=false`, `top5Count=5` after Gemini key is present and network/SSL works.

## Frontend Build And Bee-cast Upload

From `hedge-front`:

```bash
npm ci
npm run build
```

Upload the contents of:

```text
hedge-front/dist
```

to Bee-cast for the `hedgemate.eyefeet.com` frontend.

Runtime API config lives at:

```text
hedge-front/dist/hedgemate-runtime-config.js
```

Current default:

```js
window.__HEDGEMATE_API_URL__ = "";
```

With an empty value, the frontend calls same-origin `/api`. If Bee-cast is not proxying `/api`, set this file to the backend base URL before upload, for example:

```js
window.__HEDGEMATE_API_URL__ = "http://127.0.0.1:8766";
```

The backend CORS allowlist already includes `https://hedgemate.eyefeet.com`.

## News/Gemini Recovery Notes

The working fix uses `certifi` for HTTPS requests in:

```text
scenario_research/scripts/news_intraday_overlay.py
```

If news disappears again, check:

```bash
python scenario_research/scripts/run_intraday_news_overlay_pipeline.py --force --trigger-reason manual-check
curl -fsS http://127.0.0.1:8766/api/scenario-dashboard
```

Healthy news status:

- `gemini_key_present=true`
- `provider=gemini`
- `fallback_used=false`
- API `intradayNewsTop5` length is 5
- News URLs are real `https://news.google.com/...` or publisher links, not `fallback://...`

## QA Checklist

Run after backend is up and frontend is deployed:

1. Open `https://hedgemate.eyefeet.com`.
2. Confirm login/profile is real user data, not the placeholder HedgeMate user.
3. Confirm ticker search shows the full 150-asset universe.
4. Run portfolio analysis and confirm:
   - no duplicate "실시간 시장데이터 확인중" state
   - no `Hegdemate` typo
   - no unexplained `CCY` label in user-facing text
   - result report shows CVaR, MDD, beta, Sharpe improvements where applicable
   - formal recommendations may be `REVIEW_ONLY` if strict cash/bootstrap gate blocks execution, but review candidates/backtests should still be visible
5. Open market-state page and confirm:
   - current display date is today's KST date
   - no stale `0609`/old date chip beside refresh
   - news top 5 appears with clickable real URLs
   - confidence is not fallback-fixed at 60

## Known Product Status

`productStatus=REVIEW_ONLY` can be valid. It means candidates/backtests are available, but formal execution recommendations are blocked by strict gate policy. Do not treat this alone as a data failure.
