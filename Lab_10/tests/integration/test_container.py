"""Integration: the lab-4 composition root with a Mock notifier instead of the console one."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from student_manager.domain import Container, Course, EntityNotFoundError, Notifier, Student, Teacher
from student_manager.domain.value_objects import Credits, PersonName


@pytest.fixture
def notifier() -> Mock:
    return Mock(spec=Notifier)


@pytest.fixture
def app(notifier: Mock) -> Container:
    container = Container.build(notifier=notifier)
    teacher = Teacher(1, PersonName("Ігор", "Петришин"), "кафедра програмування")
    container.courses.add(Course(10, "Професійний Python", Credits(5), teacher))
    return container


def admit(container: Container, student_id: int, first: str, last: str, email: str) -> Student:
    student = Student.from_payload(
        {
            "id": student_id,
            "first_name": first,
            "last_name": last,
            "group": "ФЕП-31с",
            "email": email,
        }
    )
    container.enrollment.admit(student)
    container.enrollment.enroll(student_id, 10)
    return student


def test_admission_enrollment_and_a_failing_grade_notify(app: Container, notifier: Mock) -> None:
    marta = admit(app, 1, "Марта", "Гнатишин", "marta@lnu.edu.ua")
    ostap = admit(app, 2, "Остап", "Дзюба", "ostap@lnu.edu.ua")
    app.grading.grade(1, 10, 95)
    app.grading.grade(2, 10, 35)

    assert notifier.send.call_count == 5  # 2 admissions + 2 enrollments + 1 failing grade
    recipient, message = notifier.send.call_args.args
    assert recipient == ostap.contact
    assert "Незадовільна" in message and "Професійний Python" in message
    assert app.grading.average_of(1) == pytest.approx(95.0)
    assert app.reporting.ranking()[0][0] is marta


def test_unknown_student_raises_and_sends_nothing(app: Container, notifier: Mock) -> None:
    with pytest.raises(EntityNotFoundError):
        app.enrollment.enroll(99, 10)
    notifier.send.assert_not_called()


def test_group_report_after_grading(app: Container) -> None:
    admit(app, 1, "Марта", "Гнатишин", "marta@lnu.edu.ua")
    app.grading.grade(1, 10, 90)
    (report,) = app.reporting.group_reports()
    assert report["code"] == "ФЕП-31с"
    assert report["students"] == 1
    assert report["average"] == pytest.approx(90.0)
    assert report["best"] == "Гнатишин Марта"
