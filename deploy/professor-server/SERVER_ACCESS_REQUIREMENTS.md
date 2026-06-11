# Server Access Requirements

To finish the actual professor-server deployment, collect these details first.

## Required

- SSH host/IP
- SSH user
- Authentication method already available on this computer, or instructions for key/password use
- Whether `sudo` is available
- Preferred install path, or approval to use:

  ```text
  /opt/hedgemate/current/hedgemate-beecast-fix
  ```

- Public domain/subdomain to serve HedgeMate
- Whether this server controls `hedgemate.eyefeet.com` or another domain
- Existing web server stack: nginx, Caddy, Apache, cloud reverse proxy, or none
- TLS certificate method: existing cert, Let's Encrypt, or external load balancer
- Whether Docker Compose is allowed
- Whether outbound HTTPS is allowed for:
  - Yahoo/market data
  - Google News/RSS
  - Gemini API

## Required Secret Setup

Gemini key must be provided on the server as a file, not pasted into logs:

```bash
mkdir -p .secrets
printf '%s\n' 'PASTE_GEMINI_API_KEY_HERE' > .secrets/gemini_api_key.txt
chmod 600 .secrets/gemini_api_key.txt
```

Do not send the key through chat or commit it to Git.

## Preferred Deployment Shape

```text
public HTTPS host
  ├─ /api/* -> 127.0.0.1:8766 backend
  └─ /*     -> hedge-front/dist static frontend
```

Backend should bind to `127.0.0.1:8766` under systemd, unless Docker is chosen.

## Post-Deploy QA

From the deployed package root:

```bash
python deploy/professor-server/qa_professor_server.py \
  --api-base https://YOUR_PUBLIC_HOST/api \
  --root .
```

Required pass criteria:

- 150 assets
- `serverSafeMode=false`
- scheduler running
- today KST market nowcast
- Gemini news provider with no fallback
- real Top5 news URLs
- candidates/backtests present
- placeholder/typo strings absent
