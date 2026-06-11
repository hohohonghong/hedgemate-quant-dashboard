# Rollback Checklist

Use this if professor-server deployment is unstable or public QA fails.

## Immediate Rollback

1. Keep the protected local backend running:

   ```text
   http://127.0.0.1:8766
   ```

2. Keep the current Bee-cast frontend live:

   ```text
   https://hedgemate.eyefeet.com
   ```

3. If nginx/proxy was changed on professor server, revert `/api` routing to the previous working target or disable the new site.

4. Stop only the failed professor-server backend service:

   ```bash
   sudo systemctl stop hedgemate-backend
   ```

   If using Docker:

   ```bash
   cd deploy/professor-server/docker
   docker compose down
   ```

5. Do not delete the failed deployment directory until logs and QA output are collected.

## Evidence To Save

```bash
sudo systemctl status hedgemate-backend --no-pager
sudo journalctl -u hedgemate-backend -n 300 --no-pager
curl -fsS http://127.0.0.1:8766/api/status
curl -fsS http://127.0.0.1:8766/api/scenario-dashboard
```

Do not print or paste secret values.

## Known-Good Local Backup

Original protected local working copy:

```text
/tmp/hedgemate-beecast-fix
```

Known-good backup archive:

```text
/Users/seokmin/Downloads/hedgemate-beecast-release-20260611T1715KST/hedgemate-beecast-full-portable-20260611T1715KST.tar.gz
```

Professor-server trial archive:

```text
/Users/seokmin/Downloads/hedgemate-professor-server-trial-20260611T173057KST/hedgemate-professor-full-portable-20260611T173057KST.tar.gz
```

## Redeploy From A Clean Directory

```bash
sudo mkdir -p /opt/hedgemate/releases
cd /opt/hedgemate/releases
sudo tar -xzf hedgemate-professor-full-portable-YYYYMMDDTHHMMSSKST.tar.gz
sudo ln -sfn /opt/hedgemate/releases/hedgemate-beecast-fix /opt/hedgemate/current
```

Then recreate `.secrets/gemini_api_key.txt`, install dependencies, rebuild frontend, and run:

```bash
python deploy/professor-server/qa_professor_server.py --api-base http://127.0.0.1:8766/api --root /opt/hedgemate/current/hedgemate-beecast-fix
```

If the QA script fails on `REFRESHING`, wait for startup refresh to settle or rerun with a larger wait window:

```bash
python deploy/professor-server/qa_professor_server.py --wait-seconds 600 --api-base http://127.0.0.1:8766/api --root /opt/hedgemate/current/hedgemate-beecast-fix
```
