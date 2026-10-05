"""Serve a local dashboard over the existing diagnostic report."""

import argparse
import json
import subprocess
import sys
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from urllib.parse import urlsplit

_STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/assets/dashboard.css": ("dashboard.css", "text/css; charset=utf-8"),
    "/assets/dashboard.js": ("dashboard.js", "text/javascript; charset=utf-8"),
}
_HEALTH_PENALTIES = {"error": 25, "high": 15, "warning": 10}


def calculate_health(findings: object) -> tuple[int | None, str]:
    """Score error -25, high -15, warning -10, info -0; >=95 healthy, >=70 warning."""
    if not isinstance(findings, list) or not findings:
        return None, "Not available"

    penalty = sum(
        _HEALTH_PENALTIES.get(finding.get("severity"), 0)
        for finding in findings
        if isinstance(finding, dict)
    )
    score = max(0, 100 - penalty)
    if score >= 95:
        return score, "Healthy"
    if score >= 70:
        return score, "Warning"
    return score, "Critical"


class DashboardRequestHandler(BaseHTTPRequestHandler):
    """Serve static dashboard files and the existing CLI JSON report."""

    def __init__(
        self,
        *args: object,
        project_directory: Path,
        **kwargs: object,
    ) -> None:
        self.project_directory = project_directory
        super().__init__(*args, **kwargs)

    def do_GET(self) -> None:
        route = urlsplit(self.path).path
        if route == "/health":
            self._send_body(
                200,
                b'{"status":"ok"}',
                "application/json; charset=utf-8",
            )
            return
        if route in {"/api/report", "/api/report/download"}:
            self._send_report(download=route.endswith("/download"))
            return

        asset = _STATIC_FILES.get(route)
        if asset is None:
            self._send_body(404, b"Not found", "text/plain; charset=utf-8")
            return

        filename, content_type = asset
        try:
            body = files("devenv_doctor").joinpath("web", filename).read_bytes()
        except OSError:
            self._send_body(
                500,
                b"Dashboard assets are unavailable.",
                "text/plain; charset=utf-8",
            )
            return
        self._send_body(200, body, content_type)

    def _send_report(self, download: bool = False) -> None:
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "devenv_doctor.cli",
                    "doctor",
                    "--json",
                ],
                cwd=self.project_directory,
                capture_output=True,
                check=False,
                text=True,
                timeout=60,
            )
            report = json.loads(result.stdout)
            if not isinstance(report, dict) or not isinstance(
                report.get("findings"), list
            ):
                raise ValueError("Invalid diagnostic report")
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError, ValueError):
            self._send_body(
                502,
                b'{"error":"Unable to generate diagnostic report."}',
                "application/json; charset=utf-8",
            )
            return

        score, status = calculate_health(report["findings"])
        extra_headers = {
            "X-DevEnv-Health-Score": (
                str(score) if score is not None else "not-available"
            ),
            "X-DevEnv-Health-Status": status,
        }
        if download:
            extra_headers["Content-Disposition"] = (
                'attachment; filename="devenv-doctor-report.json"'
            )
        self._send_body(
            200,
            result.stdout.encode("utf-8"),
            "application/json; charset=utf-8",
            extra_headers,
        )

    def _send_body(
        self,
        status: int,
        body: bytes,
        content_type: str,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; connect-src 'self'; style-src 'self'; "
            "script-src 'self'; img-src 'self' data:; object-src 'none'; "
            "base-uri 'none'; frame-ancestors 'none'",
        )
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format_string: str, *args: object) -> None:
        print(f"{self.address_string()} - {format_string % args}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the local DevEnv Doctor dashboard."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    project_directory = Path.cwd()
    handler = partial(
        DashboardRequestHandler,
        project_directory=project_directory,
    )
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"DevEnv Doctor dashboard: http://{args.host}:{args.port}")
    print(f"Scanning project: {project_directory}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Dashboard stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
