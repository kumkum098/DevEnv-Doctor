"""Detect Python project markers in a directory."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ProjectInfo:
    """Presence of common Python project files and directories."""

    has_pyproject_toml: bool
    has_requirements_txt: bool
    has_requirements_dev_txt: bool
    has_venv: bool
    has_dotenv: bool
    has_dotenv_example: bool
    has_tests_directory: bool

    @property
    def is_python_project(self) -> bool:
        """Return whether Python project metadata is present."""
        return (
            self.has_pyproject_toml
            or self.has_requirements_txt
            or self.has_requirements_dev_txt
        )


def collect_project_info(directory: Path | None = None) -> ProjectInfo:
    """Check for common Python project files without reading their contents."""
    root = directory if directory is not None else Path.cwd()

    return ProjectInfo(
        has_pyproject_toml=(root / "pyproject.toml").is_file(),
        has_requirements_txt=(root / "requirements.txt").is_file(),
        has_requirements_dev_txt=(root / "requirements-dev.txt").is_file(),
        has_venv=(root / ".venv").is_dir(),
        has_dotenv=(root / ".env").is_file(),
        has_dotenv_example=(root / ".env.example").is_file(),
        has_tests_directory=(root / "tests").is_dir(),
    )
