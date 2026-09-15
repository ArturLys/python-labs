"""Application layer: use cases that orchestrate entities, repositories and notifiers.

Services hold no domain rules of their own — the entities guard those. What a service does is
fetch the right objects, call the right method, persist and notify. Every dependency comes in
through __init__ (dependency injection) and is typed by its abstraction, never by a concrete class.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping

from student_manager.config import EXCELLENT_THRESHOLD
from student_manager.domain.dto import GroupReport, StudentReport, group_to_report
from student_manager.domain.models import Course, Group, Student
from student_manager.domain.protocols import Notifier, Serializable
from student_manager.domain.repositories import Repository
from student_manager.domain.value_objects import PASSING_THRESHOLD, AcademicStatus, Grade


class AcademicStatusPolicy(ABC):
    """Strategy: how a student's grades turn into a status. Swappable without touching services."""

    @abstractmethod
    def status_of(self, student: Student) -> AcademicStatus: ...


class ThresholdPolicy(AcademicStatusPolicy):
    """Looks only at the average."""

    def __init__(self, excellent: float = EXCELLENT_THRESHOLD, passing: float = PASSING_THRESHOLD) -> None:
        self.excellent = excellent
        self.passing = passing

    def status_of(self, student: Student) -> AcademicStatus:
        average = student.average
        if average is None:
            return AcademicStatus.NO_GRADES
        if average >= self.excellent:
            return AcademicStatus.EXCELLENT
        if average >= self.passing:
            return AcademicStatus.GOOD
        return AcademicStatus.AT_RISK


class StrictPolicy(ThresholdPolicy):
    """Same thresholds, but a single failing grade puts the student at risk whatever his average."""

    def status_of(self, student: Student) -> AcademicStatus:
        if any(not grade.is_passing for _, grade in student.book):
            return AcademicStatus.AT_RISK
        return super().status_of(student)


class EnrollmentService:
    """Admits students to groups and enrolls them in courses."""

    def __init__(
        self,
        students: Repository[Student],
        courses: Repository[Course],
        groups: Repository[Group],
        notifier: Notifier,
    ) -> None:
        self._students = students
        self._courses = courses
        self._groups = groups
        self._notifier = notifier

    def admit(self, student: Student) -> Group:
        """Register a new student and seat him in the group his code points to."""
        group = next(iter(self._groups.find(lambda g: g.code == student.group)), None)
        if group is None:
            group = Group(len(self._groups) + 1, student.group)
            self._groups.add(group)
        self._students.add(student)
        group.add(student)
        self._notifier.send(student.contact, f"Вас зараховано до групи {group.code}")
        return group

    def enroll(self, student_id: int, course_id: int) -> Student:
        student = self._students.require(student_id)
        course = self._courses.require(course_id)
        student.enroll(course)
        self._notifier.send(student.contact, f"Вас записано на курс «{course.title}»")
        return student


class GradingService:
    """Records grades and answers the two questions everybody asks: average and status."""

    def __init__(
        self,
        students: Repository[Student],
        courses: Repository[Course],
        notifier: Notifier,
        policy: AcademicStatusPolicy,
    ) -> None:
        self._students = students
        self._courses = courses
        self._notifier = notifier
        self._policy = policy

    def grade(self, student_id: int, course_id: int, points: float) -> Grade:
        student = self._students.require(student_id)
        course = self._courses.require(course_id)
        grade = Grade(points)
        student.record(course, grade)
        if not grade.is_passing:
            self._notifier.send(student.contact, f"Незадовільна оцінка з «{course.title}»: {grade}")
        return grade

    def average_of(self, student_id: int) -> float | None:
        return self._students.require(student_id).average

    def status_of(self, student_id: int) -> AcademicStatus:
        return self._policy.status_of(self._students.require(student_id))


class ReportingService:
    """Read-only views over the repositories: rankings, per-student and per-group reports."""

    def __init__(self, students: Repository[Student], groups: Repository[Group], policy: AcademicStatusPolicy) -> None:
        self._students = students
        self._groups = groups
        self._policy = policy

    def ranking(self) -> list[tuple[Student, float]]:
        graded = [(s, s.average) for s in self._students.all() if s.average is not None]
        return sorted(graded, key=lambda pair: (-pair[1], pair[0].name.full))

    def student_report(self, student_id: int) -> StudentReport:
        student = self._students.require(student_id)
        return {
            "id": student.id,
            "name": student.name.full,
            "group": str(student.group),
            "courses": len(student.book.courses),
            "grades": len(student.book),
            "average": student.average,
            "credits": student.book.earned_credits.ects,
            "status": self._policy.status_of(student),
        }

    def group_reports(self) -> list[GroupReport]:
        return [group_to_report(g) for g in sorted(self._groups.all(), key=lambda g: str(g.code))]

    def with_status(self, status: AcademicStatus) -> list[Student]:
        return self._students.find(lambda s: self._policy.status_of(s) is status)

    @staticmethod
    def export(objects: Iterable[object]) -> list[Mapping[str, object]]:
        """Serialise whatever knows how; the runtime_checkable protocol filters the rest out."""
        return [obj.to_dict() for obj in objects if isinstance(obj, Serializable)]
