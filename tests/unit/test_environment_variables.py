from pathlib import Path

from devenv_doctor.diagnostics.environment_variables import (
    diagnose_environment_variables,
)


def _write_source(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_used_variable_is_present_in_process_environment(tmp_path: Path) -> None:
    _write_source(tmp_path / "app.py", "import os\nos.getenv" + '("APP_SETTING")\n')

    report = diagnose_environment_variables(
        tmp_path, environment={"APP_SETTING": "fixture-process-value"}
    )

    assert report.variables[0].name == "APP_SETTING"
    assert report.variables[0].present is True
    assert report.variables[0].sources == ("app.py",)
    assert "fixture-process-value" not in repr(report)


def test_used_variable_missing_from_process_environment(tmp_path: Path) -> None:
    _write_source(
        tmp_path / "app.py", "import os\nos.environ" + '["REQUIRED_SETTING"]\n'
    )

    report = diagnose_environment_variables(tmp_path, environment={})

    assert len(report.variables) == 1
    assert report.variables[0].name == "REQUIRED_SETTING"
    assert report.variables[0].present is False


def test_env_example_documents_variable_without_marking_it_present(
    tmp_path: Path,
) -> None:
    _write_source(tmp_path / "app.py", "import os\nos.getenv" + "('APP_SETTING')\n")
    (tmp_path / ".env.example").write_text(
        "APP_SETTING=fixture-example-value\n", encoding="utf-8"
    )

    report = diagnose_environment_variables(tmp_path, environment={})

    assert report.example_file_available is True
    assert report.variables[0].present is False
    assert report.variables[0].documented_in_example is True
    assert "fixture-example-value" not in repr(report)


def test_env_key_does_not_mean_variable_is_process_present(tmp_path: Path) -> None:
    _write_source(tmp_path / "app.py", "import os\nos.getenv" + '("APP_SETTING")\n')
    (tmp_path / ".env").write_text("APP_SETTING=fixture-env-value\n", encoding="utf-8")

    report = diagnose_environment_variables(tmp_path, environment={})

    assert report.variables[0].present is False
    assert report.variables[0].listed_in_env is True
    assert "fixture-env-value" not in repr(report)


def test_multiline_getenv_and_environ_patterns_are_detected(tmp_path: Path) -> None:
    _write_source(
        tmp_path / "app.py",
        "import os\nos.getenv(\n    'APP_SETTING'\n)\n"
        'os.environ [\n    "PROCESS_SETTING"\n]\n',
    )

    report = diagnose_environment_variables(tmp_path, environment={})

    assert [variable.name for variable in report.variables] == [
        "APP_SETTING",
        "PROCESS_SETTING",
    ]


def test_unused_example_variable_is_not_reported(tmp_path: Path) -> None:
    (tmp_path / ".env.example").write_text(
        "UNUSED_KEY=example-value\n", encoding="utf-8"
    )

    report = diagnose_environment_variables(tmp_path, environment={})

    assert report.variables == ()


def test_dotenv_and_process_values_never_enter_report(tmp_path: Path) -> None:
    _write_source(tmp_path / "app.py", "import os\nos.getenv" + '("APP_SETTING")\n')
    (tmp_path / ".env").write_text("APP_SETTING=env-fixture-value\n", encoding="utf-8")
    (tmp_path / ".env.example").write_text(
        "APP_SETTING=example-fixture-value\n", encoding="utf-8"
    )

    report = diagnose_environment_variables(
        tmp_path, environment={"APP_SETTING": "process-fixture-value"}
    )

    rendered_report = repr(report)
    assert "env-fixture-value" not in rendered_report
    assert "example-fixture-value" not in rendered_report
    assert "process-fixture-value" not in rendered_report


def test_ignored_directories_are_pruned_from_source_scan(tmp_path: Path) -> None:
    ignored_directories = (
        ".venv",
        ".venv-1",
        "__pycache__",
        ".git",
        "node_modules",
        "build",
        "dist",
    )
    for index, directory in enumerate(ignored_directories):
        _write_source(
            tmp_path / directory / "ignored.py",
            f'import os\nos.getenv("IGNORED_{index}")\n',
        )

    report = diagnose_environment_variables(tmp_path, environment={})

    assert report.variables == ()


def test_multiple_source_files_are_reported_for_a_variable(tmp_path: Path) -> None:
    _write_source(
        tmp_path / "app" / "config.py", "import os\nos.getenv" + '("APP_SETTING")\n'
    )
    _write_source(tmp_path / "worker.py", "import os\nos.environ" + '["APP_SETTING"]\n')

    report = diagnose_environment_variables(tmp_path, environment={})

    assert len(report.variables) == 1
    assert report.variables[0].sources == ("app/config.py", "worker.py")


def test_no_environment_files_means_referenced_variable_is_missing(
    tmp_path: Path,
) -> None:
    _write_source(tmp_path / "app.py", "import os\nos.getenv" + '("APP_SETTING")\n')

    report = diagnose_environment_variables(tmp_path, environment={})

    assert report.env_file_available is False
    assert report.example_file_available is False
    assert report.variables[0].name == "APP_SETTING"
    assert report.variables[0].present is False
