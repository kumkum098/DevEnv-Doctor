"""Compatibility entry point for Python runtime version analysis."""

from dataclasses import replace
from pathlib import Path

from devenv_doctor.analyzers.runtime import analyze_runtime
from devenv_doctor.collectors.runtime import collect_runtime_info
from devenv_doctor.diagnostics.finding import Finding


def diagnose_python_version(
    project_directory: Path | None = None,
    current_version: str | None = None,
) -> Finding | None:
    """Delegate to the runtime analyzer, optionally overriding the version."""
    runtime_info = collect_runtime_info()
    if current_version is not None:
        runtime_info = replace(runtime_info, python_version=current_version)
    return analyze_runtime(project_directory, runtime_info)
