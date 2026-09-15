"""Variant 1, items 1-7: creation, grade boundaries, invalid grade, average, empty registry, group filter, best."""

from __future__ import annotations

import math

import pytest
from tests.conftest import StudentFactory

from student_manager.exceptions import InvalidGradeError, InvalidGroupError, StudentManagerError
from student_manager.registry import StudentRegistry


def test_student_creation_normalises_names(make_student: StudentFactory) -> None:
    student = make_student(first_name="  Марта ", last_name=" Гнатишин")
    assert student.first_name == "Марта"
    assert student.full_name == "Гнатишин Марта"


@pytest.mark.parametrize("grade", [0, 0.0, 100, 100.0, 59.999], ids=["0", "0.0", "100", "100.0", "59.999"])
def test_boundary_grades_are_accepted(make_student: StudentFactory, grade: float) -> None:
    assert make_student(average_grade=grade).average_grade == grade


@pytest.mark.parametrize(("grade", "excellent"), [(89.99, False), (90.0, True), (100, True)])
def test_is_excellent_starts_at_ninety(make_student: StudentFactory, grade: float, excellent: bool) -> None:
    assert make_student(average_grade=grade).is_excellent is excellent


@pytest.mark.parametrize("grade", [-0.01, -1, 100.01, 101, math.nan], ids=["-0.01", "-1", "100.01", "101", "nan"])
def test_invalid_grade_raises_custom_exception(make_student: StudentFactory, grade: float) -> None:
    with pytest.raises(InvalidGradeError) as info:
        make_student(average_grade=grade)
    assert isinstance(info.value, StudentManagerError)
    assert isinstance(info.value, ValueError)


@pytest.mark.parametrize("group", ["", "феп-31с", "ФЕП-3", "ФЕП 31с", "ФЕП-31сс"])
def test_invalid_group_raises(make_student: StudentFactory, group: str) -> None:
    with pytest.raises(InvalidGroupError):
        make_student(group=group)


def test_empty_name_is_rejected(make_student: StudentFactory) -> None:
    with pytest.raises(ValueError, match="порожніми"):
        make_student(first_name="   ")


def test_average_is_compared_with_approx(make_student: StudentFactory) -> None:
    registry = StudentRegistry(make_student(average_grade=g) for g in (70.1, 70.2, 70.3))
    assert registry.group_average("ФЕП-31с") == pytest.approx(70.2)
    assert registry.group_average("ФЕП-31с") == pytest.approx(70.2, abs=1e-9)


def test_empty_registry(registry: StudentRegistry) -> None:
    empty = StudentRegistry()
    assert len(empty) == 0
    assert list(empty) == []
    assert empty.groups() == []
    assert len(registry) == 3  # the shared fixture is untouched
    with pytest.raises(StudentManagerError):
        empty.best()


@pytest.mark.parametrize(
    ("group", "expected"),
    [
        ("ФЕП-31с", ["Гнатишин", "Дзюба"]),
        ("феп-32", ["Кравець"]),
        ("ФЕП-41", []),
    ],
)
def test_filter_by_group(registry: StudentRegistry, group: str, expected: list[str]) -> None:
    assert [s.last_name for s in registry.by_group(group)] == expected


def test_best_student_overall_and_per_group(registry: StudentRegistry) -> None:
    assert registry.best().full_name == "Гнатишин Марта"
    assert registry.best("ФЕП-32").full_name == "Кравець Соломія"


def test_adding_a_student_changes_the_best(registry: StudentRegistry, make_student: StudentFactory) -> None:
    registry.add(make_student(last_name="Новак", average_grade=99.0))
    assert registry.best().last_name == "Новак"
    assert len(registry) == 4
