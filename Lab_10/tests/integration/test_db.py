"""Persistence layer on a real (temporary) SQLite database: CRUD, filters, constraints, rollback, migrations."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from student_manager.db import (
    ConstraintViolationError,
    GroupRepository,
    NewStudent,
    RecordNotFoundError,
    StudentRecord,
    StudentRepository,
    StudentService,
    raw,
    session_scope,
)

ROOT = Path(__file__).resolve().parents[2]


# --- CRUD through the service ----------------------------------------------------------------------------------


def test_create_and_read(service: StudentService) -> None:
    new_id = service.add(NewStudent("Ярина", "Бойко", "ФЕП-33", 71.0))
    listing = service.listing()
    assert new_id == 4 and len(listing) == 4
    assert listing[-1].full_name == "Бойко Ярина" and listing[-1].group == "ФЕП-33"


def test_read_by_last_name_prefix_is_case_insensitive(service: StudentService) -> None:
    assert [s.full_name for s in service.find("гн")] == ["Гнатишин Марта"]
    assert service.find("Nobody") == []


def test_filter_by_group(service: StudentService) -> None:
    assert [s.last_name for s in service.in_group("ФЕП-31с")] == ["Гнатишин", "Дзюба"]
    assert service.in_group("ФЕП-99") == []


def test_update_grade(service: StudentService) -> None:
    assert service.set_grade(2, 81.5).average_grade == 81.5
    assert service.listing()[1].average_grade == 81.5


def test_update_transfer_creates_the_target_group(service: StudentService) -> None:
    moved = service.transfer(3, "ФЕП-41")
    assert moved.group == "ФЕП-41"
    assert [g.code for g in service.group_statistics()] == ["ФЕП-31с", "ФЕП-32", "ФЕП-41"]
    assert service.in_group("ФЕП-32") == []


def test_delete(service: StudentService) -> None:
    assert service.remove(1) is True
    assert service.remove(1) is False
    assert [s.last_name for s in service.listing()] == ["Дзюба", "Кравець"]


def test_best_and_group_average_use_aggregates(service: StudentService) -> None:
    best = service.best()
    assert best is not None and best.full_name == "Гнатишин Марта"
    assert service.group_average("ФЕП-31с") == pytest.approx(86.15)
    assert service.group_average("ФЕП-99") is None
    stats = {g.code: (g.students, g.average) for g in service.group_statistics()}
    assert stats["ФЕП-32"] == (1, pytest.approx(88.1))


def test_pagination_and_sorting(service: StudentService, factory: sessionmaker[Session]) -> None:
    with session_scope(factory) as session:
        page = StudentRepository(session).page(1, 2, descending=True)
        assert [s.last_name for s in page] == ["Гнатишин", "Кравець"]
        assert [s.last_name for s in StudentRepository(session).page(2, 2, descending=True)] == ["Дзюба"]


# --- constraints and transactions --------------------------------------------------------------------------------


def test_check_constraint_rejects_grade_above_100(service: StudentService) -> None:
    with pytest.raises(ConstraintViolationError, match="ck_students_grade_range|CHECK"):
        service.set_grade(1, 150)
    assert service.listing()[0].average_grade == 93.4  # the UPDATE was rolled back


def test_unique_email_is_enforced(service: StudentService) -> None:
    with pytest.raises(ConstraintViolationError, match="UNIQUE"):
        service.add(NewStudent("Ігор", "Новак", "ФЕП-31с", 70, "marta@lnu.edu.ua"))
    assert len(service.listing()) == 3


def test_foreign_key_is_enforced(factory: sessionmaker[Session]) -> None:
    with pytest.raises(IntegrityError, match="FOREIGN KEY"), session_scope(factory) as session:
        StudentRepository(session).add(StudentRecord(first_name="Х", last_name="Y", average_grade=50, group_id=999))


def test_import_many_is_atomic(service: StudentService) -> None:
    rows = [
        NewStudent("Ярина", "Бойко", "ФЕП-33", 90),
        NewStudent("Роман", "Скиба", "ФЕП-33", 85),
        NewStudent("Олег", "Шевчук", "ФЕП-33", -5),
    ]
    with pytest.raises(ConstraintViolationError, match="рядок 3"):
        service.import_many(rows)
    assert len(service.listing()) == 3
    assert service.in_group("ФЕП-33") == []
    assert all(g.code != "ФЕП-33" for g in service.group_statistics())  # the new group was rolled back too


def test_rollback_on_python_error_inside_the_scope(factory: sessionmaker[Session], service: StudentService) -> None:
    with pytest.raises(RuntimeError), session_scope(factory) as session:
        StudentRepository(session).update_grade(1, 10.0)
        raise RuntimeError("щось пішло не так після UPDATE")
    assert service.listing()[0].average_grade == 93.4


def test_missing_record_raises(service: StudentService) -> None:
    with pytest.raises(RecordNotFoundError, match="students.*id=99"):
        service.transfer(99, "ФЕП-31с")


def test_deleting_a_group_cascades_to_students(service: StudentService) -> None:
    assert service.remove_group("ФЕП-31с") == 2
    assert [s.last_name for s in service.listing()] == ["Кравець"]
    assert service.remove_group("ФЕП-31с") == 0


def test_repository_count_and_get_or_create(factory: sessionmaker[Session], service: StudentService) -> None:
    with session_scope(factory) as session:
        groups = GroupRepository(session)
        assert groups.count() == 2
        assert groups.get_or_create("ФЕП-31с").id == groups.get_or_create(" ФЕП-31с ").id
        assert groups.count() == 2


# --- DB-API and migrations ---------------------------------------------------------------------------------------


def test_dbapi_parameterized_query_is_injection_safe(tmp_path: Path) -> None:
    connection = raw.connect(tmp_path / "raw.db")
    raw.create_tables(connection)
    group_id = raw.insert_group(connection, "ФЕП-31с")
    raw.insert_student(connection, "Марта", "Гнатишин", group_id, 93.4)
    connection.commit()
    payload = "' OR '1'='1"
    assert raw.find_by_last_name(connection, payload) == []
    assert len(raw.find_by_last_name_unsafe(connection, payload)) == 1
    assert raw.group_averages(connection) == [("ФЕП-31с", 1, pytest.approx(93.4))]
    with pytest.raises(LookupError):
        raw.transfer(connection, 1, "ФЕП-99")
    connection.close()


def columns(path: Path, table: str) -> list[str]:
    with sqlite3.connect(path) as connection:
        return [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]


def test_migrations_upgrade_and_downgrade(tmp_path: Path) -> None:
    db = tmp_path / "migrated.db"
    config = Config()
    config.set_main_option("script_location", str(ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db.as_posix()}")

    command.upgrade(config, "0001")
    assert columns(db, "students") == ["id", "first_name", "last_name", "average_grade", "group_id"]
    command.upgrade(config, "head")
    assert columns(db, "students")[-1] == "email"
    command.downgrade(config, "-1")
    assert "email" not in columns(db, "students")
    command.upgrade(config, "head")
    assert "email" in columns(db, "students")
