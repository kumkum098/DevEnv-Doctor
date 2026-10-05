import json
from importlib import metadata

from typer.testing import CliRunner

from devenv_doctor import cli
from devenv_doctor.collectors.project import ProjectInfo
from devenv_doctor.collectors.runtime import RuntimeInfo
from devenv_doctor.diagnostics.environment_variables import (
    EnvironmentVariablesReport,
    EnvironmentVariableStatus,
)
from devenv_doctor.diagnostics.finding import Finding

runner = CliRunner()


def make_finding(
    finding_id: str,
    category: str,
    title: str,
    severity: str,
    evidence: tuple[str, ...],
    recommended_action: str,
) -> Finding:
    return Finding(
        id=finding_id,
        category=category,
        title=title,
        severity=severity,
        evidence=evidence,
        confidence="Very high",
        recommended_action=recommended_action,
        validation_command="python --version",
    )


def test_doctor_reports_findings_from_all_analyzers(monkeypatch, tmp_path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "fixture-project"\nrequires-python = ">=3.11"\n',
        encoding="utf-8",
    )
    (tmp_path / "requirements.txt").write_text(
        "fixture-missing-package>=1\n", encoding="utf-8"
    )
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".env.example").write_text(
        "DOCTOR_FIXTURE_SETTING=example-fixture-value\n", encoding="utf-8"
    )
    (tmp_path / "app.py").write_text(
        'import os\nos.getenv("DOCTOR_FIXTURE_SETTING")\n', encoding="utf-8"
    )
    monkeypatch.delenv("DOCTOR_FIXTURE_SETTING", raising=False)
    runtime_info = RuntimeInfo(
        python_version="3.10.0",
        executable_path=str(tmp_path / "python"),
        operating_system="FixtureOS",
        architecture="x86_64",
        virtual_env_active=False,
        virtual_env_path=None,
    )

    def missing_package(name: str) -> str:
        raise metadata.PackageNotFoundError(name)

    monkeypatch.setattr(cli, "collect_runtime_info", lambda: runtime_info)
    monkeypatch.setattr(
        "devenv_doctor.diagnostics.dependencies.metadata.version", missing_package
    )
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(cli.app, ["doctor", "--json"])

    assert result.exit_code == 0
    report = json.loads(result.output)
    assert {finding["category"] for finding in report["findings"]} == {
        "runtime",
        "virtual-environment",
        "dependency",
        "environment",
    }
    assert report["summary"] == {"errors": 0, "warnings": 4, "info": 0}
    assert {finding["id"] for finding in report["findings"]} == {
        "PYTHON_VERSION_MISMATCH",
        "VENV_NOT_ACTIVE",
        "DEPENDENCY_MISSING",
        "ENV_VAR_MISSING",
    }
    assert "example-fixture-value" not in result.output


def test_doctor_continues_with_malformed_pyproject(monkeypatch, tmp_path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text(
        "fixture-missing-package>=1\n", encoding="utf-8"
    )
    (tmp_path / "app.py").write_text(
        'import os\nos.getenv("APP_SETTING")\n', encoding="utf-8"
    )

    def missing_package(name: str) -> str:
        raise metadata.PackageNotFoundError(name)

    monkeypatch.setattr(
        "devenv_doctor.diagnostics.dependencies.metadata.version", missing_package
    )
    monkeypatch.setattr(
        cli,
        "collect_runtime_info",
        lambda: RuntimeInfo(
            python_version="3.12.6",
            executable_path=str(tmp_path / "python"),
            operating_system="FixtureOS",
            architecture="x86_64",
            virtual_env_active=False,
            virtual_env_path=None,
        ),
    )
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(cli.app, ["doctor", "--json"])

    assert result.exit_code == 0
    report = json.loads(result.output)
    finding_ids = {finding["id"] for finding in report["findings"]}
    assert finding_ids == {
        "PYPROJECT_INVALID",
        "VENV_NOT_FOUND",
        "DEPENDENCY_MISSING",
        "ENV_VAR_MISSING",
    }
    assert report["summary"] == {"errors": 0, "warnings": 4, "info": 0}


def test_doctor_handles_directory_without_project_metadata(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(cli.app, ["doctor"])

    assert result.exit_code == 0
    assert "No recognized project" in result.output
    assert "No Python project markers detected" in result.output
    assert "Errors\nNone" in result.output
    assert "Recommended fixes" in result.output


def test_doctor_reports_configuration_errors(monkeypatch, tmp_path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "example"\nrequires-python = "not-a-specifier"\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(cli.app, ["doctor"])

    assert result.exit_code == 0
    assert "Warnings" in result.output
    assert "Errors\nNone" in result.output
    assert "Invalid Python version requirement" in result.output
    assert "Evidence" in result.output
    assert "Recommended fixes" in result.output
    assert "Correct requires-python in pyproject.toml." in result.output


def test_doctor_displays_runtime_version_mismatch(monkeypatch, tmp_path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "example"\nrequires-python = "<0"\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(cli.app, ["doctor"])

    assert result.exit_code == 0
    assert "Runtime" in result.output
    assert "Python" in result.output
    assert "Diagnosis" in result.output
    assert "HIGH | Python version mismatch" in result.output
    assert "Project requires Python <0" in result.output
    assert "Use a compatible Python version" in result.output


def test_doctor_json_is_structured_and_does_not_expose_secret_values(
    monkeypatch, tmp_path
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "example"\nrequires-python = "<3.0"\ndependencies = []\n',
        encoding="utf-8",
    )
    app_source = (
        "import os\n"
        + "os.getenv"
        + '("APP_SETTING")\n'
        + "os.environ"
        + '["PROCESS_SETTING"]\n'
        + "os.getenv"
        + '("EXAMPLE_SETTING")\n'
    )
    (tmp_path / "app.py").write_text(app_source, encoding="utf-8")
    (tmp_path / ".env").write_text("APP_SETTING=file-fixture-value\n", encoding="utf-8")
    (tmp_path / ".env.example").write_text(
        "EXAMPLE_SETTING=example-fixture-value\n", encoding="utf-8"
    )
    monkeypatch.setenv("PROCESS_SETTING", "process-fixture-value")
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(cli.app, ["doctor", "--json"])

    assert result.exit_code == 0
    report = json.loads(result.output)
    assert report["environment_summary"]["runtime"]["python_version"]
    assert report["environment_summary"]["project"]["is_python_project"] is True
    assert report["warnings"][0]["id"] == "PYTHON_VERSION_MISMATCH"
    assert "findings" in report
    assert report["summary"]["errors"] == 0
    assert report["summary"]["warnings"] >= 1
    assert any(finding["category"] == "runtime" for finding in report["findings"])
    assert report["diagnosis"][0]["evidence"]
    assert report["recommended_fixes"]
    variable_statuses = {
        variable["name"]: variable
        for variable in report["environment_variables"]["variables"]
    }
    assert variable_statuses["APP_SETTING"]["present"] is False
    assert variable_statuses["APP_SETTING"]["listed_in_env"] is True
    assert variable_statuses["PROCESS_SETTING"]["present"] is True
    assert variable_statuses["EXAMPLE_SETTING"]["present"] is False
    assert variable_statuses["EXAMPLE_SETTING"]["documented_in_example"] is True
    env_finding = next(
        finding for finding in report["diagnosis"] if finding["id"] == "ENV_VAR_MISSING"
    )
    assert env_finding["category"] == "environment"
    assert env_finding["severity"] == "high"
    assert "Source: app.py" in env_finding["evidence"]
    assert "file-fixture-value" not in result.output
    assert "process-fixture-value" not in result.output
    assert "example-fixture-value" not in result.output
    assert "[bold" not in result.output
    assert "\x1b[" not in result.output


def test_doctor_json_aggregates_all_findings_and_exits_only_for_errors(
    monkeypatch, tmp_path
) -> None:
    runtime_info = RuntimeInfo(
        python_version="3.12.6",
        executable_path=str(tmp_path / "python"),
        operating_system="FixtureOS",
        architecture="x86_64",
        virtual_env_active=False,
        virtual_env_path=None,
    )
    project_info = ProjectInfo(
        has_pyproject_toml=True,
        has_requirements_txt=True,
        has_requirements_dev_txt=False,
        has_venv=True,
        has_dotenv=False,
        has_dotenv_example=True,
        has_tests_directory=True,
    )
    runtime_finding = make_finding(
        "PYTHON_VERSION_COMPATIBLE",
        "runtime",
        "Python version is compatible",
        "info",
        ("Python version satisfies the project requirement.",),
        "No action required.",
    )
    virtual_environment_finding = make_finding(
        "VENV_NOT_ACTIVE",
        "virtual-environment",
        "Virtual environment is not active",
        "warning",
        ("The project environment is not active.",),
        "Activate the project virtual environment.",
    )
    dependency_finding = make_finding(
        "DEPENDENCY_MISSING",
        "dependency",
        "Dependency missing",
        "error",
        ("Required package: example-package", "Installed: not found"),
        "Install a compatible version.",
    )
    environment_report = EnvironmentVariablesReport(
        variables=(
            EnvironmentVariableStatus(
                "APP_SETTING", False, True, False, ("app/config.py",)
            ),
        ),
        env_file_available=False,
        example_file_available=True,
    )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "collect_runtime_info", lambda: runtime_info)
    monkeypatch.setattr(cli, "collect_project_info", lambda: project_info)
    monkeypatch.setattr(cli, "analyze_runtime", lambda **kwargs: runtime_finding)
    monkeypatch.setattr(
        cli,
        "diagnose_virtual_environment",
        lambda **kwargs: virtual_environment_finding,
    )
    monkeypatch.setattr(cli, "diagnose_dependencies", lambda: [dependency_finding])
    monkeypatch.setattr(
        cli, "diagnose_environment_variables", lambda: environment_report
    )

    result = runner.invoke(cli.app, ["doctor", "--json"])

    assert result.exit_code == 1
    report = json.loads(result.output)
    findings = report["findings"]
    assert {finding["category"] for finding in findings} == {
        "runtime",
        "virtual-environment",
        "dependency",
        "environment",
    }
    assert report["summary"] == {"errors": 1, "warnings": 2, "info": 1}
    assert len(findings) == 4
    assert len(
        {(finding["id"], tuple(finding["evidence"])) for finding in findings}
    ) == len(findings)
    assert "APP_SETTING" in result.output
    assert "secret-value" not in result.output
