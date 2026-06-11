# GitHub And Release Strategy

Use GitHub for reproducible source control, not as a dumping ground for bulky generated outputs.

## Put In Normal Git

- `HedgeMate/scripts`
- `HedgeMate/tests`
- `HedgeMate/web`
- `scenario_research/scripts`
- `scenario_research/tests`
- `hedge-front/src`
- `hedge-front/public`
- `hedge-front/scripts`
- `hedge-front/package.json`
- `hedge-front/package-lock.json`
- `requirements.txt`
- `deploy/professor-server`
- `deploy/professor-server/docker`
- README/runbook files

## Keep Out Of Normal Git

- `.secrets`
- `.venv`
- `node_modules`
- `hedge-front/dist` unless intentionally committing a small static snapshot
- large/generated `HedgeMate/outputs`
- large/generated `scenario_research/outputs`
- local databases and cache files

GitHub regular Git rejects files over 100 MiB and repositories become painful well before they are technically rejected. Keep the repo small; store verified portable snapshots as GitHub Release assets or external archives.

## Release Assets

Attach these to a dated GitHub Release when preserving a known-good deployment:

- `hedgemate-professor-full-portable-YYYYMMDDTHHMMSSKST.tar.gz`
- `hedgemate-professor-front-dist-contents-YYYYMMDDTHHMMSSKST.zip`
- `SHA256SUMS.txt`
- `SERVER_DEPLOY_RESTORE_QA.md`
- `PROFESSOR_SERVER_DEPLOY_README.md`
- `BEECAST_PUBLIC_INTEGRATED_QA.md`
- `GOAL_COMPLETION_AUDIT.md`
- `SERVER_ACCESS_REQUIREMENTS.md`
- `GITHUB_RELEASE_STRATEGY.md`
- `ROLLBACK_CHECKLIST.md`

The full portable archive should exclude secrets, virtualenvs, `node_modules`, `.git`, and pycache files.

## Recommended Release Notes

```text
HedgeMate professor-server trial package

Validated:
- backend restore and startup
- scheduler running
- 150-asset universe
- Gemini news overlay
- frontend build
- same-origin /api runtime config
- public Bee-cast /api QA passed
- candidate/backtest artifacts present
- qa_professor_server.py automation included
- systemd/nginx and Docker Compose deployment options included

Secrets are not included. Recreate .secrets/gemini_api_key.txt on the target server.
```

## Local Verification Before Upload

```bash
shasum -a 256 -c SHA256SUMS.txt
tar -tzf hedgemate-professor-full-portable-*.tar.gz | grep -E '(.secrets|node_modules|.venv|gemini_api_key)' && echo "BAD" || echo "OK"
zipinfo -1 hedgemate-professor-front-dist-contents-*.zip | grep -E '(.secrets|node_modules|gemini_api_key)' && echo "BAD" || echo "OK"
```

## Suggested Upload Pattern

1. Push only source/config/runbooks to GitHub.
2. Create a dated Release.
3. Attach the portable tarball, frontend zip, SHA file, QA reports, deploy README, goal audit, server access notes, rollback checklist, and release strategy document.
4. On the target server, download the Release tarball, verify SHA, extract into a fresh directory, recreate `.secrets/gemini_api_key.txt`, then run `install_on_server.sh` or Docker Compose.
