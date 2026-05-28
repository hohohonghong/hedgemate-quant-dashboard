#!/usr/bin/env python3
"""Refresh HedgeMate market data through the local backend API."""

import argparse
import json
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "runtime_logs"


def is_port_listening(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", int(port))) == 0


def request_json(url, method="GET", payload=None, timeout=30):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def api_ok(base_url):
    try:
        return bool(request_json(f"{base_url}/api/health", timeout=5).get("ok"))
    except Exception:
        return False


def start_backend(port):
    LOG_DIR.mkdir(exist_ok=True)
    stdout = (LOG_DIR / "market-refresh-backend.out.log").open("ab")
    stderr = (LOG_DIR / "market-refresh-backend.err.log").open("ab")
    try:
        process = subprocess.Popen(
            [sys.executable, "scripts/serve_dashboard.py", "--host", "127.0.0.1", "--port", str(port)],
            cwd=str(ROOT / "HedgeMate"),
            stdout=stdout,
            stderr=stderr,
            stdin=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )
    finally:
        stdout.close()
        stderr.close()
    return process


def wait_for_api(base_url, timeout_seconds=20):
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if api_ok(base_url):
            return
        time.sleep(0.5)
    raise RuntimeError(f"Could not start HedgeMate API at {base_url}. Check runtime_logs.")


def stop_process(process):
    if process and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def main():
    parser = argparse.ArgumentParser(description="Refresh HedgeMate market data.")
    parser.add_argument("--mode", choices=["market_data_only", "full_rebuild"], default="market_data_only")
    parser.add_argument("--backend-port", type=int, default=8766)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    base_url = f"http://127.0.0.1:{args.backend_port}"
    backend = None
    started_backend = False

    if not api_ok(base_url):
        if is_port_listening(args.backend_port):
            raise SystemExit(f"Port {args.backend_port} is in use, but HedgeMate API did not respond.")
        backend = start_backend(args.backend_port)
        started_backend = True
        wait_for_api(base_url)

    try:
        payload = {
            "mode": args.mode,
            "force": args.force,
            "forceFullRefresh": args.force or args.mode == "full_rebuild",
        }
        job = request_json(f"{base_url}/api/refresh-market-data", method="POST", payload=payload)
        if job.get("status") == "skipped_latest":
            print("Market refresh skipped: latest available data is already active.")
            return
        job_id = job.get("jobId")
        if not job_id:
            raise RuntimeError("Refresh API did not return a jobId.")

        while True:
            time.sleep(2)
            job = request_json(f"{base_url}/api/run-status?job_id={job_id}", timeout=10)
            print(
                "status={status} stage={stage} step={step}".format(
                    status=job.get("status"),
                    stage=job.get("stage"),
                    step=job.get("currentStep"),
                )
            )
            if job.get("status") not in {"queued", "running"}:
                break

        if job.get("status") not in {"completed", "skipped_latest"}:
            raise RuntimeError(job.get("error") or "unknown refresh failure")

        print()
        print(f"Market refresh finished: {job.get('status')}")
        result = job.get("result") or {}
        for key in ("latestMarketDate", "rawPath", "warning", "reason"):
            if result.get(key):
                print(f"{key}: {result[key]}")
    finally:
        if started_backend:
            stop_process(backend)


if __name__ == "__main__":
    main()
