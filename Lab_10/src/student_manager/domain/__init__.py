"""Typed object model of the student-accounting domain (lab 4).

Layers, inner to outer: value_objects → models → protocols/repositories/dto → services → container.
The lab-1 dataclass `student_manager.models.Student` stays as the minimal model for the console
menu; this package is its professional successor and the base for the database and API labs.
"""

from student_manager.domain.container import Container
from student_manager.domain.dto import GradePayload, GroupReport, StudentPayload, StudentReport, group_to_report
from student_manager.domain.errors import (
    AlreadyEnrolledError,
    DomainError,
    DuplicateEntityError,
    EnrollmentError,
    EntityNotFoundError,
    NotEnrolledError,
    WrongGroupError,
)
from student_manager.domain.models import Course, Entity, GradeBook, Group, Person, Student, Teacher
from student_manager.domain.notifications import ConsoleNotifier, RecordingNotifier
from student_manager.domain.protocols import HasId, Notifier, Serializable
from student_manager.domain.repositories import InMemoryRepository, Repository
from student_manager.domain.services import (
    AcademicStatusPolicy,
    EnrollmentService,
    GradingService,
    ReportingService,
    StrictPolicy,
    ThresholdPolicy,
)
from student_manager.domain.value_objects import (
    AcademicStatus,
    Credits,
    Grade,
    GroupCode,
    PersonName,
    validated_points,
)

__all__ = [
    "AcademicStatus",
    "AcademicStatusPolicy",
    "AlreadyEnrolledError",
    "ConsoleNotifier",
    "Container",
    "Course",
    "Credits",
    "DomainError",
    "DuplicateEntityError",
    "EnrollmentError",
    "EnrollmentService",
    "Entity",
    "EntityNotFoundError",
    "Grade",
    "GradeBook",
    "GradePayload",
    "GradingService",
    "Group",
    "GroupCode",
    "GroupReport",
    "HasId",
    "InMemoryRepository",
    "NotEnrolledError",
    "Notifier",
    "Person",
    "PersonName",
    "RecordingNotifier",
    "ReportingService",
    "Repository",
    "Serializable",
    "StrictPolicy",
    "Student",
    "StudentPayload",
    "StudentReport",
    "Teacher",
    "ThresholdPolicy",
    "WrongGroupError",
    "group_to_report",
    "validated_points",
]
