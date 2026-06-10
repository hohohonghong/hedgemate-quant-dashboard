#!/usr/bin/env python3
import argparse
import mimetypes
import os
import urllib.error
import urllib.parse
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DIST_DIR = ROOT / "hedge-front" / "dist"
DEFAULT_CORS_ORIGINS = {
    "https://hedgemate.eyefeet.com",
    "https://hedgemate-front.eyefeet.com",
}


def configured_cors_origins():
    raw = os.environ.get("HEDGEMATE_CORS_ORIGINS", "")
    values = {item.strip().rstrip("/") for item in raw.split(",") if item.strip()}
    return DEFAULT_CORS_ORIGINS | values


class FrontendHandler(BaseHTTPRequestHandler):
    api_base = "http://127.0.0.1:8766"
    cors_origins = configured_cors_origins()

    def log_message(self, format, *args):
        return

    def do_GET(self):
        if self.path.startswith("/api/"):
            return self.proxy_api()
        return self.serve_static()

    def do_POST(self):
        if self.path.startswith("/api/"):
            return self.proxy_api()
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_PUT(self):
        if self.path.startswith("/api/"):
            return self.proxy_api()
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_PATCH(self):
        if self.path.startswith("/api/"):
            return self.proxy_api()
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_DELETE(self):
        if self.path.startswith("/api/"):
            return self.proxy_api()
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_cors_headers()
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
        self.end_headers()

    def cors_origin(self):
        origin = (self.headers.get("Origin") or "").strip().rstrip("/")
        if not origin:
            return None
        return origin if origin in self.cors_origins else None

    def send_cors_headers(self):
        origin = self.cors_origin()
        if not origin:
            return
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Vary", "Origin")

    def proxy_api(self):
        target = self.api_base.rstrip("/") + self.path
        body = None
        if self.command in {"POST", "PUT", "PATCH", "DELETE"}:
            length = int(self.headers.get("Content-Length") or "0")
            body = self.rfile.read(length) if length else b""
        headers = {}
        content_type = self.headers.get("Content-Type")
        if content_type:
            headers["Content-Type"] = content_type
        cookie = self.headers.get("Cookie")
        if cookie:
            headers["Cookie"] = cookie
        request = urllib.request.Request(target, data=body, method=self.command, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = response.read()
                self.send_response(response.status)
                self.send_header("Content-Type", response.headers.get("Content-Type", "application/json"))
                self.send_cors_headers()
                for cookie_value in response.headers.get_all("Set-Cookie", []):
                    self.send_header("Set-Cookie", cookie_value)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
        except urllib.error.HTTPError as exc:
            payload = exc.read()
            self.send_response(exc.code)
            self.send_header("Content-Type", exc.headers.get("Content-Type", "application/json"))
            self.send_cors_headers()
            for cookie_value in exc.headers.get_all("Set-Cookie", []) if exc.headers else []:
                self.send_header("Set-Cookie", cookie_value)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except Exception as exc:
            payload = f'{{"error":"frontend proxy failed: {exc}"}}'.encode("utf-8")
            self.send_response(HTTPStatus.BAD_GATEWAY)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_cors_headers()
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    def serve_static(self):
        if not DIST_DIR.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "hedge-front/dist is missing. Run npm run build first.")
            return
        path = urllib.parse.urlparse(self.path).path
        rel = path.lstrip("/") or "index.html"
        candidate = (DIST_DIR / rel).resolve()
        if not str(candidate).startswith(str(DIST_DIR.resolve())):
            self.send_error(HTTPStatus.FORBIDDEN, "Forbidden")
            return
        if candidate.is_dir():
            candidate = candidate / "index.html"
        if not candidate.exists():
            candidate = DIST_DIR / "index.html"
        data = candidate.read_bytes()
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    parser = argparse.ArgumentParser(description="Serve built HedgeMate frontend with /api proxy")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5173)
    parser.add_argument("--api-base", default="http://127.0.0.1:8766")
    args = parser.parse_args()
    FrontendHandler.api_base = args.api_base
    server = ThreadingHTTPServer((args.host, args.port), FrontendHandler)
    print(f"HedgeMate frontend running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
