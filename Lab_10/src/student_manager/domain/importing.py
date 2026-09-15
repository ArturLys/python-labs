"""The same behaviour built two ways — the inheritance-vs-composition experiment of the lab.

Task: turn text lines "student_id,course_id,points" into validated, formatted rows.
Variant A: a base class with a template method; a subclass fills in the parsing step.
Variant B: a plain class that *has* a parser, a validator and a formatter, each behind its own
small Protocol.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Protocol

from student_manager.domain.dto import GradePayload
from student_manager.domain.value_objects import Grade

# ----------------------------------------------------------------------------- variant A: inheritance


class BaseGradeImporter(ABC):
    """Template method: import_lines() fixes the algorithm, subclasses may only vary the steps."""

    def import_lines(self, lines: Iterable[str]) -> list[str]:
        return [self.format_row(self.validate(self.parse_line(line))) for line in lines if line.strip()]

    @abstractmethod
    def parse_line(self, line: str) -> GradePayload: ...

    def validate(self, row: GradePayload) -> tuple[GradePayload, Grade]:
        return row, Grade(row["points"])

    def format_row(self, checked: tuple[GradePayload, Grade]) -> str:
        row, grade = checked
        return f"{row['student_id']}:{row['course_id']} -> {grade}"


class CsvGradeImporter(BaseGradeImporter):
    def parse_line(self, line: str) -> GradePayload:
        student_id, course_id, points = (part.strip() for part in line.split(","))
        return {"student_id": int(student_id), "course_id": int(course_id), "points": float(points)}


# ----------------------------------------------------------------------------- variant B: composition


class LineParser(Protocol):
    def parse(self, line: str) -> GradePayload: ...


class GradeValidator(Protocol):
    def validate(self, row: GradePayload) -> Grade: ...


class RowFormatter(Protocol):
    def format(self, row: GradePayload, grade: Grade) -> str: ...


class DelimitedParser:
    def __init__(self, delimiter: str = ",") -> None:
        self.delimiter = delimiter

    def parse(self, line: str) -> GradePayload:
        student_id, course_id, points = (part.strip() for part in line.split(self.delimiter))
        return {"student_id": int(student_id), "course_id": int(course_id), "points": float(points)}


class RangeValidator:
    def validate(self, row: GradePayload) -> Grade:
        return Grade(row["points"])


class ArrowFormatter:
    def format(self, row: GradePayload, grade: Grade) -> str:
        return f"{row['student_id']}:{row['course_id']} -> {grade}"


class TableFormatter:
    def format(self, row: GradePayload, grade: Grade) -> str:
        return f"| {row['student_id']:>3} | {row['course_id']:>3} | {grade.points:5.1f} | {grade.ects:<2} |"


class GradeImporter:
    """Has-a parser, validator and formatter; knows nothing about how any of them works."""

    def __init__(self, parser: LineParser, validator: GradeValidator, formatter: RowFormatter) -> None:
        self._parser = parser
        self._validator = validator
        self._formatter = formatter

    def import_lines(self, lines: Iterable[str]) -> list[str]:
        result: list[str] = []
        for line in lines:
            if not line.strip():
                continue
            row = self._parser.parse(line)
            result.append(self._formatter.format(row, self._validator.validate(row)))
        return result
