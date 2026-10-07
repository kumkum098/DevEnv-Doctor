# Development

## Requirements

- Python 3.12 or newer.

The package uses Typer and Rich for the CLI, `packaging` for requirement comparisons, and the Python standard library for project, runtime, and installed-package inspection. Pytest and Ruff are development dependencies.

## Set Up

From the repository root:

```shell
python -m venv .venv
# PowerShell
.\.venv\Scripts\Activate.ps1
# Linux or macOS
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

The editable install exposes the `devenv` command in the active environment. The same setup is used by CI, which currently checks the minimum supported Python version (3.12).

## Run and Validate

```shell
devenv doctor
devenv doctor --json
python -m devenv_doctor.dashboard
python -m pytest -v
python -m ruff check .
python -m ruff format --check .
```

Run a focused test while iterating:

```shell
python -m pytest tests/unit/test_dependencies.py
python -m pytest tests/integration/test_doctor.py
```

## Project Layout

- `src/devenv_doctor/cli.py`: command orchestration and terminal/JSON reporting.
- `src/devenv_doctor/dashboard.py`: standard-library HTTP adapter for the existing CLI JSON report; localhost-only by default.
- `src/devenv_doctor/web/`: packaged dashboard HTML, CSS, and JavaScript assets.
- `src/devenv_doctor/analyzers/`: runtime analysis.
- `src/devenv_doctor/collectors/`: runtime and project-marker collection.
- `src/devenv_doctor/diagnostics/`: version, virtual-environment, dependency, and environment-variable checks.
- `tests/unit/`: focused collector and rule tests.
- `tests/integration/`: end-to-end CLI report tests.
- `docs/`: architecture, rule reference, and development notes.

## Add an Analyzer or Finding

1. Put diagnosis logic with the closest existing rule module under `src/devenv_doctor/diagnostics/` (or under `analyzers/` when it analyzes collected runtime data). Keep terminal formatting out of diagnosis logic.
2. Reuse `Finding` from `diagnostics/finding.py`. Give a new diagnosis a stable ID, accurate category and severity, concise evidence, and a read-only recommended action.
3. If the rule needs new input, collect that fact in the appropriate collector and pass it to the diagnosis logic. Avoid reading or retaining secret values.
4. Wire the finding into `cli.py` only when it belongs in the combined report, and update [diagnosis-rules.md](diagnosis-rules.md) with its actual behavior.

## Add Tests

- Use `tmp_path` for project files and directories, and `monkeypatch` for runtime metadata or installed-package lookups.
- Test analyzer input through its returned `Finding` or status record, including ID, category, severity, evidence, and recommendation where relevant.
- Add or extend an integration test when combined report contents or exit behavior changes. Assert user-visible terminal or JSON output rather than internal helper call order.
- Keep tests independent of packages, credentials, and environment variables on the developer's machine.

## Change Guidelines

- Keep the tool read-only. Do not add automatic installs, environment creation, or configuration edits.
- Keep analysis bounded and document unsupported inputs rather than implying general parsing or resolution.
- Add unit tests for rule outcomes and integration tests when CLI output or orchestration changes.
- Ensure environment-variable values are not retained in findings or printed.
- Update [diagnosis-rules.md](diagnosis-rules.md) whenever a rule's input, condition, severity, evidence, confidence, or recommendation changes.
- Run pytest, Ruff lint, and Ruff format checks before submitting a change.