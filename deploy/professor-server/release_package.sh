#!/usr/bin/env bash
set -euo pipefail

PACKAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STAMP="${STAMP:-$(TZ=Asia/Seoul date +%Y%m%dT%H%M%SKST)}"
OUT_DIR="${OUT_DIR:-$HOME/Downloads/hedgemate-professor-server-trial-$STAMP}"

mkdir -p "$OUT_DIR"

COPYFILE_DISABLE=1 tar -czf "$OUT_DIR/hedgemate-professor-full-portable-$STAMP.tar.gz" \
  --exclude='hedgemate-beecast-fix/.git' \
  --exclude='hedgemate-beecast-fix/.secrets' \
  --exclude='hedgemate-beecast-fix/.venv' \
  --exclude='hedgemate-beecast-fix/venv' \
  --exclude='hedgemate-beecast-fix/__pycache__' \
  --exclude='hedgemate-beecast-fix/hedge-front/node_modules' \
  --exclude='*/__pycache__' \
  --exclude='*.pyc' \
  -C "$(dirname "$PACKAGE_ROOT")" "$(basename "$PACKAGE_ROOT")"

(
  cd "$PACKAGE_ROOT/hedge-front/dist"
  rm -f "$OUT_DIR/hedgemate-professor-front-dist-contents-$STAMP.zip"
  COPYFILE_DISABLE=1 zip -qr "$OUT_DIR/hedgemate-professor-front-dist-contents-$STAMP.zip" .
)

cp "$PACKAGE_ROOT/deploy/professor-server/README.md" "$OUT_DIR/PROFESSOR_SERVER_DEPLOY_README.md"
cp "$PACKAGE_ROOT/deploy/professor-server/BEECAST_PUBLIC_INTEGRATED_QA.md" "$OUT_DIR/BEECAST_PUBLIC_INTEGRATED_QA.md"
cp "$PACKAGE_ROOT/deploy/professor-server/GITHUB_RELEASE_STRATEGY.md" "$OUT_DIR/GITHUB_RELEASE_STRATEGY.md"
cp "$PACKAGE_ROOT/deploy/professor-server/GOAL_COMPLETION_AUDIT.md" "$OUT_DIR/GOAL_COMPLETION_AUDIT.md"
cp "$PACKAGE_ROOT/deploy/professor-server/ROLLBACK_CHECKLIST.md" "$OUT_DIR/ROLLBACK_CHECKLIST.md"
cp "$PACKAGE_ROOT/deploy/professor-server/SERVER_ACCESS_REQUIREMENTS.md" "$OUT_DIR/SERVER_ACCESS_REQUIREMENTS.md"
cp "$PACKAGE_ROOT/HedgeMate/outputs/reports/server_deploy_restore_qa_20260611.md" "$OUT_DIR/SERVER_DEPLOY_RESTORE_QA.md"

shasum -a 256 "$OUT_DIR"/*.tar.gz "$OUT_DIR"/*.zip > "$OUT_DIR/SHA256SUMS.txt"
echo "$OUT_DIR"
