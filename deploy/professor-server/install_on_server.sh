#!/usr/bin/env bash
set -euo pipefail

INSTALL_ROOT="${INSTALL_ROOT:-/opt/hedgemate/current/hedgemate-beecast-fix}"
SERVICE_USER="${SERVICE_USER:-hedgemate}"
SERVICE_GROUP="${SERVICE_GROUP:-hedgemate}"
BACKEND_PORT="${BACKEND_PORT:-8766}"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
SKIP_SYSTEMD="${SKIP_SYSTEMD:-0}"

usage() {
  cat <<'EOF'
Install HedgeMate on a professor server from an extracted package.

Run this from the extracted hedgemate-beecast-fix package root.

Environment overrides:
  INSTALL_ROOT=/opt/hedgemate/current/hedgemate-beecast-fix
  SERVICE_USER=hedgemate
  SERVICE_GROUP=hedgemate
  BACKEND_HOST=127.0.0.1
  BACKEND_PORT=8766
  SKIP_SYSTEMD=1

Required before final service start:
  .secrets/gemini_api_key.txt

This script never prints secret values.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

PACKAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PACKAGE_ROOT"

echo "PACKAGE_ROOT=$PACKAGE_ROOT"
echo "INSTALL_ROOT=$INSTALL_ROOT"
echo "BACKEND=${BACKEND_HOST}:${BACKEND_PORT}"

if [[ ! -f requirements.txt ]]; then
  echo "ERROR: requirements.txt not found. Run from the extracted package." >&2
  exit 1
fi

if [[ ! -f .secrets/gemini_api_key.txt ]]; then
  cat >&2 <<EOF
ERROR: .secrets/gemini_api_key.txt is missing.

Create it without printing the key:
  mkdir -p .secrets
  printf '%s\n' 'PASTE_GEMINI_API_KEY_HERE' > .secrets/gemini_api_key.txt
  chmod 600 .secrets/gemini_api_key.txt
EOF
  exit 1
fi

if [[ ! -s .secrets/gemini_api_key.txt ]]; then
  echo "ERROR: .secrets/gemini_api_key.txt exists but is empty." >&2
  exit 1
fi

chmod 600 .secrets/gemini_api_key.txt

python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

(
  cd hedge-front
  npm ci
  npm run build
)

python -m py_compile \
  HedgeMate/scripts/serve_dashboard.py \
  scenario_research/scripts/news_intraday_overlay.py \
  deploy/professor-server/qa_professor_server.py

if [[ "$SKIP_SYSTEMD" != "1" && "$(id -u)" == "0" ]]; then
  if ! id "$SERVICE_USER" >/dev/null 2>&1; then
    useradd --system --home-dir "$(dirname "$INSTALL_ROOT")" --shell /usr/sbin/nologin "$SERVICE_USER"
  fi

  chown -R "$SERVICE_USER:$SERVICE_GROUP" "$PACKAGE_ROOT"

  sed \
    -e "s|User=hedgemate|User=${SERVICE_USER}|g" \
    -e "s|Group=hedgemate|Group=${SERVICE_GROUP}|g" \
    -e "s|/opt/hedgemate/current/hedgemate-beecast-fix|${INSTALL_ROOT}|g" \
    -e "s|--host 127.0.0.1 --port 8766|--host ${BACKEND_HOST} --port ${BACKEND_PORT}|g" \
    deploy/professor-server/hedgemate-backend.service \
    > /etc/systemd/system/hedgemate-backend.service

  systemctl daemon-reload
  systemctl enable hedgemate-backend
  systemctl restart hedgemate-backend
  systemctl status hedgemate-backend --no-pager || true
else
  echo "Systemd install skipped. Manual backend command:"
  echo ".venv/bin/python HedgeMate/scripts/serve_dashboard.py --host ${BACKEND_HOST} --port ${BACKEND_PORT}"
fi

echo "Run QA after backend is reachable:"
echo ".venv/bin/python deploy/professor-server/qa_professor_server.py --api-base http://${BACKEND_HOST}:${BACKEND_PORT}/api --root ${PACKAGE_ROOT}"
