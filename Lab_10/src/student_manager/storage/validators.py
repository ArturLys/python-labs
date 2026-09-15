"""Validation at the system boundary: raw rows in, checked DTOs out.

Every failure is a RecordValidationError that knows the line and the field and keeps the low-level
cause (ValueError, InvalidGroupError, ...) attached through `raise ... from error`.
"""

from __future__ import annotations

import re

from student_manager.analytics.data import DISCIPLINES, GradeRecord
from student_manager.config import GRADE_MAX, GRADE_MIN
from student_manager.exceptions import InvalidGroupError, StudentManagerError
from student_manager.models import Student
from student_manager.storage.dto import Row, StudentRow
from student_manager.storage.exceptions import RecordValidationError

# "Basic level": one @, something before it, a dot after it, no whitespace. RFC 5322 is not the point.
EMAIL_PATTERN = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


def text_of(value: object) -> str:
    """CSV gives str, JSON/YAML give int/float/None: normalise to a stripped string ('' for missing)."""
    return "" if value is None else str(value).strip()


def parse_id(row: Row, line_number: int, field: str = "student_id") -> int:
    """EAFP: try int() and turn the ValueError into a domain error instead of pre-checking with regex."""
    try:
        value = int(text_of(row.get(field)))
    except ValueError as error:
        raise RecordValidationError(
            f"{field} має бути цілим числом, отримано {text_of(row.get(field))!r}", line_number=line_number, field=field
        ) from error
    if value <= 0:
        raise RecordValidationError(
            f"{field} має бути додатним, отримано {value}", line_number=line_number, field=field
        )
    return value


def parse_grade(value: object, line_number: int, field: str = "grade") -> float:
    """float() with a decimal comma allowed; NaN and infinities fail the range check like any other number."""
    try:
        grade = float(text_of(value).replace(",", "."))
    except ValueError as error:
        raise RecordValidationError(
            f"{field} має бути числом, отримано {text_of(value)!r}", line_number=line_number, field=field
        ) from error
    if not GRADE_MIN <= grade <= GRADE_MAX:
        raise RecordValidationError(
            f"{field} має бути в межах {GRADE_MIN:g}..{GRADE_MAX:g}, отримано {grade:g}",
            line_number=line_number,
            field=field,
        )
    return grade


def parse_required_text(row: Row, field: str, line_number: int) -> str:
    value = text_of(row.get(field))
    if not value:
        raise RecordValidationError(f"поле {field} порожнє", line_number=line_number, field=field)
    return value


def parse_student_row(row: Row, line_number: int) -> StudentRow:
    """Parse and validate one raw row; the domain model gets the last word (group pattern, grade range)."""
    student_id = parse_id(row, line_number)
    name = parse_required_text(row, "name", line_number)
    if len(name.split()) < 2:
        raise RecordValidationError(
            f"name має містити прізвище та ім'я, отримано {name!r}", line_number=line_number, field="name"
        )
    group = parse_required_text(row, "group", line_number)
    grade = parse_grade(row.get("grade"), line_number)
    email = parse_required_text(row, "email", line_number)
    if not EMAIL_PATTERN.fullmatch(email):
        raise RecordValidationError(f"email {email!r} не схожий на адресу", line_number=line_number, field="email")
    dto = StudentRow(student_id, name, group, grade, email)
    to_student(dto, line_number=line_number)
    return dto


def to_student(row: StudentRow, *, line_number: int | None = None) -> Student:
    """Domain conversion. The model's own exceptions (lab 1) become validation errors with the cause kept."""
    try:
        return row.to_student()
    except StudentManagerError as error:
        field = "group" if isinstance(error, InvalidGroupError) else "grade"
        raise RecordValidationError(str(error), line_number=line_number, field=field) from error


def parse_grade_record(row: Row, line_number: int) -> GradeRecord:
    """Row of the lab-2 data set: student, group, discipline (one of the four known), grade."""
    student = parse_required_text(row, "student", line_number)
    group = parse_required_text(row, "group", line_number)
    discipline = parse_required_text(row, "discipline", line_number)
    if discipline not in DISCIPLINES:
        raise RecordValidationError(f"невідома дисципліна {discipline!r}", line_number=line_number, field="discipline")
    return GradeRecord(student, group, discipline, parse_grade(row.get("grade"), line_number))
