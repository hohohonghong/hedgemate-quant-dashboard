# HedgeMate Professor Server Deployment

This runbook is for deploying the restored HedgeMate package as one server-hosted product:

- Backend: Python server on `127.0.0.1:8766`
- Frontend: static files from `hedge-front/dist`
- Reverse proxy: public HTTPS host routes `/api/*` to backend and all other paths to the frontend

The local restore test used port `8876` only because the protected local backend was already running on `8766`.

## Bee-cast Public Verification

The live Bee-cast tenant was verified on 2026-06-11 KST:

- Admin host: `https://admin.eyefeet.com`
- Public host: `https://hedgemate.eyefeet.com`
- Runtime observed: `python`
- Branch observed: `beecast-deploy`
- Tenant status observed: `running`
- Public API base: `https://hedgemate.eyefeet.com/api`

The public API is reachable and the 150-asset universe remains alive. However, the 18:00 KST recheck is **not fully QA-clean**: market data refreshed successfully at 18:03 KST, but daily market-state anchoring stayed at `2026-06-09`, and `intraday_nowcast` became `STALE` because no 18:00 nowcast artifact was created.

See `BEECAST_PUBLIC_INTEGRATED_QA.md` and `GOAL_COMPLETION_AUDIT.md` before treating the public deployment as complete.

An isolated localfix copy now passes 21/21 QA on `127.0.0.1:8876`. That patch must still be deployed to Bee-cast and rechecked publicly before this runbook can be treated as a completed deployment.

No redeploy was triggered during this verification because the Bee-cast tenant was already running a successful deployment and the public URL passed QA.

## Safety Rules

- Do not edit the protected local working copy at `/tmp/hedgemate-beecast-fix`.
- Do not commit `.secrets`, `.venv`, `node_modules`, or bulky `outputs` snapshots into normal Git history.
- Keep code in GitHub; keep large reproducible snapshots as GitHub Release assets or external archives.
- Do not enable lite/safe/skip modes for production. The backend should run the full 150-asset universe and normal scheduler.

## First Install On Server

Assumed install path:

```bash
/opt/hedgemate/current/hedgemate-beecast-fix
```

Commands:

```bash
cd /opt/hedgemate/current/hedgemate-beecast-fix
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

mkdir -p .secrets
printf '%s\n' 'PASTE_GEMINI_API_KEY_HERE' > .secrets/gemini_api_key.txt
chmod 600 .secrets/gemini_api_key.txt

cd hedge-front
npm ci
npm run build
```

Keep `hedge-front/dist/hedgemate-runtime-config.js` as:

```js
window.__HEDGEMATE_API_URL__ = "";
```

That makes the browser call same-origin `/api`.

### Scripted Install

After extracting the package and creating `.secrets/gemini_api_key.txt`, this helper performs dependency install, frontend build, Python compile checks, and optional systemd install:

```bash
cd /opt/hedgemate/current/hedgemate-beecast-fix
sudo INSTALL_ROOT=/opt/hedgemate/current/hedgemate-beecast-fix \
  SERVICE_USER=hedgemate \
  BACKEND_PORT=8766 \
  deploy/professor-server/install_on_server.sh
```

To run without systemd changes:

```bash
SKIP_SYSTEMD=1 deploy/professor-server/install_on_server.sh
```

## Manual Backend Smoke Start

```bash
cd /opt/hedgemate/current/hedgemate-beecast-fix
.venv/bin/python HedgeMate/scripts/serve_dashboard.py --host 127.0.0.1 --port 8766
```

Health checks:

```bash
curl -fsS http://127.0.0.1:8766/api/health
curl -fsS http://127.0.0.1:8766/api/status
curl -fsS http://127.0.0.1:8766/api/assets
curl -fsS http://127.0.0.1:8766/api/scenario-dashboard
```

Expected:

- `serverSafeMode=false`
- `scheduler=RUNNING`
- `/api/assets` returns 150 assets
- `market_data=FRESH`
- `intraday_nowcast=FRESH`
- `news_overlay=FRESH`
- news status has `provider=gemini`, `fallbackUsed=false`, `top5Count=5`

## systemd

Copy `hedgemate-backend.service` to:

```bash
/etc/systemd/system/hedgemate-backend.service
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable hedgemate-backend
sudo systemctl start hedgemate-backend
sudo systemctl status hedgemate-backend
```

## nginx

Copy `nginx-hedgemate.conf` into the nginx site config, adjust `server_name`, TLS certificate paths, and frontend root as needed.

Required routing:

- `/api/` -> `http://127.0.0.1:8766/api/`
- everything else -> `hedge-front/dist`

After nginx is live, public checks should use:

```bash
curl -fsS https://hedgemate.eyefeet.com/api/health
curl -fsS https://hedgemate.eyefeet.com/api/assets
curl -fsS https://hedgemate.eyefeet.com/api/scenario-dashboard
```

## Automated QA

From the package root:

```bash
python deploy/professor-server/qa_professor_server.py \
  --api-base http://127.0.0.1:8766/api \
  --root .
```

After public `/api` proxy is live:

```bash
python deploy/professor-server/qa_professor_server.py \
  --api-base https://hedgemate.eyefeet.com/api \
  --root .
```

The script waits for startup refresh to settle, then checks safe mode, scheduler, 150 assets, today nowcast, Gemini news, candidate/backtest artifacts, runtime config, and forbidden placeholder strings.

The latest Bee-cast public recheck used:

```bash
python deploy/professor-server/qa_professor_server.py \
  --api-base https://hedgemate.eyefeet.com/api \
  --root /tmp/hedgemate-server-deploy-test/hedgemate-beecast-fix \
  --wait-seconds 180
```

Result: 18/21 required checks passed; 3 required freshness checks failed after 18:00 KST.

The localfix recheck used:

```bash
python deploy/professor-server/qa_professor_server.py \
  --api-base http://127.0.0.1:8876/api \
  --root /tmp/hedgemate-server-deploy-test/hedgemate-beecast-fix \
  --wait-seconds 180
```

Result: 21/21 required checks passed locally after the scheduler/nowcast patch.

## Docker Option

If Docker Compose is available, see:

```text
deploy/professor-server/docker/README.md
```

The Docker option exposes one frontend+API endpoint on port `8080` and keeps Gemini secrets mounted from `.secrets`.

## Rollback

If the professor server deployment is unstable, leave the current local backend + Bee-cast frontend setup in place:

- Protected backend: `http://127.0.0.1:8766`
- Bee-cast frontend: `https://hedgemate.eyefeet.com`

The tested portable backup can be restored again from the release archive without touching the protected local working copy.

See also:

- `BEECAST_PUBLIC_INTEGRATED_QA.md` for the public Bee-cast verification result.
- `qa_professor_server.py` for repeatable post-deploy QA.
- `install_on_server.sh` for repeatable non-Docker server setup.
- `docker/README.md` for the Docker Compose option.
- `GITHUB_RELEASE_STRATEGY.md` for what belongs in Git vs Release assets.
- `ROLLBACK_CHECKLIST.md` for the exact rollback sequence.
- `SERVER_ACCESS_REQUIREMENTS.md` for the information needed before real server deployment.
- `GOAL_COMPLETION_AUDIT.md` for the requirement-by-requirement status.
