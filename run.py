#!/usr/bin/env python3
"""Start HedgeMate backend and built frontend together."""

import argparse
import json
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "runtime_logs"
PID_PATH = LOG_DIR / "pids.json"


def is_port_listening(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", int(port))) == 0


def choose_port(requested_port, strict=False):
    if not is_port_listening(requested_port):
        return requested_port
    if strict:
        raise SystemExit(f"Port {requested_port} is already in use.")
    for port in range(requested_port + 1, requested_port + 100):
        if not is_port_listening(port):
            print(f"Port {requested_port} is already in use. Using {port} instead.")
            return port
    raise SystemExit(f"No free port found near {requested_port}.")


def wait_for_url(url, timeout_seconds=20):
    deadline = time.time() + timeout_seconds
    last_error = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                if response.status < 500:
                    return True
        except Exception as exc:
            last_error = exc
        time.sleep(0.5)
    raise RuntimeError(f"Timed out waiting for {url}: {last_error}")


def local_lan_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return None


def start_process(args, cwd, stdout_path, stderr_path):
    stdout = stdout_path.open("ab")
    stderr = stderr_path.open("ab")
    try:
        process = subprocess.Popen(
            args,
            cwd=str(cwd),
            stdout=stdout,
            stderr=stderr,
            stdin=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )
    finally:
        stdout.close()
        stderr.close()
    return process


def main():
    parser = argparse.ArgumentParser(description="Run HedgeMate backend and frontend.")
    parser.add_argument("--backend-port", type=int, default=8766)
    parser.add_argument("--frontend-port", type=int, default=5173)
    parser.add_argument(
        "--frontend-host",
        default="127.0.0.1",
        help="Use 0.0.0.0 when another computer on the same network should open the app.",
    )
    parser.add_argument("--strict-ports", action="store_true", help="Fail instead of choosing another port.")
    parser.add_argument("--no-browser", action="store_true", help="Do not open the browser automatically.")
    args = parser.parse_args()

    dist_index = ROOT / "hedge-front" / "dist" / "index.html"
    if not dist_index.exists():
        raise SystemExit(
            "hedge-front/dist is missing. Build it first:\n"
            "  cd hedge-front\n"
            "  npm ci\n"
            "  npm run build\n"
            "  cd .."
        )

    args.backend_port = choose_port(args.backend_port, strict=args.strict_ports)
    args.frontend_port = choose_port(args.frontend_port, strict=args.strict_ports)

    LOG_DIR.mkdir(exist_ok=True)
    backend = None
    frontend = None
    try:
        backend = start_process(
            [
                sys.executable,
                "scripts/serve_dashboard.py",
                "--host",
                "127.0.0.1",
                "--port",
                str(args.backend_port),
            ],
            ROOT / "HedgeMate",
            LOG_DIR / "backend.out.log",
            LOG_DIR / "backend.err.log",
        )
        wait_for_url(f"http://127.0.0.1:{args.backend_port}/api/health")

        frontend = start_process(
            [
                sys.executable,
                "serve_frontend.py",
                "--host",
                args.frontend_host,
                "--port",
                str(args.frontend_port),
                "--api-base",
                f"http://127.0.0.1:{args.backend_port}",
            ],
            ROOT,
            LOG_DIR / "frontend.out.log",
            LOG_DIR / "frontend.err.log",
        )
        wait_for_url(f"http://127.0.0.1:{args.frontend_port}/")

        PID_PATH.write_text(
            json.dumps(
                {
                    "backend": {"pid": backend.pid, "port": args.backend_port},
                    "frontend": {"pid": frontend.pid, "port": args.frontend_port},
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        (LOG_DIR / "backend.pid").write_text(str(backend.pid), encoding="utf-8")
        (LOG_DIR / "frontend.pid").write_text(str(frontend.pid), encoding="utf-8")

        print("HedgeMate started.")
        print(f"Frontend: http://localhost:{args.frontend_port}")
        print(f"Backend : http://127.0.0.1:{args.backend_port}")
        if args.frontend_host == "0.0.0.0":
            ip = local_lan_ip()
            if ip:
                print(f"LAN URL : http://{ip}:{args.frontend_port}")
        print(f"Logs    : {LOG_DIR}")
        print("Stop with: python stop.py")
        if not args.no_browser:
            webbrowser.open(f"http://127.0.0.1:{args.frontend_port}")
    except Exception:
        for process in (frontend, backend):
            if process and process.poll() is None:
                process.terminate()
        raise


if __name__ == "__main__":
    main()
