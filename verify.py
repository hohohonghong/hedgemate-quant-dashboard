#!/usr/bin/env python3
import argparse
import json
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def run(command, cwd=ROOT):
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=str(cwd), check=True)


def request_json(url, timeout=10):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def request_text(url, timeout=10):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def assert_file(path, message):
    if not path.exists():
        raise SystemExit(message)


def verify_runtime(backend_port, frontend_port):
    dist_index = ROOT / "hedge-front" / "dist" / "index.html"
    assert_file(ROOT / "HedgeMate" / "outputs" / "latest_manifest.json", "Missing HedgeMate output manifest.")
    assert_file(ROOT / "scenario_research" / "outputs" / "latest_manifest.json", "Missing scenario output manifest.")
    assert_file(
        ROOT
        / "scenario_research"
        / "outputs"
        / "validation"
        / "historical_validation_cases_phase10a-wave5-20260514.csv",
        "Missing scenario historical validation cases required by run_scenario_backtest.py.",
    )
    try:
        run(
            [
                sys.executable,
                "run.py",
                "--backend-port",
                str(backend_port),
                "--frontend-port",
                str(frontend_port),
                "--strict-ports",
                "--no-browser",
            ]
        )
        assert_file(dist_index, "Missing hedge-front/dist/index.html after run.py launch.")
        index_html = dist_index.read_text(encoding="utf-8")
        main_script = re.search(r'<script[^>]+src="(/assets/index-[^"]+\.js)"', index_html)
        if not main_script:
            raise SystemExit("Frontend index.html does not reference the main /assets/index-*.js bundle.")
        assert_file(ROOT / "hedge-front" / "dist" / main_script.group(1).lstrip("/"), "Missing frontend main JS bundle.")

        status = request_json(f"http://127.0.0.1:{backend_port}/api/status", timeout=60)
        if not status.get("ok"):
            raise RuntimeError(f"Backend status is not ok: {status}")
        product = request_json(f"http://127.0.0.1:{backend_port}/api/product-dashboard", timeout=90)
        if not (product.get("hedgeActionPlan") or product.get("hedgeActionCandidates")):
            raise RuntimeError("Product dashboard did not include hedge output data.")
        html = request_text(f"http://127.0.0.1:{frontend_port}/")
        if "<!doctype html" not in html.lower():
            raise RuntimeError("Frontend did not serve the built app.")
        print("Runtime verification complete: backend, product output, and frontend are reachable.")
    finally:
        subprocess.run([sys.executable, "stop.py"], cwd=str(ROOT), check=False)


def verify_full_build():
    try:
        import pytest  # noqa: F401
    except ImportError:
        raise SystemExit("pytest is missing. Install it with: python -m pip install -r requirements.txt")

    run([sys.executable, "-m", "pytest", "-q"])

    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if not npm:
        raise SystemExit("npm is missing. Install Node.js to rebuild the frontend.")

    front_dir = ROOT / "hedge-front"
    if not (front_dir / "node_modules").exists():
        run([npm, "ci"], front_dir)
    run([npm, "run", "build"], front_dir)
    print("Full verification complete: Python tests + frontend build.")


def main():
    parser = argparse.ArgumentParser(description="Verify the HedgeMate shared package.")
    parser.add_argument("--backend-port", type=int, default=18766)
    parser.add_argument("--frontend-port", type=int, default=15173)
    parser.add_argument("--full", action="store_true", help="Also run pytest and rebuild the frontend with npm.")
    args = parser.parse_args()

    verify_runtime(args.backend_port, args.frontend_port)
    if args.full:
        verify_full_build()


if __name__ == "__main__":
    main()
