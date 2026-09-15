"""Fixtures shared by every test module. pytest finds this file by its path; nothing imports it.

Scopes: ``sample_students`` is built once per session (cheap to share, never mutated), ``registry`` is rebuilt
for every test (tests add to it), ``make_student`` is a factory fixture, ``policy`` is parametrised, and
``quiet_logging`` is autouse: it runs for every test without being named.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator, Sequence
from datetime import UTC, datetime
from itertools import count
from pathlib import Path
from unittest.mock import create_autospec

import pytest

from student_manager import clock
from student_manager.models import Student
from student_manager.notify import Mailer
from student_manager.registry import StudentRegistry
from student_manager.storage.dto import STUDENT_FIELDS
from student_manager.storage.services import STRICT, TOLERANT, ImportPolicy

FROZEN_TIME = datetime(2026, 9, 8, 10, 0, tzinfo=UTC)

StudentFactory = Callable[..., Student]
CsvWriter = Callable[[Sequence[Sequence[object]]], Path]


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Everything under tests/integration/ gets the marker automatically, so -m integration never misses a file."""
    for item in items:
        if "integration" in item.path.parts:
            item.add_marker(pytest.mark.integration)


@pytest.fixture(scope="session")
def sample_students() -> tuple[Student, ...]:
    return (
        Student("Марта", "Гнатишин", "ФЕП-31с", 93.4),
        Student("Остап", "Дзюба", "ФЕП-31с", 78.9),
        Student("Соломія", "Кравець", "ФЕП-32", 88.1),
    )


@pytest.fixture
def registry(sample_students: tuple[Student, ...]) -> StudentRegistry:
    return StudentRegistry(sample_students)


@pytest.fixture
def make_student() -> StudentFactory:
    """Factory fixture: each call gives a valid student; keyword arguments override single fields."""
    numbers = count(1)

    def factory(**overrides: object) -> Student:
        fields: dict[str, object] = {
            "first_name": "Тест",
            "last_name": f"Студент{next(numbers)}",
            "group": "ФЕП-31с",
            "average_grade": 75.0,
        }
        fields.update(overrides)
        return Student(**fields)  # type: ignore[arg-type]

    return factory


@pytest.fixture
def write_csv(tmp_path: Path) -> CsvWriter:
    """Write a variant-1 students CSV into the test's private temporary directory."""

    def writer(rows: Sequence[Sequence[object]], name: str = "students.csv") -> Path:
        lines = [",".join(STUDENT_FIELDS)] + [",".join(str(v) for v in row) for row in rows]
        path = tmp_path / name
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    return writer


@pytest.fixture
def frozen_clock(monkeypatch: pytest.MonkeyPatch) -> datetime:
    """Deterministic time: production code reads ``clock.now``; monkeypatch restores it after the test."""
    monkeypatch.setattr(clock, "now", lambda: FROZEN_TIME)
    return FROZEN_TIME


@pytest.fixture
def mailer() -> Mailer:
    """An autospec double of the Mailer protocol: wrong argument names or counts raise TypeError."""
    double: Mailer = create_autospec(Mailer, instance=True)
    return double


@pytest.fixture(params=[STRICT, TOLERANT], ids=["strict", "tolerant"])
def policy(request: pytest.FixtureRequest) -> ImportPolicy:
    """Parametrised fixture: every test that asks for ``policy`` runs twice."""
    result: ImportPolicy = request.param
    return result


@pytest.fixture(autouse=True)
def isolation_guard() -> Iterator[None]:
    """Autouse: runs around every test without being requested. Fails loudly if a test leaked global state
    (a patched clock or a stray handler on the package logger), so the leak is blamed on the right test."""
    log = logging.getLogger("student_manager")
    handlers_before = list(log.handlers)
    yield
    assert clock.now is clock._system_now, "тест залишив підмінений clock.now"
    assert log.handlers == handlers_before, "тест залишив обробник логера student_manager"
