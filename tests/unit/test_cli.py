from typer.testing import CliRunner

from devenv_doctor.cli import app
from devenv_doctor.collectors.runtime import RuntimeInfo
from devenv_doctor.diagnostics.finding import Finding

runner = CliRunner()


def test_doctor_displays_collected_runtime_information(monkeypatch, tmp_path) -> None:
    (tmp_path / ".venv").mkdir()
    monkeypatch.chdir(tmp_path)
    executable_path = "fixture-python.exe"
    virtual_env_path = ".venv"
    info = RuntimeInfo(
        python_version="3.12.6",
        executable_path=executable_path,
        operating_system="Windows",
        architecture="x86_64",
        virtual_env_active=True,
        virtual_env_path=virtual_env_path,
    )
    finding = Finding(
        id="PYTHON_VERSION_COMPATIBLE",
        category="runtime",
        title="Python version is compatible",
        severity="info",
        evidence=("Project requires >=3.11,<3.13.", "Current Python is 3.12.6."),
        confidence="Very high",
        recommended_action="No action required.",
        validation_command="python --version",
    )
    monkeypatch.setattr("devenv_doctor.cli.collect_runtime_info", lambda: info)
    monkeypatch.setattr(
        "devenv_doctor.cli.analyze_runtime", lambda runtime_info=None: finding
    )

    result = runner.invoke(app, ["doctor"], terminal_width=120)

    assert result.exit_code == 0
    assert "DevEnv Doctor" in result.output
    assert "Environment Summary" in result.output
    assert "Runtime" in result.output
    assert "3.12.6" in result.output
    assert executable_path in result.output
    assert "Windows" in result.output
    assert "x86_64" in result.output
    assert virtual_env_path in result.output
    assert "✓ Python version is compatible" in result.output
    assert "Passed checks" in result.output
    assert "Warnings" in result.output
    assert "Errors" in result.output
    assert "Diagnosis" in result.output
    assert "Evidence" in result.output
    assert "Recommended fixes" in result.output


def test_doctor_displays_inactive_virtual_environment(monkeypatch, tmp_path) -> None:
    (tmp_path / ".venv").mkdir()
    monkeypatch.chdir(tmp_path)
    info = RuntimeInfo(
        python_version="3.12.6",
        executable_path=str(tmp_path / "python"),
        operating_system="FixtureOS",
        architecture="x86_64",
        virtual_env_active=False,
        virtual_env_path=None,
    )
    monkeypatch.setattr("devenv_doctor.cli.collect_runtime_info", lambda: info)

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "Virtual Env" in result.output
    assert "Not active" in result.output
    assert ".venv exists but is not active" in result.output
