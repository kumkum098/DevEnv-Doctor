# Architecture

DevEnv Doctor uses a small pipeline. A project is the input; findings are the shared diagnostic output; the CLI or local dashboard presents the report.

```text
Project
	↓
Collectors
	↓
Analyzers
	↓
Findings
	├── CLI → Terminal / JSON
	└── Local HTTP adapter → Dashboard
```

The CLI coordinates collection and diagnosis and owns the existing JSON report. The dashboard is a local visualization layer over that report; it does not duplicate diagnosis logic or define a second report schema.

## Components

### CLI

`src/devenv_doctor/cli.py` implements `devenv doctor`. It calls the collectors and analyzers in sequence, classifies results as passed checks, warnings, or errors, then renders the report as Rich terminal text or JSON when `--json` is supplied.

### Collectors

Collectors gather facts; they do not decide whether those facts are a problem. Keeping collection separate makes runtime and project inputs easier to test with temporary projects and controlled runtime values.

- `collectors/runtime.py` reads the active interpreter and platform through Python's standard library. It reports Python version, executable path, operating system, architecture, and virtual-environment state.
- `collectors/project.py` checks for a fixed set of project markers: `pyproject.toml`, requirements files, `.venv`, dotenv files, and `tests/`. It does not read those files' contents.

### Analyzers

Analyzers apply diagnosis rules to collected or locally read evidence. They should not render terminal output.

- `analyzers/runtime.py` reads `[project].requires-python` from `pyproject.toml` and compares it to the running interpreter with `packaging`. `diagnostics/python_version.py` remains a compatibility wrapper around this analyzer.
- `diagnostics/virtual_environment.py` compares active interpreter state with whether the project has a `.venv` directory.
- `diagnostics/dependencies.py` reads requirements from `requirements.txt` and PEP 621 `[project].dependencies`, then checks installed distribution metadata with `importlib.metadata` and `packaging`.
- `diagnostics/environment_variables.py` searches Python source with a small set of regular expressions. It compares referenced names with the process environment and dotenv key names. Values are not included in its report.

The environment-variable analyzer returns status records rather than `Finding` objects. The CLI turns missing-variable statuses into findings for the report. The CLI also creates the project-not-detected finding from the project collector's result.

### Findings

`diagnostics/finding.py` defines the shared immutable `Finding` data model. Findings contain an ID, category, title, severity, evidence, confidence, recommended action, and validation command. Compatible checks are summarized as passed checks; dependency checks that pass do not produce a finding.

The shared model lets each diagnosis provide the same kind of explanation without knowing whether it will be displayed in a terminal or serialized as JSON.

### Reporters

The existing report is produced by `cli.py`:

- Default output uses Rich to show an environment summary, passed checks, warnings, errors, diagnosis, evidence, and recommended fixes.
- `devenv doctor --json` serializes the same collected data and findings with the standard-library `json` module. Environment-variable records contain names and status flags, not values.

`dashboard.py` runs the existing CLI JSON command as a subprocess and serves that JSON at `/api/report`. It binds to localhost by default; a deployment can provide its public bind address and port as command-line options. Static assets are in `web/`. The health score is derived only from Finding severities and is returned separately in response headers. Environment-variable values are not included in the report or dashboard. In deployment, the subprocess scans the project checkout and Python environment on the server, not the browser visitor's computer.

## Execution Flow

1. The CLI asks the runtime and project collectors for local facts.
2. Runtime and project facts, plus supported project files, are passed to diagnosis logic.
3. The CLI combines findings and environment-variable statuses into one report.
4. The CLI renders terminal text or JSON. When started separately, the dashboard retrieves that existing JSON report and visualizes it.

The checks are read-only. The tool does not run validation commands, resolve dependencies, contact package indexes, install packages, or modify project files or environments.

## Tests

Unit tests cover collectors and individual diagnosis rules under `tests/unit/`. CLI integration tests under `tests/integration/` cover combined findings, malformed project configuration, result grouping, missing project metadata, error reporting, and JSON serialization.