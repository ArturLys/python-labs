"""Demo of the domain model: `python -m student_manager.domain`.

Deterministic: the same nine students and 36 grades as in the analytics package of lab 2.
"""

from __future__ import annotations

import io
import sys
from collections.abc import Callable
from dataclasses import FrozenInstanceError

from student_manager.domain import (
    AcademicStatus,
    ConsoleNotifier,
    Container,
    Course,
    Credits,
    DomainError,
    Grade,
    GroupCode,
    InMemoryRepository,
    PersonName,
    RecordingNotifier,
    ReportingService,
    Serializable,
    StrictPolicy,
    Student,
    StudentPayload,
    Teacher,
)
from student_manager.domain.importing import (
    ArrowFormatter,
    CsvGradeImporter,
    DelimitedParser,
    GradeImporter,
    RangeValidator,
    TableFormatter,
)
from student_manager.exceptions import StudentManagerError

TEACHERS = [
    (1, "Олена", "Ткаченко", "кафедра програмування"),
    (2, "Ігор", "Романюк", "кафедра системного програмування"),
    (3, "Наталія", "Шевчук", "кафедра обчислювальної математики"),
    (4, "Василь", "Бойко", "кафедра інформаційних систем"),
]
COURSES = [  # id, title, credits, teacher id
    (10, "Професійний Python", 4, 1),
    (11, "Мова С", 4, 2),
    (12, "Методи обчислень", 3, 3),
    (13, "Інженерія даних", 3, 4),
]
STUDENTS: list[StudentPayload] = [
    {"id": 1, "first_name": "Марта", "last_name": "Гнатишин", "group": "ФЕП-31с", "email": "marta.h@lnu.edu.ua"},
    {"id": 2, "first_name": "Остап", "last_name": "Дзюба", "group": "ФЕП-31с"},
    {"id": 3, "first_name": "Тарас", "last_name": "Вовк", "group": "ФЕП-31с"},
    {"id": 4, "first_name": "Соломія", "last_name": "Кравець", "group": "ФЕП-32", "email": "solomiia.k@lnu.edu.ua"},
    {"id": 5, "first_name": "Ірина", "last_name": "Пасічник", "group": "ФЕП-32"},
    {"id": 6, "first_name": "Андрій", "last_name": "Мельник", "group": "ФЕП-32"},
    {"id": 7, "first_name": "Юрій", "last_name": "Скиба", "group": "ФЕП-33"},
    {"id": 8, "first_name": "Назар", "last_name": "Ковальчук", "group": "ФЕП-33"},
    {"id": 9, "first_name": "Богдан", "last_name": "Тимків", "group": "ФЕП-33", "email": "bohdan.t@lnu.edu.ua"},
]
# Grades in COURSES order — the same numbers as analytics.data._RAW in lab 2.
GRADES: dict[int, tuple[float, ...]] = {
    1: (95, 91, 94, 93),
    2: (81, 74, 79, 82),
    3: (88, 83, 85, 84),
    4: (90, 86, 87, 89),
    5: (98, 96, 95, 97),
    6: (77, 70, 72, 75),
    7: (73, 68, 70, 74),
    8: (85, 80, 82, 83),
    9: (91, 89, 90, 92),
}


def show(title: str) -> None:
    print(f"\n{title}\n{'-' * len(title)}")


def attempt(label: str, action: Callable[[], object]) -> None:
    """Run a zero-argument callable and print the domain error it raises."""
    try:
        action()
        print(f"  {label}: без помилки")
    except StudentManagerError as error:
        print(f"  {label}: {type(error).__name__}: {error}")


def seed(app: Container) -> None:
    """Fill the repositories through the services, never behind their back."""
    for teacher_id, first, last, department in TEACHERS:  # teachers live inside their courses
        teacher = Teacher(teacher_id, PersonName(first, last), department)
        for course_id, title, credits, owner in COURSES:
            if owner == teacher_id:
                app.courses.add(Course(course_id, title, Credits(credits), teacher))
    for payload in STUDENTS:
        student = Student.from_payload(payload)
        app.enrollment.admit(student)
        for (course_id, _, _, _), points in zip(COURSES, GRADES[student.id], strict=True):
            app.enrollment.enroll(student.id, course_id)
            app.grading.grade(student.id, course_id, points)


def print_ranking(reporting: ReportingService) -> None:
    for place, (student, average) in enumerate(reporting.ranking(), 1):
        print(f"  {place:2}. {student.name.full:<18} {str(student.group):<8} {average:6.2f}")


def main() -> None:
    if isinstance(sys.stdout, io.TextIOWrapper) and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    show("VALUE OBJECTS: frozen dataclass, properties, total_ordering, __add__")
    best, worst = Grade(95), Grade(58)
    print(f"  Grade(95) -> {best}; Grade(58) -> {worst}; is_passing: {best.is_passing}, {worst.is_passing}")
    print(f"  Grade(95) > Grade(58): {best > worst}; Grade(90) == Grade(90.0): {Grade(90) == Grade(90.0)}")
    print("  sorted:", [str(g) for g in sorted((Grade(81), Grade(95), Grade(60.5)))])
    print("  max:   ", max(Grade(81), Grade(95), Grade(60.5)))
    try:
        best.points = 100  # type: ignore[misc]  # the checker forbids it too
    except FrozenInstanceError as error:
        print(f"  best.points = 100 -> FrozenInstanceError: {error}")
    attempt("Grade(101)", lambda: Grade(101))
    total = sum((Credits(4), Credits(4), Credits(3)), start=Credits(0))
    print(f"  Credits(4) + Credits(4) + Credits(3) = {total}")
    name = PersonName("  Марта ", "Гнатишин")
    print(f"  PersonName -> {name!r}; full={name.full!r}; initials={name.initials!r}")
    code = GroupCode("ФЕП-31с")
    print(f"  GroupCode -> faculty={code.faculty}, stream={code.stream}")
    attempt('GroupCode("група 31")', lambda: GroupCode("група 31"))

    show("ENTITIES: identity, inheritance, super()")
    marta = Student(1, PersonName("Марта", "Гнатишин"), GroupCode("ФЕП-31с"))
    same_id = Student(1, PersonName("Марта", "Гнатишин-Ковальчук"), GroupCode("ФЕП-31с"))
    teacher = Teacher(1, PersonName("Олена", "Ткаченко"), "кафедра програмування")
    print(f"  {marta!r} == {same_id!r}: {marta == same_id}  (одна id -> одна сутність)")
    print(f"  Student(id=1) == Teacher(id=1): {marta == teacher}  (різні типи)")
    print(f"  len({{marta, same_id}}) = {len({marta, same_id})}")
    print(f"  str(student): {marta};  str(teacher): {teacher}")
    print("  MRO Student:", " -> ".join(cls.__name__ for cls in Student.__mro__))

    show("СЕРВІСИ ЧЕРЕЗ DI-КОНТЕЙНЕР: admit, enroll, grade")
    log = RecordingNotifier()
    app = Container.build(notifier=log)
    seed(app)
    print(f"  студентів: {len(app.students)}, курсів: {len(app.courses)}, груп: {len(app.groups)}")
    print(f"  повідомлень у RecordingNotifier: {len(log)}; перші два:")
    for recipient, message in log.sent[:2]:
        print(f"    {recipient}: {message}")

    show("GRADEBOOK — власна колекція: __len__, __contains__, __getitem__, __iter__")
    student = app.students.require(1)
    python_course = app.courses.require(10)
    book = student.book
    print(f"  {book!r}; len(book) = {len(book)}")
    print(
        f"  python_course in book: {python_course in book}; book[python_course] = {[str(g) for g in book[python_course]]}"
    )
    for course, grade in book:
        print(f"    {course.title:<20} {grade}")
    print(f"  average = {book.average:.2f}; earned_credits = {book.earned_credits}")
    attempt("record без enroll", lambda: student.record(Course(99, "Фізика", Credits(3), teacher), Grade(80)))
    attempt("enroll вдруге", lambda: student.enroll(python_course))

    show("GROUP — сутність-колекція")
    for group in sorted(app.groups.all(), key=lambda g: str(g.code)):
        members = ", ".join(s.name.initials for s in group)
        print(f"  {group}: {members}; середній {group.average:.2f}")
    fep31 = app.groups.require(1)
    print(f"  student in fep31: {student in fep31}")
    attempt("add ФЕП-32 у ФЕП-31с", lambda: fep31.add(app.students.require(4)))

    show("REPORTING: рейтинг, статуси (ThresholdPolicy), звіти-TypedDict")
    print_ranking(app.reporting)
    print("  відмінники:", [s.name.full for s in app.reporting.with_status(AcademicStatus.EXCELLENT)])
    print("  student_report(9):", dict(app.reporting.student_report(9)))
    for report in app.reporting.group_reports():
        print(
            f"  {report['code']:<8} студентів {report['students']}  середній {report['average']:.2f}  кращий: {report['best']}"
        )

    show("STRATEGY: ThresholdPolicy проти StrictPolicy після одного «незадовільно»")
    app.grading.grade(7, 11, 55)  # Скиба Юрій, Мова С, друга оцінка
    strict = ReportingService(app.students, app.groups, StrictPolicy())
    for student_id in (7, 8):
        s = app.students.require(student_id)
        print(
            f"  {s.name.full:<16} avg {s.average:5.2f}  threshold: {app.grading.status_of(student_id):<18} "
            f"strict: {strict.student_report(student_id)['status']}"
        )
    print(f"  останнє повідомлення: {log.sent[-1]}")

    show("TYPEDDICT <-> ENTITY, runtime_checkable Protocol")
    payload: StudentPayload = {"id": 10, "first_name": "Оксана", "last_name": "Ференц", "group": "ФЕП-31с"}
    newcomer = Student.from_payload(payload)
    print(f"  from_payload -> {newcomer}; to_dict -> {newcomer.to_dict()}")
    print(f"  to_dict з email -> {app.students.require(1).to_dict()}")
    for thing in (newcomer, Grade(77), python_course, teacher, "рядок"):
        print(f"  isinstance({type(thing).__name__}, Serializable) = {isinstance(thing, Serializable)}")
    print("  export:", ReportingService.export([Grade(77), teacher, python_course]))

    show("DEPENDENCY INJECTION: той самий сервіс, інший Notifier і інша policy")
    console_app = Container.build(notifier=ConsoleNotifier(), policy=StrictPolicy())
    console_app.courses.add(Course(11, "Мова С", Credits(4), teacher))
    console_app.enrollment.admit(newcomer)
    console_app.enrollment.enroll(10, 11)
    console_app.grading.grade(10, 11, 42)
    print(f"  статус: {console_app.grading.status_of(10)}")

    show("GENERIC REPOSITORY: InMemoryRepository[Teacher]")
    teachers = InMemoryRepository[Teacher](
        (Teacher(i, PersonName(f, l), d) for i, f, l, d in TEACHERS), kind="викладач"
    )
    print(f"  {teachers!r}; 2 in teachers: {2 in teachers}; 9 in teachers: {9 in teachers}")
    print("  find(кафедра програмування):", [str(t) for t in teachers.find(lambda t: "програмування" in t.department)])
    print(f"  remove(4): {teachers.remove(4)}; remove(4) вдруге: {teachers.remove(4)}; len: {len(teachers)}")
    attempt("require(4)", lambda: teachers.require(4))
    attempt("add дубліката id=1", lambda: teachers.add(Teacher(1, PersonName("Хтось", "Інший"), "-")))

    show("ІЄРАРХІЯ ВИНЯТКІВ: усе ловиться одним DomainError / StudentManagerError")
    bases: tuple[type[StudentManagerError], ...] = (DomainError, StudentManagerError)
    for base in bases:
        try:
            app.enrollment.enroll(99, 10)
        except base as caught:
            print(f"  except {base.__name__}: {type(caught).__name__} — {caught}")

    show("ЕКСПЕРИМЕНТ: inheritance (CsvGradeImporter) проти composition (GradeImporter)")
    lines = ["1,10,95", "7,11,55", "", "9,13,92"]
    inherited = CsvGradeImporter().import_lines(lines)
    composed = GradeImporter(DelimitedParser(), RangeValidator(), ArrowFormatter()).import_lines(lines)
    print(f"  однаковий результат: {inherited == composed}")
    for row in inherited:
        print(f"    {row}")
    print("  інший формат і роздільник без нового підкласу:")
    table = GradeImporter(DelimitedParser(";"), RangeValidator(), TableFormatter())
    for row in table.import_lines(line.replace(",", ";") for line in lines):
        print(f"    {row}")


if __name__ == "__main__":
    main()
