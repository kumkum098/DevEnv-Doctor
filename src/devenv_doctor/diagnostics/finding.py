"""Shared model for diagnostic findings."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Finding:
    """A single actionable diagnosis result."""

    id: str
    category: str
    title: str
    severity: str
    evidence: tuple[str, ...]
    confidence: str
    recommended_action: str
    validation_command: str
