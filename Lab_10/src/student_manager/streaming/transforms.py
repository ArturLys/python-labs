"""Transformation stage: tidy each record, and adapt the stream to the GradeRecord shape of lab 2."""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator

from student_manager.analytics.data import GradeRecord
from student_manager.streaming.models import StudentRecord

_SPACES = re.compile(r"\s+")


def tidy(record: StudentRecord) -> StudentRecord:
    """Collapse spaces and title-case the name, upper-case the group prefix («феп-31с» -> «ФЕП-31с»)."""
    prefix, dash, rest = record.group.partition("-")
    return record._replace(
        name=_SPACES.sub(" ", record.name.strip()).title(),
        group=f"{prefix.upper()}{dash}{rest.lower()}",
    )


def normalize(records: Iterable[StudentRecord]) -> Iterator[StudentRecord]:
    """Mapping stage as a generator expression over tidy()."""
    return (tidy(record) for record in records)


def to_grade_records(records: Iterable[StudentRecord], discipline: str) -> Iterator[GradeRecord]:
    """Bridge to lab 2: the same stream in the shape that the analytics package understands."""
    return (GradeRecord(record.name, record.group, discipline, record.grade) for record in records)
