#!/usr/bin/env python3
"""Stop HedgeMate processes started by run.py."""

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "runtime_logs"
PID_PATH = LOG_DIR / "pids.json"


def stop_pid(pid):
    if not pid:
        return
    pid = int(pid)
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return
    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(0.5)
    except ProcessLookupError:
        return
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return
    os.kill(pid, signal.SIGKILL)


def read_pids():
    pids = []
    if PID_PATH.exists():
        try:
            data = json.loads(PID_PATH.read_text(encoding="utf-8"))
            for key in ("frontend", "backend"):
                pid = (data.get(key) or {}).get("pid")
                if pid:
                    pids.append(pid)
        except Exception:
            pass
    for name in ("frontend.pid", "backend.pid"):
        path = LOG_DIR / name
        if path.exists():
            try:
                pids.append(int(path.read_text(encoding="utf-8").strip()))
            except Exception:
                pass
    return list(dict.fromkeys(pids))


def main():
    for pid in read_pids():
        stop_pid(pid)
    for path in (PID_PATH, LOG_DIR / "frontend.pid", LOG_DIR / "backend.pid"):
        try:
            path.unlink()
        except FileNotFoundError:
            pass
    print("HedgeMate processes stopped.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
