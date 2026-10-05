"""Inspect simple environment-variable references and dotenv keys."""

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

_REFERENCE_PATTERNS = (
    re.compile(
        r"""\bos\s*\.\s*getenv\s*\(\s*(?P<quote>['"])(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?P=quote)"""
    ),
    re.compile(
        r"""\bos\s*\.\s*environ\s*\[\s*(?P<quote>['"])(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?P=quote)\s*\]"""
    ),
)
_DOTENV_KEY_PATTERN = re.compile(
    r"^\s*(?:export\s+)?(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*="
)
_EXCLUDED_SOURCE_DIRECTORIES = {
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    "__pycache__",
    "build",
    "dist",
    "env",
    "node_modules",
    "venv",
}


@dataclass(frozen=True, slots=True)
class EnvironmentVariableStatus:
    """Safe availability metadata for a referenced environment variable."""

    name: str
    present: bool
    documented_in_example: bool
    listed_in_env: bool = False
    sources: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EnvironmentVariablesReport:
    """Detected variables and availability of dotenv files."""

    variables: tuple[EnvironmentVariableStatus, ...]
    env_file_available: bool
    example_file_available: bool


def _find_referenced_variables(project_directory: Path) -> dict[str, set[str]]:
    references: dict[str, set[str]] = {}
    pending_directories = [project_directory]
    while pending_directories:
        directory = pending_directories.pop()
        try:
            children = directory.iterdir()
            for child in children:
                if child.is_symlink():
                    continue
                if child.is_dir():
                    if (
                        child.name not in _EXCLUDED_SOURCE_DIRECTORIES
                        and not child.name.startswith(".venv")
                    ):
                        pending_directories.append(child)
                    continue
                if child.suffix != ".py":
                    continue
                try:
                    source = child.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                source_name = child.relative_to(project_directory).as_posix()
                for pattern in _REFERENCE_PATTERNS:
                    for match in pattern.finditer(source):
                        references.setdefault(match.group("name"), set()).add(
                            source_name
                        )
        except OSError:
            continue
    return references


def _read_dotenv_keys(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    keys = set()
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return keys
    for line in lines:
        match = _DOTENV_KEY_PATTERN.match(line)
        if match is not None:
            keys.add(match.group("name"))
    return keys


def diagnose_environment_variables(
    project_directory: Path | None = None,
    environment: Mapping[str, str] | None = None,
) -> EnvironmentVariablesReport:
    """Report whether referenced names exist without retaining their values."""
    root = project_directory if project_directory is not None else Path.cwd()
    env_path = root / ".env"
    example_path = root / ".env.example"
    env_keys = _read_dotenv_keys(env_path)
    example_keys = _read_dotenv_keys(example_path)
    process_environment = os.environ if environment is None else environment
    references = _find_referenced_variables(root)

    variables = tuple(
        EnvironmentVariableStatus(
            name=name,
            present=name in process_environment,
            documented_in_example=name in example_keys,
            listed_in_env=name in env_keys,
            sources=tuple(sorted(references[name])),
        )
        for name in sorted(references)
    )
    return EnvironmentVariablesReport(
        variables=variables,
        env_file_available=env_path.is_file(),
        example_file_available=example_path.is_file(),
    )
