from importlib import metadata
from pathlib import Path

from devenv_doctor.diagnostics import dependencies


def test_missing_declared_package(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "requirements.txt").write_text("requests>=2.31,<3\n", encoding="utf-8")

    def missing_package(name: str) -> str:
        raise metadata.PackageNotFoundError(name)

    monkeypatch.setattr(dependencies.metadata, "version", missing_package)

    findings = dependencies.diagnose_dependencies(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.id == "DEPENDENCY_MISSING"
    assert finding.title == "Dependency missing"
    assert finding.category == "dependency"
    assert finding.severity == "high"
    assert "Required package: requests" in finding.evidence
    assert "Requirement: <3,>=2.31" in finding.evidence
    assert "Installed: not found" in finding.evidence
    assert finding.recommended_action == "Install a compatible version of requests."


def test_compatible_declared_package(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "example"\ndependencies = ["requests>=2.31,<3"]\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(dependencies.metadata, "version", lambda name: "2.32.3")

    findings = dependencies.diagnose_dependencies(tmp_path)

    assert findings == []


def test_incompatible_declared_package(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "requirements.txt").write_text("requests>=2.31,<3\n", encoding="utf-8")
    monkeypatch.setattr(dependencies.metadata, "version", lambda name: "2.28.0")

    findings = dependencies.diagnose_dependencies(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.id == "DEPENDENCY_VERSION_MISMATCH"
    assert finding.title == "Dependency mismatch"
    assert "Required: <3,>=2.31" in finding.evidence
    assert "Installed: 2.28.0" in finding.evidence
    assert finding.recommended_action == "Upgrade requests to a compatible version."


def test_exact_version_requirement_is_compatible(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "requirements.txt").write_text("requests==2.32.0\n", encoding="utf-8")
    monkeypatch.setattr(dependencies.metadata, "version", lambda name: "2.32.0")

    assert dependencies.diagnose_dependencies(tmp_path) == []


def test_exact_version_requirement_mismatch(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "requirements.txt").write_text("requests==2.32.0\n", encoding="utf-8")
    monkeypatch.setattr(dependencies.metadata, "version", lambda name: "2.32.1")

    findings = dependencies.diagnose_dependencies(tmp_path)

    assert len(findings) == 1
    assert findings[0].id == "DEPENDENCY_VERSION_MISMATCH"


def test_version_range_is_accepted(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "requirements.txt").write_text("requests>=2.30,<3\n", encoding="utf-8")
    monkeypatch.setattr(dependencies.metadata, "version", lambda name: "2.32.5")

    assert dependencies.diagnose_dependencies(tmp_path) == []


def test_requirements_file_parses_common_requirement_forms(
    tmp_path: Path, monkeypatch
) -> None:
    (tmp_path / "requirements.txt").write_text(
        "requests>=2.31\nflask\npytest>=8\n", encoding="utf-8"
    )
    installed_versions = {"requests": "2.32.5", "flask": "3.0.0", "pytest": "8.3.0"}
    monkeypatch.setattr(
        dependencies.metadata, "version", lambda name: installed_versions[name]
    )

    assert dependencies.diagnose_dependencies(tmp_path) == []


def test_pyproject_dependencies_are_parsed(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "example"\ndependencies = ["requests>=2.31", "flask"]\n',
        encoding="utf-8",
    )
    installed_versions = {"requests": "2.32.5", "flask": "3.0.0"}
    monkeypatch.setattr(
        dependencies.metadata, "version", lambda name: installed_versions[name]
    )

    assert dependencies.diagnose_dependencies(tmp_path) == []


def test_invalid_requirement_lines_are_skipped_safely(
    tmp_path: Path, monkeypatch
) -> None:
    (tmp_path / "requirements.txt").write_text(
        "this is not a valid requirement !!!\nrequests>=2.31\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(dependencies.metadata, "version", lambda name: "2.32.5")

    assert dependencies.diagnose_dependencies(tmp_path) == []


def test_malformed_pyproject_is_skipped_safely(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project\nname = "example"\n', encoding="utf-8"
    )

    assert dependencies.diagnose_dependencies(tmp_path) == []
