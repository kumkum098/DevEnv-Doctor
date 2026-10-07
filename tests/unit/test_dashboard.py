import json
import threading
from functools import partial
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
from urllib.request import urlopen

import pytest

from devenv_doctor import dashboard


@pytest.fixture
def dashboard_server(monkeypatch, tmp_path):
    finding = {
        "id": "DEPENDENCY_VERSION_MISMATCH",
        "category": "dependency",
        "title": "Dependency mismatch",
        "severity": "high",
        "evidence": (
            "Package: example-package",
            "Required: >=2",
            "Installed: 1.0",
        ),
        "confidence": "Very high",
        "recommended_action": "Upgrade example-package to a compatible version.",
        "validation_command": "python -m pip show example-package",
    }
    environment_value = "dashboard-test-value-must-not-be-returned"
    report = {
        "findings": [finding],
        "summary": {"errors": 0, "warnings": 1, "info": 0},
        "environment_summary": {
            "runtime": {
                "python_version": "3.14.0",
                "executable_path": "fixture-python",
                "operating_system": "FixtureOS",
                "architecture": "test-arch",
                "virtual_env_active": True,
                "virtual_env_path": ".venv",
            },
            "project": {"is_python_project": True, "markers": ["pyproject.toml"]},
            "virtual_environment": {"active": True, "path": ".venv"},
        },
        "environment_variables": {
            "variables": [
                {
                    "name": "DASHBOARD_SETTING",
                    "present": True,
                    "documented_in_example": False,
                    "listed_in_env": False,
                    "sources": ["app.py"],
                }
            ],
            "env_file_available": False,
            "example_file_available": False,
        },
        "passed_checks": [],
        "warnings": [finding],
        "errors": [],
        "diagnosis": [finding],
        "evidence": [],
        "recommended_fixes": [],
    }
    monkeypatch.setattr(
        dashboard.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout=json.dumps(report)),
    )
    monkeypatch.setenv("DASHBOARD_SETTING", environment_value)
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        partial(dashboard.DashboardRequestHandler, project_directory=tmp_path),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}", report, environment_value
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def test_dashboard_and_static_assets_load(dashboard_server) -> None:
    base_url, _, _ = dashboard_server

    for path, expected in (
        (
            "/",
            "cannot inspect the computer viewing this page",
        ),
        ("/assets/dashboard.css", "--canvas"),
        ("/assets/dashboard.js", "renderDependencies"),
    ):
        with urlopen(f"{base_url}{path}") as response:
            body = response.read().decode("utf-8")
        assert response.status == 200
        assert expected in body


def test_health_endpoint_does_not_run_diagnostics(
    dashboard_server, monkeypatch
) -> None:
    base_url, _, _ = dashboard_server

    def unexpected_scan(*args, **kwargs):
        pytest.fail("health checks must not run diagnostics")

    monkeypatch.setattr(dashboard.subprocess, "run", unexpected_scan)

    with urlopen(f"{base_url}/health") as response:
        body = response.read()

    assert response.status == 200
    assert json.loads(body) == {"status": "ok"}
    assert body == b'{"status":"ok"}'


def test_api_returns_existing_report_and_finding_shape_without_values(
    dashboard_server,
) -> None:
    base_url, expected_report, environment_value = dashboard_server

    with urlopen(f"{base_url}/api/report") as response:
        report_text = response.read().decode("utf-8")
        report = json.loads(report_text)

    expected_json = json.loads(json.dumps(expected_report))
    assert set(report) == set(expected_json)
    assert report["findings"][0] == expected_json["findings"][0]
    assert set(report["findings"][0]) == {
        "id",
        "category",
        "title",
        "severity",
        "evidence",
        "confidence",
        "recommended_action",
        "validation_command",
    }
    assert report["environment_variables"]["variables"][0]["name"] == (
        "DASHBOARD_SETTING"
    )
    assert environment_value not in report_text
    assert "value" not in report["environment_variables"]["variables"][0]
    assert response.headers["X-DevEnv-Health-Score"] == "85"
    assert response.headers["X-DevEnv-Health-Status"] == "Warning"

    with urlopen(f"{base_url}/api/report/download") as download:
        assert download.headers["Content-Disposition"] == (
            'attachment; filename="devenv-doctor-report.json"'
        )
        assert json.loads(download.read()) == expected_json


def test_health_score_is_deterministic_and_handles_insufficient_data() -> None:
    findings = [
        {"severity": "error"},
        {"severity": "high"},
        {"severity": "warning"},
        {"severity": "info"},
    ]

    assert dashboard.calculate_health(findings) == (50, "Critical")
    assert dashboard.calculate_health(findings) == (50, "Critical")
    assert dashboard.calculate_health([{"severity": "warning"}]) == (90, "Warning")
    assert dashboard.calculate_health([{"severity": "info"}]) == (100, "Healthy")
    assert dashboard.calculate_health([]) == (None, "Not available")


def test_api_executes_existing_cli_and_preserves_safe_variable_report(
    tmp_path, monkeypatch
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "dashboard-check"\nversion = "0.1.0"\n'
        'requires-python = ">=3.12"\ndependencies = []\n',
        encoding="utf-8",
    )
    access = "os." + "getenv" + '("DASHBOARD_SETTING")'
    (tmp_path / "app.py").write_text(
        f"import os\nDEMO_SETTING = {access}\n", encoding="utf-8"
    )
    environment_value = "dashboard-runtime-value-not-output"
    monkeypatch.setenv("DASHBOARD_SETTING", environment_value)
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        partial(dashboard.DashboardRequestHandler, project_directory=tmp_path),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        with urlopen(f"http://127.0.0.1:{server.server_port}/api/report") as response:
            report_text = response.read().decode("utf-8")
            report = json.loads(report_text)
        variable = report["environment_variables"]["variables"][0]
        assert variable["name"] == "DASHBOARD_SETTING"
        assert variable["present"] is True
        assert environment_value not in report_text
        assert any(
            finding["category"] == "virtual-environment"
            for finding in report["findings"]
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
