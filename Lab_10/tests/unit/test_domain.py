from dataclasses import FrozenInstanceError

import pytest

from student_manager.domain import (
    AcademicStatus,
    AlreadyEnrolledError,
    Container,
    Course,
    Credits,
    DomainError,
    DuplicateEntityError,
    EntityNotFoundError,
    Grade,
    GradeBook,
    Group,
    GroupCode,
    InMemoryRepository,
    NotEnrolledError,
    PersonName,
    RecordingNotifier,
    Serializable,
    StrictPolicy,
    Student,
    StudentPayload,
    Teacher,
    ThresholdPolicy,
    WrongGroupError,
    validated_points,
)
from student_manager.domain.importing import (
    ArrowFormatter,
    CsvGradeImporter,
    DelimitedParser,
    GradeImporter,
    RangeValidator,
    TableFormatter,
)
from student_manager.exceptions import InvalidGradeError, InvalidGroupError, StudentManagerError

TEACHER = Teacher(1, PersonName("Олена", "Ткаченко"), "кафедра програмування")


def course(course_id: int = 10, title: str = "Професійний Python", credits: int = 4) -> Course:
    return Course(course_id, title, Credits(credits), TEACHER)


def student(student_id: int = 1, group: str = "ФЕП-31с") -> Student:
    return Student(student_id, PersonName("Марта", "Гнатишин"), GroupCode(group))


# ----------------------------------------------------------------------------- value objects


def test_grade_is_frozen_validated_and_ordered() -> None:
    grade = Grade(95)
    assert grade.points == 95.0 and grade.ects == "A" and grade.is_excellent
    with pytest.raises(FrozenInstanceError):
        grade.points = 10  # type: ignore[misc]
    with pytest.raises(InvalidGradeError):
        Grade(100.5)
    assert Grade(58) < Grade(60) <= Grade(60.0) and Grade(90) == Grade(90.0)
    assert max(Grade(81), Grade(95), Grade(60.5)) == Grade(95)
    assert [g.ects for g in (Grade(59), Grade(60), Grade(70), Grade(75), Grade(85), Grade(90))] == [
        "FX",
        "E",
        "D",
        "C",
        "B",
        "A",
    ]


def test_validated_points_keeps_the_type() -> None:
    assert validated_points(90) == 90 and isinstance(validated_points(90), int)
    assert validated_points(90.5) == 90.5
    with pytest.raises(InvalidGradeError):
        validated_points(-1)


def test_person_name_and_group_code_normalise_and_validate() -> None:
    name = PersonName(" Марта ", "Гнатишин ")
    assert name.full == "Гнатишин Марта" and name.initials == "Гнатишин М."
    with pytest.raises(ValueError):
        PersonName("", "Гнатишин")
    code = GroupCode(" ФЕП-31с ")
    assert (code.faculty, code.stream, str(code)) == ("ФЕП", "31", "ФЕП-31с")
    with pytest.raises(InvalidGroupError):
        GroupCode("31-ФЕП")


def test_credits_add_and_sum() -> None:
    assert Credits(4) + Credits(3) == Credits(7)
    assert sum((Credits(4), Credits(3)), start=Credits(0)) == Credits(7)
    with pytest.raises(ValueError):
        Credits(-1)


# ----------------------------------------------------------------------------- entities


def test_entities_compare_by_id_and_type() -> None:
    a, b = student(1), Student(1, PersonName("Інше", "Ім'я"), GroupCode("ФЕП-32"))
    assert a == b and hash(a) == hash(b) and len({a, b}) == 1
    assert a != student(2)
    assert a != Teacher(1, PersonName("Марта", "Гнатишин"), "кафедра")
    with pytest.raises(ValueError):
        student(0)


def test_inheritance_chain_and_str() -> None:
    s = student()
    assert isinstance(s, Student) and str(s) == "Гнатишин Марта, ФЕП-31с"
    assert str(TEACHER) == "Ткаченко Олена (кафедра програмування)"
    assert [cls.__name__ for cls in Student.__mro__[:3]] == ["Student", "Person", "Entity"]


def test_gradebook_is_a_collection() -> None:
    book = GradeBook()
    python, c_lang = course(10), course(11, "Мова С")
    book.enroll(python)
    book.enroll(c_lang)
    book.add(python, Grade(95))
    book.add(python, Grade(85))
    book.add(c_lang, Grade(50))
    assert len(book) == 3 and python in book and course(12) not in book
    assert book[python] == (Grade(95), Grade(85))
    assert [(c.title, g.points) for c, g in book] == [
        ("Професійний Python", 95),
        ("Професійний Python", 85),
        ("Мова С", 50),
    ]
    assert book.average == pytest.approx((95 + 85 + 50) / 3)
    assert book.average_for(python) == 90 and book.earned_credits == Credits(4)
    with pytest.raises(AlreadyEnrolledError):
        book.enroll(python)
    with pytest.raises(NotEnrolledError):
        book.add(course(12), Grade(70))
    with pytest.raises(NotEnrolledError):
        book[course(12)]


def test_empty_gradebook_has_no_average() -> None:
    s = student()
    assert s.average is None and len(s.book) == 0 and s.book.earned_credits == Credits(0)


def test_group_roster_rules() -> None:
    group = Group(1, GroupCode("ФЕП-31с"))
    group.add(student(1))
    assert len(group) == 1 and student(1) in group and group.average is None
    with pytest.raises(DuplicateEntityError):
        group.add(student(1))
    with pytest.raises(WrongGroupError):
        group.add(student(2, "ФЕП-32"))


# ----------------------------------------------------------------------------- repository and DTO


def test_generic_repository() -> None:
    repo = InMemoryRepository[Teacher]([TEACHER], kind="викладач")
    assert len(repo) == 1 and 1 in repo and 2 not in repo and repo.get(2) is None
    assert repo.require(1) is TEACHER
    with pytest.raises(EntityNotFoundError) as info:
        repo.require(2)
    assert "викладач" in str(info.value) and info.value.entity_id == 2
    with pytest.raises(DuplicateEntityError):
        repo.add(TEACHER)
    assert repo.remove(1) is True and repo.remove(1) is False and repo.all() == []


def test_payload_round_trip_and_optional_email() -> None:
    payload: StudentPayload = {"id": 5, "first_name": "Ірина", "last_name": "Пасічник", "group": "ФЕП-32"}
    s = Student.from_payload(payload)
    assert s.email is None and s.contact == "Пасічник Ірина" and s.to_dict() == payload
    with_email: StudentPayload = {**payload, "email": "i@lnu.edu.ua"}
    assert Student.from_payload(with_email).to_dict() == with_email


def test_serializable_is_structural() -> None:
    assert isinstance(student(), Serializable) and isinstance(Grade(70), Serializable)
    assert not isinstance(TEACHER, Serializable) and not isinstance("text", Serializable)
    assert Grade(70).to_dict() == {"points": 70.0, "ects": "D"}


# ----------------------------------------------------------------------------- services


@pytest.fixture
def app() -> tuple[Container, RecordingNotifier]:
    log = RecordingNotifier()
    container = Container.build(notifier=log)
    container.courses.add(course(10))
    container.courses.add(course(11, "Мова С"))
    return container, log


def test_admit_creates_group_and_notifies(app: tuple[Container, RecordingNotifier]) -> None:
    container, log = app
    group = container.enrollment.admit(student(1))
    container.enrollment.admit(student(2))
    assert len(container.groups) == 1 and len(group) == 2 and str(group.code) == "ФЕП-31с"
    assert log.sent == [("Гнатишин Марта", "Вас зараховано до групи ФЕП-31с")] * 2
    with pytest.raises(DuplicateEntityError):
        container.enrollment.admit(student(1))


def test_enroll_grade_average_and_status(app: tuple[Container, RecordingNotifier]) -> None:
    container, log = app
    container.enrollment.admit(student(1))
    container.enrollment.enroll(1, 10)
    container.enrollment.enroll(1, 11)
    assert container.grading.status_of(1) is AcademicStatus.NO_GRADES
    container.grading.grade(1, 10, 95)
    container.grading.grade(1, 11, 91)
    assert container.grading.average_of(1) == pytest.approx(93)
    assert container.grading.status_of(1) is AcademicStatus.EXCELLENT
    container.grading.grade(1, 11, 40)
    assert log.sent[-1] == ("Гнатишин Марта", "Незадовільна оцінка з «Мова С»: 40.0 (FX)")
    container.courses.add(course(12, "Методи обчислень", 3))
    with pytest.raises(NotEnrolledError):
        container.grading.grade(1, 12, 70)
    with pytest.raises(EntityNotFoundError):
        container.grading.grade(1, 99, 70)


def test_policies_are_interchangeable_strategies() -> None:
    s = student()
    python, c_lang = course(10), course(11, "Мова С")
    for c in (python, c_lang):
        s.enroll(c)
    s.record(python, Grade(95))
    s.record(c_lang, Grade(55))
    assert ThresholdPolicy().status_of(s) is AcademicStatus.GOOD
    assert StrictPolicy().status_of(s) is AcademicStatus.AT_RISK
    assert ThresholdPolicy(excellent=70).status_of(s) is AcademicStatus.EXCELLENT


def test_reporting(app: tuple[Container, RecordingNotifier]) -> None:
    container, _ = app
    for student_id, points in ((1, 95), (2, 70), (3, 95)):
        container.enrollment.admit(
            Student(student_id, PersonName("Ім'я", f"Прізвище{student_id}"), GroupCode("ФЕП-31с"))
        )
        container.enrollment.enroll(student_id, 10)
        container.grading.grade(student_id, 10, points)
    ranking = container.reporting.ranking()
    assert [(s.id, avg) for s, avg in ranking] == [(1, 95.0), (3, 95.0), (2, 70.0)]
    report = container.reporting.student_report(2)
    assert report == {
        "id": 2,
        "name": "Прізвище2 Ім'я",
        "group": "ФЕП-31с",
        "courses": 1,
        "grades": 1,
        "average": 70.0,
        "credits": 4,
        "status": AcademicStatus.GOOD,
    }
    (group_report,) = container.reporting.group_reports()
    assert group_report == {
        "code": "ФЕП-31с",
        "students": 3,
        "average": pytest.approx(86.67, abs=0.01),
        "best": "Прізвище1 Ім'я",
    }
    assert [s.id for s in container.reporting.with_status(AcademicStatus.EXCELLENT)] == [1, 3]


def test_domain_errors_are_student_manager_errors() -> None:
    assert issubclass(DomainError, StudentManagerError)
    for error in (EntityNotFoundError, DuplicateEntityError, NotEnrolledError, WrongGroupError):
        assert issubclass(error, DomainError)
    assert issubclass(EntityNotFoundError, LookupError) and issubclass(WrongGroupError, ValueError)


# ----------------------------------------------------------------------------- inheritance vs composition


def test_both_importers_agree() -> None:
    lines = ["1,10,95", "", "7,11,55"]
    inherited = CsvGradeImporter().import_lines(lines)
    composed = GradeImporter(DelimitedParser(), RangeValidator(), ArrowFormatter()).import_lines(lines)
    assert inherited == composed == ["1:10 -> 95.0 (A)", "7:11 -> 55.0 (FX)"]
    with pytest.raises(InvalidGradeError):
        CsvGradeImporter().import_lines(["1,10,150"])


def test_composed_parts_are_testable_alone() -> None:
    assert DelimitedParser(";").parse("1; 10; 95") == {"student_id": 1, "course_id": 10, "points": 95.0}
    assert RangeValidator().validate({"student_id": 1, "course_id": 10, "points": 61}) == Grade(61)
    assert (
        TableFormatter().format({"student_id": 1, "course_id": 10, "points": 61}, Grade(61))
        == "|   1 |  10 |  61.0 | D  |"
    )
