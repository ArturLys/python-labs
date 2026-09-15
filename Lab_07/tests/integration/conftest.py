"""Database fixtures for the integration tests: a fresh SQLite file per test, never the real data/students.db."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from student_manager.db import NewStudent, StudentService, create_schema, make_engine, make_session_factory

SEED = [
    NewStudent("Марта", "Гнатишин", "ФЕП-31с", 93.4, "marta@lnu.edu.ua"),
    NewStudent("Остап", "Дзюба", "ФЕП-31с", 78.9, "ostap@lnu.edu.ua"),
    NewStudent("Соломія", "Кравець", "ФЕП-32", 88.1, None),
]


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test.db"


@pytest.fixture
def engine(db_path: Path) -> Iterator[Engine]:
    engine = make_engine(f"sqlite:///{db_path.as_posix()}")
    create_schema(engine)
    yield engine
    engine.dispose()  # teardown: close the pool so tmp_path can be deleted on Windows


@pytest.fixture
def factory(engine: Engine) -> sessionmaker[Session]:
    return make_session_factory(engine)


@pytest.fixture
def service(factory: sessionmaker[Session]) -> StudentService:
    service = StudentService(factory)
    for row in SEED:
        service.add(row)
    return service
