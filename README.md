# HedgeMate Quant Dashboard

HedgeMate is a local quant dashboard that combines the `HedgeMate` backend, the
`hedge-front` React UI, and the `scenario_research` market-regime pipeline.

The frontend and backend are connected through `/api`. In development, Vite
proxies `/api` to `http://127.0.0.1:8766`. In the packaged local runner,
`serve_frontend.py` serves `hedge-front/dist` and proxies `/api` to the same
backend.

## Requirements

- Python 3.11 or newer
- Node.js 18 or newer
- Internet access for market-data refreshes

## First Setup

```powershell
git clone https://github.com/hohohonghong/hedgemate-quant-dashboard.git
cd hedgemate-quant-dashboard

py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

cd hedge-front
npm ci
cd ..
```

Generated outputs and raw market-data caches are intentionally not committed to
GitHub. On a fresh computer, create the first active bundle before expecting the
full dashboard/report pages to show current results:

```powershell
python HedgeMate\scripts\refresh_product_bundle.py --data-version YYYYMMDD --run-stamp YYYYMMDD
```

Use today's date in `YYYYMMDD` form. The first run can take a while because it
downloads market data and rebuilds scenario, hedge, backtest, and active-bundle
artifacts.

## Run

For a local app:

```powershell
python run.py
```

`run.py` starts the backend and frontend together. If `hedge-front/dist` is
missing, it automatically runs `npm ci` when needed and then `npm run build`
before starting the frontend on port `5173`.

Open `http://localhost:5173`. Stop both processes with:

```powershell
python stop.py
```

For frontend development:

```powershell
# Terminal 1
cd HedgeMate
python scripts\serve_dashboard.py --host 127.0.0.1 --port 8766

# Terminal 2
cd hedge-front
npm run dev -- --host 127.0.0.1
```

## Refresh Data

Refresh only market data:

```powershell
python refresh_market_data.py --mode market_data_only
```

Force a full rebuild through the API:

```powershell
python refresh_market_data.py --mode full_rebuild --force
```

The app skips refreshes when the latest available data is already active. When
daily bars are not fully available yet, the backend can use the latest intraday
nowcast data instead.

## Notes

- `HedgeMate/outputs`, `scenario_research/outputs`, `outputs`, and raw market
  caches are local generated artifacts.
- `hedge-front/dist` is rebuilt locally with `npm run build`.
- If `python run.py` starts but dashboard result pages are empty, run the first
  active-bundle command above.
