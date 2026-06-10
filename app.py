#!/usr/bin/env python3
"""Bee-cast deployment entrypoint for HedgeMate.

This process exposes one public HTTP port, serves the built frontend, and
proxies /api requests to the existing local HedgeMate backend.
"""

import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PUBLIC_PORT = int(os.environ.get("PORT", "8000"))
BACKEND_PORT = int(os.environ.get("BACKEND_PORT", "8766"))


def start_backend():
    return subprocess.Popen(
        [
            sys.executable,
            "scripts/serve_dashboard.py",
            "--host",
            "127.0.0.1",
            "--port",
            str(BACKEND_PORT),
            "--no-startup-refresh",
        ],
        cwd=str(ROOT / "HedgeMate"),
        stdin=subprocess.DEVNULL,
    )


def wait_for_backend(timeout_seconds=45):
    deadline = time.time() + timeout_seconds
    last_error = None
    health_url = f"http://127.0.0.1:{BACKEND_PORT}/api/health"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(health_url, timeout=3) as response:
                if response.status < 500:
                    return
        except Exception as exc:
            last_error = exc
        time.sleep(0.5)
    raise RuntimeError(f"Timed out waiting for backend at {health_url}: {last_error}")


def main():
    dist_index = ROOT / "hedge-front" / "dist" / "index.html"
    if not dist_index.exists():
        raise SystemExit("Missing hedge-front/dist/index.html. Commit the prebuilt frontend before deploying.")

    backend = start_backend()

    def stop(*_):
        if backend.poll() is None:
            backend.terminate()
            try:
                backend.wait(timeout=10)
            except subprocess.TimeoutExpired:
                backend.kill()
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    try:
        wait_for_backend()
        subprocess.run(
            [
                sys.executable,
                "serve_frontend.py",
                "--host",
                "0.0.0.0",
                "--port",
                str(PUBLIC_PORT),
                "--api-base",
                f"http://127.0.0.1:{BACKEND_PORT}",
            ],
            cwd=str(ROOT),
            check=True,
        )
    finally:
        if backend.poll() is None:
            backend.terminate()


if __name__ == "__main__":
    main()
