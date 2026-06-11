#!/usr/bin/env python3
"""Bee-cast deployment entrypoint for HedgeMate.

This process exposes one public HTTP port, serves the built frontend, and
proxies /api requests to the existing local HedgeMate backend.
"""

import os
import json
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
TRUTHY_VALUES = {"1", "true", "yes", "on"}
EXTERNAL_API_ENV_KEYS = (
    "HEDGEMATE_EXTERNAL_API_BASE",
    "HEDGEMATE_PUBLIC_BACKEND_URL",
    "HEDGEMATE_FRONTEND_API_BASE",
    "VITE_HEDGEMATE_API_URL",
)


def writable_check(path):
    target = Path(path)
    result = {"path": str(target), "exists": target.exists(), "writable": False}
    probe = None
    try:
        target.mkdir(parents=True, exist_ok=True)
        probe = target / f".write_check_{os.getpid()}_{int(time.time() * 1000)}.tmp"
        probe.write_text("ok", encoding="utf-8")
        result.update({"exists": True, "writable": True})
    except Exception as exc:
        result["error"] = str(exc)[:500]
    finally:
        if probe:
            try:
                probe.unlink(missing_ok=True)
            except OSError:
                pass
    return result


def startup_diagnostics():
    backend_root = ROOT / "HedgeMate"
    scenario_root = ROOT / "scenario_research"
    return {
        "processCwd": os.getcwd(),
        "deployRoot": str(ROOT),
        "backendCwd": str(backend_root),
        "scenarioResearchRoot": str(scenario_root),
        "publicPort": PUBLIC_PORT,
        "backendPort": BACKEND_PORT,
        "writable": {
            "hedgemateOutputs": writable_check(backend_root / "outputs"),
            "hedgemateInputs": writable_check(backend_root / "inputs"),
            "hedgemateRunInputs": writable_check(backend_root / "outputs" / "run_inputs"),
            "scenarioResearchOutputs": writable_check(scenario_root / "outputs"),
        },
    }


def log_startup_diagnostics():
    print(
        "Bee-cast HedgeMate startup: "
        + json.dumps(startup_diagnostics(), ensure_ascii=False),
        flush=True,
    )


def startup_refresh_disabled():
    if os.environ.get("HEDGEMATE_NO_STARTUP_REFRESH", "").strip().lower() in NO_STARTUP_REFRESH_VALUES:
        return True
    return os.environ.get("HEDGEMATE_ENABLE_STARTUP_REFRESH", "").strip().lower() not in ENABLE_STARTUP_REFRESH_VALUES


def external_api_base():
    for key in EXTERNAL_API_ENV_KEYS:
        value = os.environ.get(key, "").strip()
        if value:
            return value.rstrip("/")
    return ""


def frontend_only_mode():
    if os.environ.get("HEDGEMATE_BEECAST_FRONTEND_ONLY", "").strip().lower() in TRUTHY_VALUES:
        return True
    return bool(external_api_base())


def start_backend():
    backend_env = os.environ.copy()
    backend_env.pop("HEDGEMATE_SERVER_SAFE_MODE", None)
    backend_env.setdefault("HEDGEMATE_SCHEDULER_INITIAL_DELAY_SECONDS", "0")
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

    log_startup_diagnostics()
    external_api = external_api_base()
    if frontend_only_mode():
        if not external_api:
            raise SystemExit("HEDGEMATE_BEECAST_FRONTEND_ONLY requires HEDGEMATE_EXTERNAL_API_BASE.")
        subprocess.run(
            [
                sys.executable,
                "serve_frontend.py",
                "--host",
                "0.0.0.0",
                "--port",
                str(PUBLIC_PORT),
                "--api-base",
                external_api,
                "--frontend-api-base",
                external_api,
            ],
            cwd=str(ROOT),
            check=True,
        )
        return

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
