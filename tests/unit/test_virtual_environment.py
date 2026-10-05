from pathlib import Path

from devenv_doctor.diagnostics.virtual_environment import diagnose_virtual_environment


def test_active_project_virtual_environment(tmp_path: Path) -> None:
    project_venv = tmp_path / ".venv"
    project_venv.mkdir()

    finding = diagnose_virtual_environment(
        virtual_env_active=True,
        virtual_env_path=str(project_venv),
        project_venv_exists=True,
        project_directory=tmp_path,
    )

    assert finding.id == "VENV_ACTIVE"
    assert finding.title == "Virtual environment active"
    assert finding.severity == "info"
    assert f"Active virtual environment path: {project_venv}." in finding.evidence


def test_no_active_environment_and_no_project_venv(tmp_path: Path) -> None:
    finding = diagnose_virtual_environment(
        virtual_env_active=False,
        virtual_env_path=None,
        project_venv_exists=False,
        project_directory=tmp_path,
    )

    assert finding.id == "VENV_NOT_FOUND"
    assert finding.title == "No virtual environment detected"
    assert finding.severity == "warning"


def test_project_venv_exists_but_is_inactive(tmp_path: Path) -> None:
    (tmp_path / ".venv").mkdir()

    finding = diagnose_virtual_environment(
        virtual_env_active=False,
        virtual_env_path=None,
        project_venv_exists=True,
        project_directory=tmp_path,
    )

    assert finding.id == "VENV_NOT_ACTIVE"
    assert finding.title == ".venv exists but is not active"
    assert finding.severity == "warning"
    assert "Activate the project's virtual environment" in finding.recommended_action


def test_environment_from_different_project_is_active(tmp_path: Path) -> None:
    (tmp_path / ".venv").mkdir()
    other_venv = tmp_path.parent / "other-project" / ".venv"

    finding = diagnose_virtual_environment(
        virtual_env_active=True,
        virtual_env_path=str(other_venv),
        project_venv_exists=True,
        project_directory=tmp_path,
    )

    assert finding.id == "VENV_WRONG_PROJECT"
    assert finding.title == "A virtual environment from another location is active"
    assert finding.severity == "warning"
    assert str(other_venv.resolve()) in finding.evidence[1]


def test_active_project_environment_path_is_normalized(tmp_path: Path) -> None:
    project_venv = tmp_path / ".venv"
    project_venv.mkdir()
    path_with_dot = tmp_path / "folder" / ".." / ".venv"

    finding = diagnose_virtual_environment(
        virtual_env_active=True,
        virtual_env_path=str(path_with_dot),
        project_venv_exists=True,
        project_directory=tmp_path,
    )

    assert finding.id == "VENV_ACTIVE"
    assert str(project_venv.resolve()) in finding.evidence[1]
