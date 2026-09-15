"""Data transfer objects: the shape of the external files, kept apart from the domain model.

    CSV / JSON / YAML  ->  Row (dict)  ->  StudentRow (validated DTO)  ->  Student (domain, lab 1)

The registry's Student has no id and no e-mail, and splits the name in two; the files (variant 1) have
student_id, name, group, grade, email. The DTO is where the two shapes meet, so neither side has to bend.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from student_manager.analytics.data import GradeRecord
from student_manager.models import Student

# One parsed record as it comes from a file. CSV gives str values, JSON/YAML give real types.
Row = dict[str, object]

STUDENT_FIELDS: tuple[str, ...] = ("student_id", "name", "group", "grade", "email")
GRADE_FIELDS: tuple[str, ...] = ("student", "group", "discipline", "grade")


@dataclass(frozen=True, slots=True)
class StudentRow:
    """Variant-1 input schema: student_id, name ("Прізвище Ім'я"), group, grade, email."""

    student_id: int
    name: str
    group: str
    grade: float
    email: str

    def to_dict(self) -> Row:
        return asdict(self)

    def to_student(self) -> Student:
        """Domain conversion. The model re-checks the group pattern and the grade range itself."""
        last_name, _, first_name = self.name.partition(" ")
        return Student(first_name=first_name, last_name=last_name, group=self.group, average_grade=self.grade)

    @classmethod
    def from_student(cls, student: Student, *, student_id: int, email: str) -> StudentRow:
        return cls(student_id, student.full_name, student.group, student.average_grade, email)


def grade_record_to_dict(record: GradeRecord) -> Row:
    """GradeRecord is a NamedTuple: json would write it as a list, so name the columns explicitly."""
    return record._asdict()
