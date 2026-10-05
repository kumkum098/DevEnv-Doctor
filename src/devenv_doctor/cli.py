"""Command-line interface for DevEnv Doctor."""

import json
from dataclasses import asdict
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from devenv_doctor.analyzers.runtime import analyze_runtime
from devenv_doctor.collectors.project import ProjectInfo, collect_project_info
from devenv_doctor.collectors.runtime import collect_runtime_info
from devenv_doctor.diagnostics.dependencies import diagnose_dependencies
from devenv_doctor.diagnostics.environment_variables import (
    EnvironmentVariablesReport,
    diagnose_environment_variables,
)
from devenv_doctor.diagnostics.finding import Finding
from devenv_doctor.diagnostics.virtual_environment import diagnose_virtual_environment

app = typer.Typer(no_args_is_help=True)
console = Console()


def _project_markers(project_info: ProjectInfo) -> list[str]:
    marker_attributes = (
        ("has_pyproject_toml", "pyproject.toml"),
        ("has_requirements_txt", "requirements.txt"),
        ("has_requirements_dev_txt", "requirements-dev.txt"),
        ("has_venv", ".venv"),
        ("has_dotenv", ".env"),
        ("has_dotenv_example", ".env.example"),
        ("has_tests_directory", "tests/"),
    )
    return [
        marker
        for attribute, marker in marker_attributes
        if getattr(project_info, attribute)
    ]


def _project_finding() -> Finding:
    return Finding(
        id="PYTHON_PROJECT_NOT_DETECTED",
        category="project",
        title="No Python project markers detected",
        severity="warning",
        evidence=(
            "No pyproject.toml or requirements file was found in this directory.",
        ),
        confidence="High",
        recommended_action="Run DevEnv Doctor from the Python project directory.",
        validation_command="python -m pip --version",
    )


def _environment_variable_findings(
    report: EnvironmentVariablesReport,
) -> list[Finding]:
    findings = []
    for variable in report.variables:
        if variable.present:
            continue
        evidence = [
            f"{variable.name} is referenced in Python source but not set in the "
            "process environment."
        ]
        if variable.documented_in_example:
            evidence.append(f"{variable.name} is listed in .env.example.")
        findings.append(
            Finding(
                id="ENV_VAR_MISSING",
                category="environment",
                title="Environment variable missing",
                severity="high",
                evidence=(
                    f"Variable: {variable.name}",
                    f"Source: {', '.join(variable.sources) or 'unknown'}",
                    "Present in process environment: no",
                    f"Listed in .env: {'yes' if variable.listed_in_env else 'no'}",
                    "Declared in .env.example: "
                    f"{'yes' if variable.documented_in_example else 'no'}",
                ),
                confidence="High",
                recommended_action=(
                    f"Set {variable.name} before running the application."
                ),
                validation_command=(
                    f"python -c \"import os; print('{variable.name}' in os.environ)\""
                ),
            )
        )
    return findings


def _dependency_check_lines(findings: list[Finding]) -> list[str]:
    check_lines = []
    for finding in findings:
        evidence = {
            item.partition(": ")[0]: item.partition(": ")[2]
            for item in finding.evidence
        }
        package = evidence.get("Required package", evidence.get("Package", ""))
        requirement = evidence.get("Requirement", evidence.get("Required", ""))
        installed = evidence.get("Installed", "unknown")
        if finding.id == "DEPENDENCY_MISSING":
            check_lines.append(f"{package} not found (required {requirement})")
        else:
            check_lines.append(f"{package} {installed} (required {requirement})")
    return check_lines


def _print_checks(title: str, checks: list[str], style: str, empty: str) -> None:
    console.print(f"\n[bold]{title}[/bold]")
    if not checks:
        console.print(empty)
        return
    symbol = {"green": "✓", "yellow": "⚠", "red": "✗", "cyan": "•"}[style]
    for check in checks:
        console.print(f"[{style}]{symbol} {check}[/{style}]")


@app.callback()
def main() -> None:
    """DevEnv Doctor command-line interface."""


@app.command()
def doctor(json_output: bool = typer.Option(False, "--json")) -> None:
    """Check the current Python project and environment."""
    runtime_info = collect_runtime_info()
    project_info = collect_project_info()
    python_version_finding = analyze_runtime(runtime_info=runtime_info)
    virtual_environment_finding = diagnose_virtual_environment(
        virtual_env_active=runtime_info.virtual_env_active,
        virtual_env_path=runtime_info.virtual_env_path,
        project_venv_exists=project_info.has_venv,
        project_directory=Path.cwd(),
    )
    dependency_findings = diagnose_dependencies()
    environment_report = diagnose_environment_variables()

    findings = [virtual_environment_finding]
    if python_version_finding is not None:
        findings.insert(0, python_version_finding)
    findings.extend(dependency_findings)
    findings.extend(_environment_variable_findings(environment_report))
    if not project_info.is_python_project:
        findings.append(_project_finding())

    passed_checks = ["Python runtime detected"]
    if project_info.is_python_project:
        passed_checks.append("Python project metadata detected")
    passed_checks.extend(
        finding.title for finding in findings if finding.severity == "info"
    )
    if not dependency_findings:
        passed_checks.append("No declared dependency issues detected")
    present_variables = [
        variable.name for variable in environment_report.variables if variable.present
    ]
    passed_checks.extend(f"{name} present" for name in present_variables)
    if not environment_report.variables:
        passed_checks.append("No supported environment-variable references detected")

    errors = [finding for finding in findings if finding.severity == "error"]
    warnings = [
        finding for finding in findings if finding.severity not in {"info", "error"}
    ]
    info_findings = [finding for finding in findings if finding.severity == "info"]
    issues = [*warnings, *errors]
    severity_summary = {
        "errors": len(errors),
        "warnings": len(warnings),
        "info": len(info_findings),
    }

    runtime_table = Table.grid(padding=(0, 2))
    runtime_table.add_column(style="bold", width=14, no_wrap=True)
    runtime_table.add_column(overflow="fold")
    runtime_table.add_row("Python", runtime_info.python_version)
    runtime_table.add_row("Executable", runtime_info.executable_path)
    runtime_table.add_row("OS", runtime_info.operating_system)
    runtime_table.add_row("Architecture", runtime_info.architecture)
    runtime_table.add_row("Virtual Env", runtime_info.virtual_env_path or "Not active")

    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="bold", width=14, no_wrap=True)
    summary.add_column(overflow="fold")
    markers = _project_markers(project_info)
    project_status = (
        f"Python project ({', '.join(markers)})"
        if project_info.is_python_project
        else f"No recognized project ({', '.join(markers) or 'no markers'})"
    )
    environment_status = (
        f"Active ({runtime_info.virtual_env_path})"
        if runtime_info.virtual_env_active
        else "Not active"
    )
    dotenv_status = (
        ", ".join(
            name
            for available, name in (
                (project_info.has_dotenv, ".env"),
                (project_info.has_dotenv_example, ".env.example"),
            )
            if available
        )
        or "no dotenv files"
    )
    summary.add_row("Project", project_status)
    summary.add_row("Virtual Env", environment_status)
    summary.add_row("Environment", dotenv_status)

    if json_output:
        serialized_findings = [asdict(finding) for finding in issues]
        report = {
            "findings": [asdict(finding) for finding in findings],
            "summary": severity_summary,
            "environment_summary": {
                "runtime": asdict(runtime_info),
                "project": {
                    **asdict(project_info),
                    "is_python_project": project_info.is_python_project,
                    "markers": markers,
                },
                "virtual_environment": {
                    "active": runtime_info.virtual_env_active,
                    "path": runtime_info.virtual_env_path,
                },
                "dotenv_files": {
                    ".env": project_info.has_dotenv,
                    ".env.example": project_info.has_dotenv_example,
                },
            },
            "environment_variables": asdict(environment_report),
            "passed_checks": passed_checks,
            "warnings": [asdict(finding) for finding in warnings],
            "errors": [asdict(finding) for finding in errors],
            "diagnosis": serialized_findings,
            "evidence": [
                {
                    "finding_id": finding.id,
                    "title": finding.title,
                    "items": list(finding.evidence),
                }
                for finding in issues
            ],
            "recommended_fixes": [
                {
                    "finding_id": finding.id,
                    "title": finding.title,
                    "action": finding.recommended_action,
                }
                for finding in issues
            ],
        }
        typer.echo(json.dumps(report, indent=2, ensure_ascii=False))
        if errors:
            raise typer.Exit(code=1)
        return

    console.print("[bold cyan]DevEnv Doctor[/bold cyan]")
    console.print("\n[bold]Runtime[/bold]")
    console.rule(style="dim")
    console.print(runtime_table)
    console.print("\n[bold]Environment Summary[/bold]")
    console.print(summary)

    console.print("\n[bold]Environment Variables[/bold]")
    if environment_report.variables:
        for variable in environment_report.variables:
            if variable.present:
                console.print(f"[green]✓ {variable.name}[/green]")
            else:
                console.print(f"[yellow]✗ {variable.name}[/yellow]")
    else:
        console.print("No supported environment-variable references found")

    console.print("\n[bold]Dependencies[/bold]")
    dependency_checks = _dependency_check_lines(dependency_findings)
    if dependency_checks:
        for check in dependency_checks:
            console.print(f"[yellow]✗ {check}[/yellow]")
    else:
        console.print("[green]✓ No declared dependency issues detected[/green]")

    _print_checks("Passed checks", passed_checks, "green", "None")
    _print_checks("Warnings", [finding.title for finding in warnings], "yellow", "None")
    _print_checks("Errors", [finding.title for finding in errors], "red", "None")
    _print_checks(
        "Diagnosis",
        [f"{finding.severity.upper()} | {finding.title}" for finding in issues],
        "yellow",
        "No issues found",
    )

    evidence_lines = [
        f"{finding.title}: {'; '.join(finding.evidence)}" for finding in issues
    ]
    _print_checks("Evidence", evidence_lines, "yellow", "None")
    fixes = list(dict.fromkeys(finding.recommended_action for finding in issues))
    _print_checks("Recommended fixes", fixes, "cyan", "None")
    console.print("\n[bold]Summary[/bold]")
    if not warnings and not errors:
        console.print("No issues detected.")
    console.print(f"Errors: {severity_summary['errors']}")
    console.print(f"Warnings: {severity_summary['warnings']}")
    console.print(f"Info: {severity_summary['info']}")
    if errors:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
