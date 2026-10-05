"""Collect information about the currently running Python runtime."""

import platform
import sys
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RuntimeInfo:
    """Basic details about the current Python runtime and environment."""

    python_version: str
    executable_path: str
    operating_system: str
    architecture: str
    virtual_env_active: bool
    virtual_env_path: str | None


def collect_runtime_info() -> RuntimeInfo:
    """Collect version, platform, executable, and virtual-environment details."""
    virtual_env_active = sys.prefix != sys.base_prefix or hasattr(sys, "real_prefix")

    return RuntimeInfo(
        python_version=platform.python_version(),
        executable_path=sys.executable,
        operating_system=platform.system(),
        architecture=platform.machine(),
        virtual_env_active=virtual_env_active,
        virtual_env_path=sys.prefix if virtual_env_active else None,
    )
