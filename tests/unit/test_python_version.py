from pathlib import Path

from devenv_doctor.analyzers.runtime import analyze_runtime
from devenv_doctor.collectors.runtime import RuntimeInfo


def write_pyproject(directory: Path, requires_python: str | None) -> None:
    requirement = f'requires-python = "{requires_python}"\n' if requires_python else ""
    (directory / "pyproject.toml").write_text(
        f'[project]\nname = "example"\n{requirement}', encoding="utf-8"
    )


def runtime_info(version: str) -> RuntimeInfo:
    return RuntimeInfo(
        python_version=version,
        executable_path="python",
        operating_system="TestOS",
        architecture="test-architecture",
        virtual_env_active=False,
        virtual_env_path=None,
    )


def test_compatible_python_version_returns_no_finding(tmp_path: Path) -> None:
    write_pyproject(tmp_path, ">=3.11,<3.14")

    finding = analyze_runtime(tmp_path, runtime_info("3.13.0"))

    assert finding is None


def test_too_old_python_version_returns_mismatch(tmp_path: Path) -> None:
    write_pyproject(tmp_path, ">=3.11,<3.14")

    finding = analyze_runtime(tmp_path, runtime_info("3.10.9"))

    assert finding is not None
    assert finding.id == "PYTHON_VERSION_MISMATCH"
    assert finding.category == "runtime"
    assert finding.title == "Python version mismatch"
    assert finding.severity == "high"
    assert finding.evidence == (
        "Project requires Python >=3.11,<3.14",
        "Current Python is 3.10.9",
    )
    assert finding.confidence == "Very high"
    assert "compatible Python version" in finding.recommended_action
    assert "recreate the virtual environment" in finding.recommended_action
    assert finding.validation_command == "python --version; pytest"


def test_too_new_python_version_returns_mismatch(tmp_path: Path) -> None:
    write_pyproject(tmp_path, ">=3.11,<3.14")

    finding = analyze_runtime(tmp_path, runtime_info("3.14.0"))

    assert finding is not None
    assert finding.id == "PYTHON_VERSION_MISMATCH"
    assert finding.evidence[-1] == "Current Python is 3.14.0"


def test_missing_requires_python_returns_no_finding(tmp_path: Path) -> None:
    write_pyproject(tmp_path, None)

    finding = analyze_runtime(tmp_path, runtime_info("3.12.6"))

    assert finding is None


def test_invalid_requires_python_returns_configuration_warning(
    tmp_path: Path,
) -> None:
    write_pyproject(tmp_path, "not-a-version-specifier")

    finding = analyze_runtime(tmp_path, runtime_info("3.12.6"))

    assert finding is not None
    assert finding.id == "PYTHON_VERSION_REQUIREMENT_INVALID"
    assert finding.category == "runtime"
    assert finding.severity == "warning"
    assert "Invalid requires-python specifier" in finding.evidence[0]


def test_malformed_pyproject_returns_configuration_warning(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project\n", encoding="utf-8")

    finding = analyze_runtime(tmp_path, runtime_info("3.12.6"))

    assert finding is not None
    assert finding.id == "PYPROJECT_INVALID"
    assert finding.category == "runtime"
    assert finding.severity == "warning"
    assert finding.evidence == ("pyproject.toml could not be parsed as valid TOML.",)
