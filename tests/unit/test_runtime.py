from devenv_doctor.collectors import runtime


def test_collect_runtime_info_python_version(monkeypatch) -> None:
    monkeypatch.setattr(runtime.platform, "python_version", lambda: "3.14.0")

    info = runtime.collect_runtime_info()

    assert info.python_version == "3.14.0"


def test_collect_runtime_info_executable_path(monkeypatch) -> None:
    monkeypatch.setattr(runtime.sys, "executable", "fixture-python")

    info = runtime.collect_runtime_info()

    assert info.executable_path == "fixture-python"


def test_collect_runtime_info_operating_system(monkeypatch) -> None:
    monkeypatch.setattr(runtime.platform, "system", lambda: "TestOS")

    info = runtime.collect_runtime_info()

    assert info.operating_system == "TestOS"


def test_collect_runtime_info_architecture(monkeypatch) -> None:
    monkeypatch.setattr(runtime.platform, "machine", lambda: "test-architecture")

    info = runtime.collect_runtime_info()

    assert info.architecture == "test-architecture"


def test_detects_virtual_environment_from_prefixes(monkeypatch, tmp_path) -> None:
    environment_path = str(tmp_path / ".venv")
    base_path = str(tmp_path / "python")
    monkeypatch.setattr(runtime.sys, "prefix", environment_path)
    monkeypatch.setattr(runtime.sys, "base_prefix", base_path)
    monkeypatch.delattr(runtime.sys, "real_prefix", raising=False)

    info = runtime.collect_runtime_info()

    assert info.virtual_env_active is True


def test_detects_legacy_virtual_environment_prefix(monkeypatch, tmp_path) -> None:
    base_path = str(tmp_path / "python")
    monkeypatch.setattr(runtime.sys, "prefix", base_path)
    monkeypatch.setattr(runtime.sys, "base_prefix", base_path)
    monkeypatch.setattr(runtime.sys, "real_prefix", base_path, raising=False)

    info = runtime.collect_runtime_info()

    assert info.virtual_env_active is True


def test_virtual_environment_path_is_returned_when_active(
    monkeypatch, tmp_path
) -> None:
    environment_path = str(tmp_path / ".venv")
    monkeypatch.setattr(runtime.sys, "prefix", environment_path)
    monkeypatch.setattr(runtime.sys, "base_prefix", str(tmp_path / "python"))
    monkeypatch.delattr(runtime.sys, "real_prefix", raising=False)

    info = runtime.collect_runtime_info()

    assert info.virtual_env_path == environment_path


def test_virtual_environment_path_is_none_when_inactive(monkeypatch, tmp_path) -> None:
    base_path = str(tmp_path / "python")
    monkeypatch.setattr(runtime.sys, "prefix", base_path)
    monkeypatch.setattr(runtime.sys, "base_prefix", base_path)
    monkeypatch.delattr(runtime.sys, "real_prefix", raising=False)

    info = runtime.collect_runtime_info()

    assert info.virtual_env_active is False
    assert info.virtual_env_path is None
