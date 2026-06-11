# Docker Deployment Option

Use this only if the professor server supports Docker Compose.

From the package root:

```bash
mkdir -p .secrets
printf '%s\n' 'PASTE_GEMINI_API_KEY_HERE' > .secrets/gemini_api_key.txt
chmod 600 .secrets/gemini_api_key.txt

cd deploy/professor-server/docker
docker compose up --build -d
```

Default local endpoint:

```text
http://SERVER_IP:8080
http://SERVER_IP:8080/api/health
```

For production HTTPS, put a host nginx/Caddy/ALB in front of port `8080`.

Post-deploy QA from the package root:

```bash
python deploy/professor-server/qa_professor_server.py --api-base http://127.0.0.1:8080/api --root .
```

Secrets are mounted from `.secrets` and are not baked into images.

The package root includes `.dockerignore` so `.secrets`, `.venv`, `node_modules`, Git metadata, and pycache files are not sent in the Docker build context.
