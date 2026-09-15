"""Hand-written dependency injection container: the one place where concrete classes meet.

Nothing else in the package knows that repositories are dicts or that notifications go to the
console. Swap a field here (or pass another object to build()) and every service follows.
"""

from __future__ import annotations

from dataclasses import dataclass

from student_manager.domain.models import Course, Group, Student
from student_manager.domain.notifications import ConsoleNotifier
from student_manager.domain.protocols import Notifier
from student_manager.domain.repositories import InMemoryRepository, Repository
from student_manager.domain.services import (
    AcademicStatusPolicy,
    EnrollmentService,
    GradingService,
    ReportingService,
    ThresholdPolicy,
)


@dataclass(frozen=True, slots=True)
class Container:
    students: Repository[Student]
    courses: Repository[Course]
    groups: Repository[Group]
    notifier: Notifier
    policy: AcademicStatusPolicy
    enrollment: EnrollmentService
    grading: GradingService
    reporting: ReportingService

    @classmethod
    def build(cls, notifier: Notifier | None = None, policy: AcademicStatusPolicy | None = None) -> Container:
        """Composition root. Defaults are the demo wiring; tests pass their own doubles."""
        notifier = notifier if notifier is not None else ConsoleNotifier()
        policy = policy if policy is not None else ThresholdPolicy()
        students: Repository[Student] = InMemoryRepository(kind="студент")
        courses: Repository[Course] = InMemoryRepository(kind="курс")
        groups: Repository[Group] = InMemoryRepository(kind="група")
        return cls(
            students=students,
            courses=courses,
            groups=groups,
            notifier=notifier,
            policy=policy,
            enrollment=EnrollmentService(students, courses, groups, notifier),
            grading=GradingService(students, courses, notifier, policy),
            reporting=ReportingService(students, groups, policy),
        )
