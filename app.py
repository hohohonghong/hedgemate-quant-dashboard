#!/usr/bin/env python3
"""Bee-cast deployment entrypoint for HedgeMate.

This process exposes one public HTTP port, serves the built frontend, and
proxies /api requests to the existing local HedgeMate backend.
"""

import os
import signal
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PUBLIC_PORT = int(os.environ.get("PORT", "8000"))
BACKEND_PORT = int(os.environ.get("BACKEND_PORT", "8766"))
NO_STARTUP_REFRESH_VALUES = {"1", "true", "yes", "on"}
ENABLE_STARTUP_REFRESH_VALUES = {"1", "true", "yes", "on"}


def startup_refresh_disabled():
    if os.environ.get("HEDGEMATE_NO_STARTUP_REFRESH", "").strip().lower() in NO_STARTUP_REFRESH_VALUES:
        return True
    return os.environ.get("HEDGEMATE_ENABLE_STARTUP_REFRESH", "").strip().lower() not in ENABLE_STARTUP_REFRESH_VALUES


def start_backend():
    backend_env = os.environ.copy()
    backend_env.setdefault("HEDGEMATE_SERVER_SAFE_MODE", "1")
    command = [
        sys.executable,
        "scripts/serve_dashboard.py",
        "--host",
        "127.0.0.1",
        "--port",
        str(BACKEND_PORT),
    ]
    if startup_refresh_disabled():
        command.append("--no-startup-refresh")
    return subprocess.Popen(
        command,
        cwd=str(ROOT / "HedgeMate"),
        env=backend_env,
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


def backend_supervisor(get_backend, set_backend, stop_event):
    while not stop_event.wait(5):
        backend = get_backend()
        if backend is not None and backend.poll() is None:
            continue
        if stop_event.is_set():
            return
        replacement = start_backend()
        set_backend(replacement)
        try:
            wait_for_backend(timeout_seconds=30)
        except Exception as exc:
            print(f"Backend restart health check failed: {exc}", file=sys.stderr, flush=True)


def main():
    dist_index = ROOT / "hedge-front" / "dist" / "index.html"
    if not dist_index.exists():
        raise SystemExit("Missing hedge-front/dist/index.html. Commit the prebuilt frontend before deploying.")

    backend_lock = threading.Lock()
    stop_event = threading.Event()
    backend = start_backend()

    def get_backend():
        with backend_lock:
            return backend

    def set_backend(value):
        nonlocal backend
        with backend_lock:
            backend = value

    def stop(*_):
        stop_event.set()
        current_backend = get_backend()
        if current_backend is not None and current_backend.poll() is None:
            current_backend.terminate()
            try:
                current_backend.wait(timeout=10)
            except subprocess.TimeoutExpired:
                current_backend.kill()
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    try:
        wait_for_backend()
        threading.Thread(
            target=backend_supervisor,
            args=(get_backend, set_backend, stop_event),
            daemon=True,
        ).start()
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
        stop_event.set()
        current_backend = get_backend()
        if current_backend is not None and current_backend.poll() is None:
            current_backend.terminate()


if __name__ == "__main__":
    main()
