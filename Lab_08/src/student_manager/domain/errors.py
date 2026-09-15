"""Exceptions of the domain layer.

Every class below descends from the project-wide StudentManagerError (lab 1), so the console menu
and future API handlers keep catching one base type. Grade and group validation reuse
InvalidGradeError / InvalidGroupError from lab 1 unchanged.
"""

from __future__ import annotations

from student_manager.exceptions import StudentManagerError


class DomainError(StudentManagerError):
    """Base for every rule violation inside the object model."""


class EntityNotFoundError(DomainError, LookupError):
    """A repository lookup by id found nothing."""

    def __init__(self, kind: str, entity_id: int) -> None:
        super().__init__(f"{kind} з id={entity_id} не знайдено")
        self.kind = kind
        self.entity_id = entity_id


class DuplicateEntityError(DomainError, ValueError):
    """Two different objects claim the same identity or the same seat."""


class EnrollmentError(DomainError, ValueError):
    """Base for everything that can go wrong with course enrollment."""


class AlreadyEnrolledError(EnrollmentError):
    """The student is enrolled in this course already."""


class NotEnrolledError(EnrollmentError):
    """A grade for a course the student never enrolled in."""


class WrongGroupError(EnrollmentError):
    """A student put into a group whose code differs from his own."""
