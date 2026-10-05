# DevEnv Doctor

DevEnv Doctor is a local-first Python CLI that diagnoses common "works on my machine" environment problems. It compares a Python project with the interpreter and installed packages running the command, then reports evidence and suggested actions without modifying the project or environment.

## Problem It Solves

Python projects can fail on another machine because it uses the wrong Python version, the wrong virtual environment, a missing or incompatible dependency, or lacks a required environment variable. DevEnv Doctor inspects supported project metadata and source patterns, then compares them with the current Python process and installed package metadata.

## Features

- Runtime inspection, including Python version, executable, platform, and virtual-environment state.
- Python version diagnosis using `[project].requires-python`.
- Virtual environment diagnosis for active, inactive, missing, or other-location environments.
- Dependency diagnosis for supported declarations in `requirements.txt` and PEP 621 `[project].dependencies`.
- Environment variable diagnosis for literal `os.getenv("NAME")` and `os.environ["NAME"]` references.
- Combined diagnostics through `devenv doctor`.
- Structured JSON output with `devenv doctor --json`.

Environment-variable presence means the name exists in the process environment. The report separately notes keys listed in `.env` and `.env.example`; it does not load `.env` values. Reports include names and status flags only, never environment-file or process-environment values.

## Installation

Python 3.12 or newer is required. From a checkout of this repository, create and activate a virtual environment, then install the CLI and development tools:

```shell
python -m venv .venv
# PowerShell
.\.venv\Scripts\Activate.ps1
# Linux or macOS
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Usage

```powershell
devenv --help
devenv doctor
devenv doctor --json
```

`doctor` is the only command currently exposed. It inspects the current working directory and active interpreter. It does not install packages, create or modify virtual environments, or apply recommended actions.

## Web Dashboard

The dashboard is a local visualization layer over the existing `devenv doctor --json` report. It does not run a second diagnostic engine or expose environment-variable values. From the project directory with DevEnv Doctor installed, start it with:

```shell
python -m devenv_doctor.dashboard
```

Then open <http://127.0.0.1:8765>. The server binds to localhost only. Use `Ctrl+C` in the terminal to stop it; run the command from the project directory you want to inspect.

## Uptime Monitoring

An external uptime monitor can periodically request `GET /health`. The endpoint only checks that the web process is responding; it does not run the diagnostic scan or return project, filesystem, or environment details.

For an externally reachable deployment, configure the host or reverse proxy to route HTTPS requests to `/health`. The server can bind to the deployment interface with:

```shell
python -m devenv_doctor.dashboard --host 0.0.0.0 --port <platform-port>
```

Example monitor URL: `https://your-deployed-domain.com/health`

Expected response:

```json
{"status":"ok"}
```

The dashboard has no authentication. If it is externally reachable, configure the deployment proxy to expose only the routes you intend to make public.

## Example Output

Illustrative output from a project with a Python-version mismatch:

```text
DevEnv Doctor

Runtime
Python         3.10.9
Executable     /work/example/.venv/bin/python
OS             Linux
Architecture   x86_64
Virtual Env    /work/example/.venv

Environment Summary
Project         Python project (pyproject.toml, requirements.txt, .venv)
Virtual Env     Active (/work/example/.venv)
Environment     .env.example

Environment Variables
✓ APP_SETTING

Dependencies
✓ No declared dependency issues detected

Passed checks
✓ Python runtime detected
✓ Python project metadata detected
✓ Virtual environment active
✓ No declared dependency issues detected
✓ APP_SETTING present

Warnings
⚠ Python version mismatch

Errors
None

Diagnosis
HIGH | Python version mismatch

Evidence
Python version mismatch: Project requires Python >=3.11,<3.13; Current Python is 3.10.9

Recommended fixes
Use a compatible Python version, recreate the virtual environment, and reinstall project dependencies.

Summary
Errors: 0
Warnings: 1
Info: 0
```

The exact paths, checks, and findings depend on the current project and interpreter.

## Architecture

The CLI orchestrates **CLI → Collectors → Analyzers → Findings → Reporters**. See [docs/architecture.md](docs/architecture.md) for module responsibilities and data flow.

## Design Principles

- Local-first and deterministic; no cloud service or AI is required.
- Findings are based on locally observed project and interpreter evidence.
- Environment-variable values are never reported.
- The tool is read-only and does not automatically modify the system or project.

## Testing

```shell
pytest
ruff check .
ruff format --check .
```

Unit tests cover individual collectors and diagnosis rules. Integration tests exercise the CLI report and JSON output.

## Limitations

- The tool checks only the current directory and current Python environment. It does not compare machines or inspect other interpreters.
- Project detection uses a fixed set of marker files; it is not a general project or build-system detector.
- Dependency checks read `requirements.txt` and PEP 621 `[project].dependencies`. They do not resolve packages, follow included requirements files, inspect lockfiles, or understand every tool-specific `pyproject.toml` dependency format. Unsupported requirement lines are skipped.
- Environment-variable scanning uses regular expressions for the two literal access forms listed above. It is not a Python parser and may miss aliases, dynamic names, or other access patterns.
- A key listed in `.env.example` is documented, not considered configured. The tool does not validate a variable's value, format, or usability.
- No packages are installed, no files or environments are modified, and recommendations are not applied automatically.
- Git, Docker, Node.js, network services, and security analysis are not supported.

See [docs/diagnosis-rules.md](docs/diagnosis-rules.md) for the current rules, IDs, severities, and boundaries.

## Development

See [docs/development.md](docs/development.md) for setup, test, lint, and contribution instructions.

## Contributing

Keep changes focused on the supported Python-project checks. Include unit tests for rule behavior and integration tests for CLI changes, update relevant documentation, and run the checks in the development guide. Do not add automatic environment changes or claim support for formats that are not covered by tests.

