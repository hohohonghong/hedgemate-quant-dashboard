# HedgeMate Submission Package

## Quick Start

This package includes the prebuilt frontend in `hedge-front/dist`.
For the normal demo run, Node.js and Vite are not required.

Requirements:

- Python 3.11 or newer
- Windows, macOS, or Linux terminal
- Internet connection only if you refresh market data or request live prices

Windows:

```bat
START_HedgeMate.bat
```

Cross-platform:

```bash
python run.py
```

Then open:

```text
http://localhost:5173
```

Stop the servers:

```bat
STOP_HedgeMate.bat
```

or:

```bash
python stop.py
```

## Why This Runs Without Vite

The React frontend was already built into `hedge-front/dist`.
`run.py` starts:

1. Python backend API on port `8766`
2. Python static frontend server on port `5173`

The frontend server also proxies `/api/*` requests to the backend, so the app can run without `npm run dev`.

If `5173` or `8766` is already in use, `run.py` automatically chooses a nearby free port and prints the actual URL.

## Optional Frontend Rebuild

Only use this if you want to rebuild the frontend source.
This step requires Node.js 18+ and npm.

```bash
cd hedge-front
npm ci
npm run build
cd ..
python run.py
```

If another computer has Vite or dependency errors, skip this rebuild and use the included `dist`.

## Verification

Runtime-only check, no Node.js required:

```bash
python verify.py
```

Full developer check, Node.js required:

```bash
python verify.py --full
```

## Main Folders

- `HedgeMate/`: backend API, analysis engine, inputs, and output artifacts
- `scenario_research/`: market scenario engine and scenario output artifacts
- `hedge-front/dist/`: prebuilt frontend used by `run.py`
- `hedge-front/src/`: frontend source code for optional rebuilds
- `run.py`: one-command backend/frontend launcher
- `serve_frontend.py`: static frontend server with API proxy
- `stop.py`: stops launched backend/frontend processes

## Notes

- Do not delete `hedge-front/dist` if the target computer does not have Node.js.
- Unzip to a short path such as `C:\HedgeMate_Submission` if Windows has path length issues.
- The package excludes `node_modules`, QA screenshots, temporary logs, and Python cache files.
