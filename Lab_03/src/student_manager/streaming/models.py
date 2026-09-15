"""Row model of the streaming pipeline: one validated line of the input CSV (variant 1)."""

from __future__ import annotations

from typing import NamedTuple

COLUMNS: tuple[str, ...] = ("student_id", "name", "group", "grade")

RawRow = dict[str, str]


class StudentRecord(NamedTuple):
    """A parsed `student_id,name,group,grade` row. A tuple: small, immutable, cheap to create by the million."""

    student_id: int
    name: str
    group: str
    grade: float
