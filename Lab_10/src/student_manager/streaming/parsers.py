"""Parsing and validation stages: raw lines -> csv rows -> StudentRecord, counting what was rejected and why."""

from __future__ import annotations

import csv
from collections import Counter
from collections.abc import Generator, Iterable, Iterator
from dataclasses import dataclass, field

from student_manager.config import GRADE_MAX, GRADE_MIN
from student_manager.streaming.models import COLUMNS, RawRow, StudentRecord


def clean_lines(lines: Iterable[str]) -> Iterator[str]:
    """Strip whitespace and drop empty lines; one line in flight at a time."""
    for line in lines:
        value = line.strip()
        if value:
            yield value


def parse_rows(lines: Iterable[str]) -> Generator[RawRow, None, None]:
    """csv.DictReader is lazy itself: it takes the header on the first next(), then one row per next()."""
    yield from csv.DictReader(lines)


@dataclass
class ValidationReport:
    """Counters filled while validate() runs; they mean something only after the stream has been drained."""

    accepted: int = 0
    rejected: Counter[str] = field(default_factory=Counter)

    @property
    def seen(self) -> int:
        return self.accepted + sum(self.rejected.values())


def _field(row: RawRow, column: str) -> str:
    value = row.get(column)
    if value is None:  # DictReader fills missing trailing columns with None
        raise ValueError("missing_column")
    return value.strip()


def parse_record(row: RawRow) -> StudentRecord:
    """One raw row -> StudentRecord, or ValueError whose message is a short reason code."""
    id_text, name, group, grade_text = (_field(row, column) for column in COLUMNS)
    if not name or not group:
        raise ValueError("empty_field")
    try:
        student_id, grade = int(id_text), float(grade_text)
    except ValueError as error:
        raise ValueError("not_a_number") from error
    if not GRADE_MIN <= grade <= GRADE_MAX:
        raise ValueError("out_of_range")
    return StudentRecord(student_id, name, group, grade)


def validate(rows: Iterable[RawRow], report: ValidationReport | None = None) -> Iterator[StudentRecord]:
    """Generator: valid rows pass through, invalid ones are counted by reason and dropped, never raised."""
    for row in rows:
        try:
            record = parse_record(row)
        except ValueError as error:
            if report is not None:
                report.rejected[str(error)] += 1
            continue
        if report is not None:
            report.accepted += 1
        yield record
