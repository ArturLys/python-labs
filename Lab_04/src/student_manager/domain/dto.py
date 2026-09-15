"""Dict shapes for the outside world (JSON, CSV rows, a future REST API) and converters.

A TypedDict is still a dict at runtime: no validation, no methods, no identity. That is exactly why
it stays at the boundary: Student.from_payload() / Student.to_dict() and group_to_report() are the
only places where a payload becomes an entity or an entity becomes a payload.
"""

from __future__ import annotations

from typing import NotRequired, TypedDict

from student_manager.domain.models import Group
from student_manager.domain.value_objects import AcademicStatus


class StudentPayload(TypedDict):
    """Incoming student record; email may be absent."""

    id: int
    first_name: str
    last_name: str
    group: str
    email: NotRequired[str]


class GradePayload(TypedDict):
    """One row of a grade import: who, which course, how many points."""

    student_id: int
    course_id: int
    points: float


class StudentReport(TypedDict):
    """What the reporting service says about one student."""

    id: int
    name: str
    group: str
    courses: int
    grades: int
    average: float | None
    credits: int
    status: AcademicStatus


class GroupReport(TypedDict):
    code: str
    students: int
    average: float | None
    best: str | None


def group_to_report(group: Group) -> GroupReport:
    graded = [s for s in group if s.average is not None]
    best = max(graded, key=lambda s: s.average or 0.0, default=None)
    return {
        "code": str(group.code),
        "students": len(group),
        "average": group.average,
        "best": best.name.full if best is not None else None,
    }
