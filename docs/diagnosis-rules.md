# Diagnosis Rules

This document describes implemented behavior only. Severity values are reported as follows: `info` is a passed check, `warning` and `high` appear under Warnings, and `error` appears under Errors. Confidence describes confidence in the observed condition, not a prediction that a recommended change will fix every application issue.

## Project Detection

### `PYTHON_PROJECT_NOT_DETECTED`

- **Category:** `project`
- **Condition:** None of `pyproject.toml`, `requirements.txt`, or `requirements-dev.txt` exists in the current directory. A `.venv`, dotenv file, or `tests/` directory alone is insufficient.
- **Severity:** `warning`
- **Evidence:** No `pyproject.toml` or requirements file was found in this directory.
- **Recommended action:** Run DevEnv Doctor from the Python project directory.

## Python Version

### `PYPROJECT_INVALID`

- **Category:** `runtime`
- **Condition:** `pyproject.toml` cannot be parsed as TOML.
- **Severity:** `warning`
- **Evidence:** A fixed message that the file could not be parsed; parser details are not included.
- **Recommended action:** Correct the TOML syntax in `pyproject.toml`.

### `PYTHON_VERSION_REQUIREMENT_INVALID`

- **Category:** `runtime`
- **Condition:** `[project].requires-python` exists but cannot be parsed as a version specifier, or the active version cannot be parsed.
- **Severity:** `warning`
- **Evidence:** The invalid `requires-python` value.
- **Recommended action:** Correct `requires-python` in `pyproject.toml`.

### `PYTHON_VERSION_MISMATCH`

- **Category:** `runtime`
- **Condition:** The active Python version does not satisfy the parsed `[project].requires-python` specifier.
- **Severity:** `high` (displayed under Warnings)
- **Evidence:** The declared requirement and current Python version.
- **Recommended action:** Use a compatible Python version, recreate the virtual environment, and reinstall project dependencies.

- **No finding:** If `pyproject.toml` or `[project].requires-python` is absent, or if the active version satisfies the requirement, the analyzer returns no finding. It does not currently warn when the requirement is missing.

## Virtual Environment

### `VENV_ACTIVE`

- **Category:** `virtual-environment`
- **Condition:** Python reports an active virtual environment, and its resolved path matches the current project's `.venv` path or no active path is available.
- **Severity:** `info`
- **Evidence:** Active state and path, when available.
- **Recommended action:** No action required.

### `VENV_WRONG_PROJECT`

- **Category:** `virtual-environment`
- **Condition:** A virtual environment is active, but its resolved path differs from the current project's `.venv` path.
- **Severity:** `warning`
- **Evidence:** The expected project `.venv` path and active environment path.
- **Recommended action:** Activate the virtual environment located in this project.

### `VENV_NOT_ACTIVE`

- **Category:** `virtual-environment`
- **Condition:** No virtual environment is active and the current project contains a `.venv` directory.
- **Severity:** `warning`
- **Evidence:** A `.venv` directory exists in the current project.
- **Recommended action:** Activate the project's virtual environment before installing or running project dependencies.

### `VENV_NOT_FOUND`

- **Category:** `virtual-environment`
- **Condition:** No virtual environment is active and no project `.venv` directory exists.
- **Severity:** `warning`
- **Evidence:** The interpreter is not in a virtual environment and `.venv` is absent.
- **Recommended action:** Create a project virtual environment before installing dependencies. The tool does not create it.

## Dependencies

### `DEPENDENCY_MISSING`

- **Category:** `dependency`
- **Condition:** A supported requirement applies to the current environment and installed distribution metadata cannot find the package.
- **Severity:** `high` (displayed under Warnings)
- **Evidence:** Package name, requirement, not-installed status, and declaration source.
- **Recommended action:** Install a compatible version of the package.

### `DEPENDENCY_VERSION_MISMATCH`

- **Category:** `dependency`
- **Condition:** The installed distribution version does not satisfy the declared version specifier.
- **Severity:** `high` (displayed under Warnings)
- **Evidence:** Package name, required specifier, installed version, and declaration source.
- **Recommended action:** Upgrade the package to a compatible version.

- **No finding:** Compatible declared dependencies produce no per-package finding. If there are no dependency findings, the CLI reports that no declared dependency issues were detected.

## Environment Variables

### `ENV_VAR_MISSING`

- **Category:** `environment`
- **Condition:** A literal name found in `os.getenv("NAME")` or `os.environ["NAME"]` is absent from the process environment. Keys listed in `.env` or `.env.example` do not count as present; `.env` is not loaded by the tool.
- **Severity:** `high` (displayed under Warnings)
- **Evidence:** Variable name, source files, process-environment presence, and whether the name is listed in `.env` or `.env.example`. Values are never included.
- **Recommended action:** Set the variable in the process environment before running the application.

- **No finding:** A referenced name present in the process environment is reported as present. The report may separately show that a key is listed in `.env` or `.env.example`; values are not read into the report.

## Boundaries

- Environment-variable scanning recognizes only the two literal access patterns above. It does not resolve aliases, dynamically computed names, or arbitrary Python syntax.
- Dependency analysis reads `requirements.txt` and PEP 621 `[project].dependencies`. It skips pip option/directive lines and invalid requirement lines; it does not follow includes or parse lockfiles or tool-specific dependency tables.
- Malformed `pyproject.toml` files are skipped for dependency analysis. Requirements are parsed as PEP 508 entries; unsupported pip-specific syntax is safely skipped rather than resolved.
- Environment-variable presence checks inspect process keys only; dotenv key names are reported separately and their values are not used to infer process presence.
- Presence checks do not validate secret values, variable formats, connectivity, or whether application code successfully uses them.
- The tool does not install or upgrade dependencies, change configuration, create environments, or apply recommended actions.