"""Domain entities: objects with identity and a life cycle.

Entities are hand-written classes, not dataclasses, on purpose: a dataclass compares all fields,
while two Student objects are the same student exactly when their ids match. Every class keeps its
state behind __slots__ and exposes it through properties and methods, never as bare attributes
that anyone can overwrite with a nonsense value.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from statistics import mean
from typing import TYPE_CHECKING, TypeAlias

from student_manager.domain.errors import (
    AlreadyEnrolledError,
    DuplicateEntityError,
    NotEnrolledError,
    WrongGroupError,
)
from student_manager.domain.value_objects import (
    PASSING_THRESHOLD,
    ZERO_CREDITS,
    Credits,
    Grade,
    GroupCode,
    PersonName,
)

if TYPE_CHECKING:  # avoid an import cycle: dto imports models, models needs dto only for hints
    from student_manager.domain.dto import StudentPayload

EntityId: TypeAlias = int


class Entity:
    """Base for anything with identity. Equality and hash come from the id, not from the fields."""

    __slots__ = ("_id",)

    def __init__(self, entity_id: EntityId) -> None:
        if entity_id <= 0:
            raise ValueError(f"id має бути додатним, отримано {entity_id!r}")
        self._id = entity_id

    @property
    def id(self) -> EntityId:
        return self._id

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity):
            return NotImplemented
        return type(self) is type(other) and self._id == other._id

    def __hash__(self) -> int:
        return hash((type(self).__name__, self._id))

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self._id})"


class Person(Entity):
    """Someone with a name. Student and Teacher *are* persons, so inheritance is the honest choice."""

    __slots__ = ("name",)

    def __init__(self, entity_id: EntityId, name: PersonName) -> None:
        super().__init__(entity_id)
        self.name = name

    def __str__(self) -> str:
        return self.name.full

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self.id}, name={self.name.full!r})"


class Teacher(Person):
    """A lecturer; courses refer to him, he does not own them."""

    __slots__ = ("department",)

    def __init__(self, entity_id: EntityId, name: PersonName, department: str) -> None:
        super().__init__(entity_id, name)
        self.department = department.strip()

    def __str__(self) -> str:
        return f"{super().__str__()} ({self.department})"


class Course(Entity):
    """A discipline with credits and a teacher. Course *has* a teacher — composition, not inheritance."""

    __slots__ = ("title", "credits", "teacher")

    def __init__(self, entity_id: EntityId, title: str, credits: Credits, teacher: Teacher) -> None:
        super().__init__(entity_id)
        self.title = title.strip()
        self.credits = credits
        self.teacher = teacher

    def to_dict(self) -> Mapping[str, object]:
        return {"id": self.id, "title": self.title, "credits": self.credits.ects, "teacher": self.teacher.name.full}

    def __str__(self) -> str:
        return f"{self.title} ({self.credits}, {self.teacher.name.initials})"


class GradeBook:
    """A student's record book: the courses he is enrolled in and the grades in each of them.

    A custom collection: len() counts grades, iteration yields (course, grade) pairs,
    `course in book` asks about enrollment, book[course] gives that course's grades.
    """

    __slots__ = ("_entries",)

    def __init__(self) -> None:
        self._entries: dict[Course, list[Grade]] = {}

    def enroll(self, course: Course) -> None:
        if course in self:
            raise AlreadyEnrolledError(f"курс «{course.title}» уже в заліковій книжці")
        self._entries[course] = []

    def add(self, course: Course, grade: Grade) -> None:
        if course not in self:
            raise NotEnrolledError(f"немає запису на курс «{course.title}», оцінку ставити нікуди")
        self._entries[course].append(grade)

    @property
    def courses(self) -> tuple[Course, ...]:
        return tuple(self._entries)

    @property
    def grades(self) -> tuple[Grade, ...]:
        return tuple(grade for grades in self._entries.values() for grade in grades)

    @property
    def average(self) -> float | None:
        grades = self.grades
        return mean(g.points for g in grades) if grades else None

    @property
    def earned_credits(self) -> Credits:
        """Credits of every course whose average is a pass; sum() works thanks to Credits.__add__."""
        passed = (
            course.credits
            for course, grades in self._entries.items()
            if grades and mean(g.points for g in grades) >= PASSING_THRESHOLD
        )
        return sum(passed, start=ZERO_CREDITS)

    def average_for(self, course: Course) -> float | None:
        grades = self[course]
        return mean(g.points for g in grades) if grades else None

    def __len__(self) -> int:
        return len(self.grades)

    def __iter__(self) -> Iterator[tuple[Course, Grade]]:
        for course, grades in self._entries.items():
            for grade in grades:
                yield course, grade

    def __contains__(self, item: object) -> bool:
        return item in self._entries

    def __getitem__(self, course: Course) -> tuple[Grade, ...]:
        if course not in self:
            raise NotEnrolledError(f"немає запису на курс «{course.title}»")
        return tuple(self._entries[course])

    def __repr__(self) -> str:
        return f"GradeBook(courses={len(self._entries)}, grades={len(self)})"


class Student(Person):
    """A student of one group with his own GradeBook (composition: Student *has* a GradeBook)."""

    __slots__ = ("_group", "_book", "email")

    def __init__(
        self,
        entity_id: EntityId,
        name: PersonName,
        group: GroupCode,
        email: str | None = None,
        book: GradeBook | None = None,
    ) -> None:
        super().__init__(entity_id, name)
        self._group = group
        self._book = book if book is not None else GradeBook()
        self.email = email

    @classmethod
    def from_payload(cls, data: StudentPayload) -> Student:
        """Class factory: build an entity from an external dict shape (TypedDict)."""
        return cls(
            data["id"],
            PersonName(data["first_name"], data["last_name"]),
            GroupCode(data["group"]),
            data.get("email"),
        )

    def to_dict(self) -> StudentPayload:
        """The inverse of from_payload; together they make Student structurally Serializable."""
        payload: StudentPayload = {
            "id": self.id,
            "first_name": self.name.first,
            "last_name": self.name.last,
            "group": str(self._group),
        }
        if self.email is not None:
            payload["email"] = self.email
        return payload

    @property
    def group(self) -> GroupCode:
        return self._group

    @property
    def book(self) -> GradeBook:
        return self._book

    @property
    def average(self) -> float | None:
        return self._book.average

    @property
    def contact(self) -> str:
        return self.email or self.name.full

    def enroll(self, course: Course) -> None:
        self._book.enroll(course)

    def record(self, course: Course, grade: Grade) -> None:
        self._book.add(course, grade)

    def __str__(self) -> str:
        return f"{super().__str__()}, {self._group}"


class Group(Entity):
    """Academic group: a code and the roster. Iterable, sized, supports `student in group`."""

    __slots__ = ("code", "_students")

    def __init__(self, entity_id: EntityId, code: GroupCode) -> None:
        super().__init__(entity_id)
        self.code = code
        self._students: dict[EntityId, Student] = {}

    def add(self, student: Student) -> None:
        if student.group != self.code:
            raise WrongGroupError(f"{student.name} належить до групи {student.group}, а не {self.code}")
        if student in self:
            raise DuplicateEntityError(f"{student.name} уже в групі {self.code}")
        self._students[student.id] = student

    @property
    def average(self) -> float | None:
        averages = [s.average for s in self if s.average is not None]
        return mean(averages) if averages else None

    def __len__(self) -> int:
        return len(self._students)

    def __iter__(self) -> Iterator[Student]:
        return iter(self._students.values())

    def __contains__(self, item: object) -> bool:
        return isinstance(item, Student) and item.id in self._students

    def __str__(self) -> str:
        return f"{self.code} ({len(self)} студ.)"
