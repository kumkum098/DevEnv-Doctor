"""Inspect declared dependencies against installed distribution metadata."""

import tomllib
from importlib import metadata
from pathlib import Path

from packaging.requirements import InvalidRequirement, Requirement
from packaging.version import Version

from devenv_doctor.diagnostics.finding import Finding


def _parse_requirement(line: str) -> Requirement | None:
    line = line.split(" #", maxsplit=1)[0].strip()
    if not line or line.startswith("#") or line.startswith("-"):
        return None
    try:
        return Requirement(line)
    except InvalidRequirement:
        return None


def _read_declared_requirements(
    project_directory: Path,
) -> list[tuple[Requirement, str]]:
    declared: list[tuple[Requirement, str]] = []
    requirements_path = project_directory / "requirements.txt"
    if requirements_path.is_file():
        for line in requirements_path.read_text(encoding="utf-8").splitlines():
            requirement = _parse_requirement(line)
            if requirement is not None:
                declared.append((requirement, "requirements.txt"))

    pyproject_path = project_directory / "pyproject.toml"
    if pyproject_path.is_file():
        try:
            project = tomllib.loads(pyproject_path.read_text(encoding="utf-8")).get(
                "project", {}
            )
        except tomllib.TOMLDecodeError:
            project = {}
        dependencies = (
            project.get("dependencies", []) if isinstance(project, dict) else []
        )
        if isinstance(dependencies, list):
            for line in dependencies:
                if isinstance(line, str):
                    requirement = _parse_requirement(line)
                    if requirement is not None:
                        declared.append((requirement, "pyproject.toml"))
    return declared


def diagnose_dependencies(project_directory: Path | None = None) -> list[Finding]:
    """Report declared packages that are missing or version-incompatible."""
    root = project_directory if project_directory is not None else Path.cwd()
    findings = []

    for requirement, source in _read_declared_requirements(root):
        if requirement.marker is not None and not requirement.marker.evaluate():
            continue

        specifier = str(requirement.specifier) or "any version"
        try:
            installed_version = metadata.version(requirement.name)
        except metadata.PackageNotFoundError:
            findings.append(
                Finding(
                    id="DEPENDENCY_MISSING",
                    category="dependency",
                    title="Dependency missing",
                    severity="high",
                    evidence=(
                        f"Required package: {requirement.name}",
                        f"Requirement: {specifier}",
                        "Installed: not found",
                        f"Declared in: {source}",
                    ),
                    confidence="Very high",
                    recommended_action=(
                        f"Install a compatible version of {requirement.name}."
                    ),
                    validation_command=f"python -m pip show {requirement.name}",
                )
            )
            continue

        if Version(installed_version) not in requirement.specifier:
            findings.append(
                Finding(
                    id="DEPENDENCY_VERSION_MISMATCH",
                    category="dependency",
                    title="Dependency mismatch",
                    severity="high",
                    evidence=(
                        f"Package: {requirement.name}",
                        f"Required: {specifier}",
                        f"Installed: {installed_version}",
                        f"Declared in: {source}",
                    ),
                    confidence="Very high",
                    recommended_action=(
                        f"Upgrade {requirement.name} to a compatible version."
                    ),
                    validation_command=f"python -m pip show {requirement.name}",
                )
            )

    return findings
