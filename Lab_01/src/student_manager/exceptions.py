"""Domain-specific exceptions. Callers catch StudentManagerError to handle any of them at once."""

from student_manager.config import GRADE_MAX, GRADE_MIN


class StudentManagerError(Exception):
    """Base class for every error raised by the project."""


class InvalidGradeError(StudentManagerError, ValueError):
    """Average grade outside the 100-point scale."""

    def __init__(self, grade: float) -> None:
        super().__init__(f"середній бал має бути в межах {GRADE_MIN:g}..{GRADE_MAX:g}, отримано {grade!r}")
        self.grade = grade


class InvalidGroupError(StudentManagerError, ValueError):
    """Group name that does not look like ФЕП-31с."""

    def __init__(self, group: str) -> None:
        super().__init__(f"назва групи {group!r} не схожа на ФЕП-31с")
        self.group = group


class StudentNotFoundError(StudentManagerError, LookupError):
    """A query matched no student."""
