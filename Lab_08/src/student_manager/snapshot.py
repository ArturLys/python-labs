"""A dated summary of a registry: what the dashboard shows and what the export writes."""

from __future__ import annotations

from typing import TypedDict

from student_manager import clock
from student_manager.registry import StudentRegistry


class Snapshot(TypedDict):
    generated_at: str
    total: int
    groups: dict[str, float]
    excellent: list[str]


def registry_snapshot(registry: StudentRegistry) -> Snapshot:
    """Group averages are rounded to one decimal, so two runs over the same data compare equal."""
    return Snapshot(
        generated_at=clock.now().isoformat(timespec="seconds"),
        total=len(registry),
        groups={group: round(registry.group_average(group), 1) for group in registry.groups()},
        excellent=sorted(student.full_name for student in registry if student.is_excellent),
    )
