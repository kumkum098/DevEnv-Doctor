"""Analyze whether the current Python runtime satisfies project metadata."""

import tomllib
from pathlib import Path

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version

from devenv_doctor.collectors.runtime import RuntimeInfo, collect_runtime_info
from devenv_doctor.diagnostics.finding import Finding


def analyze_runtime(
    project_directory: Path | None = None,
    runtime_info: RuntimeInfo | None = None,
) -> Finding | None:
    """Return a finding for an invalid or unsatisfied Python requirement."""
    root = project_directory if project_directory is not None else Path.cwd()
    runtime = runtime_info if runtime_info is not None else collect_runtime_info()
    pyproject_path = root / "pyproject.toml"
    if not pyproject_path.is_file():
        return None

    try:
        document = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return Finding(
            id="PYPROJECT_INVALID",
            category="runtime",
            title="Invalid pyproject.toml",
            severity="warning",
            evidence=("pyproject.toml could not be parsed as valid TOML.",),
            confidence="Very high",
            recommended_action="Correct the TOML syntax in pyproject.toml.",
            validation_command=(
                'python -c "import tomllib; '
                "tomllib.loads(open('pyproject.toml', encoding='utf-8').read())\""
            ),
        )
    project = document.get("project", {})
    requirement = project.get("requires-python") if isinstance(project, dict) else None
    if requirement is None:
        return None

    try:
        specifier = SpecifierSet(requirement)
        current_version = Version(runtime.python_version)
    except (InvalidSpecifier, InvalidVersion, TypeError):
        return Finding(
            id="PYTHON_VERSION_REQUIREMENT_INVALID",
            category="runtime",
            title="Invalid Python version requirement",
            severity="warning",
            evidence=(f"Invalid requires-python specifier: {requirement!r}.",),
            confidence="Very high",
            recommended_action="Correct requires-python in pyproject.toml.",
            validation_command="python --version",
        )

    if current_version in specifier:
        return None

    return Finding(
        id="PYTHON_VERSION_MISMATCH",
        category="runtime",
        title="Python version mismatch",
        severity="high",
        evidence=(
            f"Project requires Python {requirement}",
            f"Current Python is {runtime.python_version}",
        ),
        confidence="Very high",
        recommended_action=(
            "Use a compatible Python version, recreate the virtual environment, "
            "and reinstall project dependencies."
        ),
        validation_command="python --version; pytest",
    )
