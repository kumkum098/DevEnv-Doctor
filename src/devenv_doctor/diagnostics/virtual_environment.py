"""Diagnose whether a project virtual environment is active."""

from pathlib import Path

from devenv_doctor.diagnostics.finding import Finding


def diagnose_virtual_environment(
    virtual_env_active: bool,
    virtual_env_path: str | None,
    project_venv_exists: bool,
    project_directory: Path | None = None,
) -> Finding:
    """Report whether a virtual environment is active or available locally."""
    validation_command = 'python -c "import sys; print(sys.prefix != sys.base_prefix)"'

    if virtual_env_active:
        project_root = (
            project_directory if project_directory is not None else Path.cwd()
        )
        expected_path = (project_root / ".venv").resolve()
        active_path = Path(virtual_env_path).resolve() if virtual_env_path else None
        if active_path is not None and active_path != expected_path:
            return Finding(
                id="VENV_WRONG_PROJECT",
                category="virtual-environment",
                title="A virtual environment from another location is active",
                severity="warning",
                evidence=(
                    f"Project virtual environment: {expected_path}",
                    f"Active virtual environment: {active_path}",
                ),
                confidence="Very high",
                recommended_action=(
                    "Activate the virtual environment located in this project."
                ),
                validation_command=validation_command,
            )
        evidence = ["A virtual environment is active in the current Python process."]
        if virtual_env_path is not None:
            evidence.append(f"Active virtual environment path: {active_path}.")
        return Finding(
            id="VENV_ACTIVE",
            category="virtual-environment",
            title="Virtual environment active",
            severity="info",
            evidence=tuple(evidence),
            confidence="Very high",
            recommended_action="No action required.",
            validation_command=validation_command,
        )

    if project_venv_exists:
        return Finding(
            id="VENV_NOT_ACTIVE",
            category="virtual-environment",
            title=".venv exists but is not active",
            severity="warning",
            evidence=("A .venv directory exists in the current project.",),
            confidence="Very high",
            recommended_action=(
                "Activate the project's virtual environment before installing "
                "or running project dependencies."
            ),
            validation_command=validation_command,
        )

    return Finding(
        id="VENV_NOT_FOUND",
        category="virtual-environment",
        title="No virtual environment detected",
        severity="warning",
        evidence=(
            "The current Python process is not running inside a virtual environment.",
            "No .venv directory exists in the current project.",
        ),
        confidence="Very high",
        recommended_action=(
            "Create a project virtual environment before installing dependencies."
        ),
        validation_command=validation_command,
    )
