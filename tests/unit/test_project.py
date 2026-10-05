from pathlib import Path

from devenv_doctor.collectors.project import collect_project_info


def test_collect_project_info_detects_all_markers(tmp_path: Path) -> None:
    for filename in (
        "pyproject.toml",
        "requirements.txt",
        "requirements-dev.txt",
        ".env",
        ".env.example",
    ):
        (tmp_path / filename).touch()
    (tmp_path / ".venv").mkdir()
    (tmp_path / "tests").mkdir()

    info = collect_project_info(tmp_path)

    assert info.is_python_project is True
    assert info.has_pyproject_toml is True
    assert info.has_requirements_txt is True
    assert info.has_requirements_dev_txt is True
    assert info.has_venv is True
    assert info.has_dotenv is True
    assert info.has_dotenv_example is True
    assert info.has_tests_directory is True


def test_collect_project_info_reports_no_markers(tmp_path: Path) -> None:
    info = collect_project_info(tmp_path)

    assert info.is_python_project is False
    assert info.has_pyproject_toml is False
    assert info.has_requirements_txt is False
    assert info.has_requirements_dev_txt is False
    assert info.has_venv is False
    assert info.has_dotenv is False
    assert info.has_dotenv_example is False
    assert info.has_tests_directory is False


def test_environment_and_tests_markers_alone_do_not_identify_project(
    tmp_path: Path,
) -> None:
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".env").touch()
    (tmp_path / ".env.example").touch()
    (tmp_path / "tests").mkdir()

    info = collect_project_info(tmp_path)

    assert info.is_python_project is False
