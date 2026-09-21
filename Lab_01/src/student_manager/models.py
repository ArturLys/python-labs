"""Data model of the registry."""

from __future__ import annotations

import re
from dataclasses import dataclass

from student_manager.config import EXCELLENT_THRESHOLD, GRADE_MAX, GRADE_MIN, GROUP_PATTERN
from student_manager.exceptions import InvalidGradeError, InvalidGroupError


@dataclass(slots=True)
class Student:
    """One student: name, academic group and average grade on the 100-point scale."""

    first_name: str
    last_name: str
    group: str
    average_grade: float

    def __post_init__(self) -> None:
        self.first_name = self.first_name.strip()
        self.last_name = self.last_name.strip()
        self.group = self.group.strip()
        if not self.first_name or not self.last_name:
            raise ValueError("ім'я та прізвище не можуть бути порожніми")
        if not re.fullmatch(GROUP_PATTERN, self.group):
            raise InvalidGroupError(self.group)
        if not GRADE_MIN <= self.average_grade <= GRADE_MAX:
            raise InvalidGradeError(self.average_grade)

    @property
    def full_name(self) -> str:
        return f"{self.last_name} {self.first_name}"

    @property
    def is_excellent(self) -> bool:
        return self.average_grade >= EXCELLENT_THRESHOLD
