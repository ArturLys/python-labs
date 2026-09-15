"""Demo of lab 7: ``python -m student_manager.db`` — DB-API first, then ORM + repositories + migrations."""

from __future__ import annotations

import logging
import sqlite3
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from student_manager.db import (
    ConstraintViolationError, NewStudent, RecordNotFoundError, StudentService, make_engine,
    make_session_factory,
)
from student_manager.db import raw

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data"

SEED = [
    NewStudent("Марта", "Гнатишин", "ФЕП-31с", 93.4, "marta@lnu.edu.ua"),
    NewStudent("Остап", "Дзюба", "ФЕП-31с", 78.9, "ostap@lnu.edu.ua"),
    NewStudent("Соломія", "Кравець", "ФЕП-32", 88.1, "solomiia@lnu.edu.ua"),
    NewStudent("Тарас", "Гаврилюк", "ФЕП-32", 64.0, None),
]


def show(title: str) -> None:
    print(f"\n{title}\n{'-' * len(title)}")


def attempt(label: str, action: object) -> None:
    try:
        action()  # type: ignore[operator]
    except Exception as error:  # noqa: BLE001 - the demo prints every failure on purpose
        print(f"  {label}: {type(error).__name__}: {str(error).splitlines()[0][:110]}")


def print_students(service: StudentService) -> None:
    for number, student in enumerate(service.listing(), start=1):
        print(f"  {number:>2} {student.full_name:<20} {student.group:<8} {student.average_grade:>6.2f}")


def columns(url_path: Path, table: str) -> list[str]:
    with sqlite3.connect(url_path) as connection:
        return [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]


def alembic_config(db_path: Path) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path.as_posix()}")
    return config


def dbapi_demo(path: Path) -> None:
    path.unlink(missing_ok=True)
    connection = raw.connect(path)
    raw.create_tables(connection)
    show("DB-API (sqlite3): CREATE TABLE, INSERT ?, SELECT ?, JOIN + GROUP BY")
    groups = {code: raw.insert_group(connection, code) for code in ("ФЕП-31с", "ФЕП-32")}
    for s in SEED:
        raw.insert_student(connection, s.first_name, s.last_name, groups[s.group], s.average_grade)
    connection.commit()
    print("  rows:", [dict(r) for r in raw.find_by_last_name(connection, "Гнатишин")])
    print("  group averages:", raw.group_averages(connection))

    show("Parameterized query проти f-string: payload = \"' OR '1'='1\"")
    payload = "' OR '1'='1"
    print("  safe   ->", len(raw.find_by_last_name(connection, payload)), "рядків")
    print("  unsafe ->", len(raw.find_by_last_name_unsafe(connection, payload)), "рядків (весь список витік)")

    show("Транзакція з rollback (DB-API)")
    before = connection.execute("SELECT group_id FROM students WHERE id = 1").fetchone()[0]
    attempt("transfer(1, 'ФЕП-99')", lambda: raw.transfer(connection, 1, "ФЕП-99"))
    after = connection.execute("SELECT group_id FROM students WHERE id = 1").fetchone()[0]
    print(f"  group_id студента 1 до/після: {before} / {after} (UPDATE не відбувся)")
    raw.transfer(connection, 1, "ФЕП-32")
    print("  transfer(1, 'ФЕП-32') -> group_id =", connection.execute("SELECT group_id FROM students WHERE id = 1").fetchone()[0])
    connection.close()


def orm_demo(db_path: Path) -> None:
    db_path.unlink(missing_ok=True)
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="  %(levelname)s [%(name)s] %(message)s")
    logging.getLogger("student_manager").setLevel(logging.WARNING)
    config = alembic_config(db_path)

    show("Alembic: upgrade 0001 -> head")
    command.upgrade(config, "0001")
    print("  students після 0001:", columns(db_path, "students"))
    command.upgrade(config, "head")
    print("  students після head:", columns(db_path, "students"))
    logging.getLogger("alembic").setLevel(logging.WARNING)

    engine = make_engine(f"sqlite:///{db_path.as_posix()}")
    print("  таблиці:", inspect(engine).get_table_names())
    service = StudentService(make_session_factory(engine))

    show("Create: service.add / import_many")
    for s in SEED:
        service.add(s)
    print_students(service)

    show("Read: пошук за прізвищем, фільтр за групою, найкращий, середній бал групи")
    print("  find('Гн')      ->", [s.full_name for s in service.find("Гн")])
    print("  in_group(ФЕП-32)->", [s.full_name for s in service.in_group("ФЕП-32")])
    best = service.best()
    print(f"  best()          -> {best.full_name} {best.average_grade}" if best else "  best() -> None")
    print("  group_average(ФЕП-31с) ->", round(service.group_average("ФЕП-31с") or 0, 2))
    print("  statistics      ->", [(g.code, g.students, round(g.average or 0, 2)) for g in service.group_statistics()])

    show("Update: зміна балу, переведення до іншої групи")
    print("  set_grade(2, 81.5) ->", service.set_grade(2, 81.5))
    print("  transfer(4, 'ФЕП-41') ->", service.transfer(4, "ФЕП-41"))
    print("  statistics ->", [(g.code, g.students) for g in service.group_statistics()])

    show("Обмеження та rollback (ORM)")
    attempt("set_grade(1, 150)", lambda: service.set_grade(1, 150))
    attempt("add(duplicate email)", lambda: service.add(NewStudent("Ігор", "Новак", "ФЕП-31с", 70, "marta@lnu.edu.ua")))
    attempt("transfer(99, ...)", lambda: service.transfer(99, "ФЕП-31с"))
    count_before = len(service.listing())
    attempt("import_many([ok, ok, grade=-5])", lambda: service.import_many([
        NewStudent("Ярина", "Бойко", "ФЕП-33", 90), NewStudent("Роман", "Скиба", "ФЕП-33", 85),
        NewStudent("Олег", "Шевчук", "ФЕП-33", -5),
    ]))
    print(f"  студентів до/після імпорту: {count_before} / {len(service.listing())} — жоден рядок не зберігся")
    print("  оцінка студента 1 після невдалого set_grade:", service.listing()[0].average_grade)

    show("Delete: студент, каскадне видалення групи")
    print("  remove(3) ->", service.remove(3), "; remove(3) вдруге ->", service.remove(3))
    print("  remove_group('ФЕП-41') -> видалено студентів:", service.remove_group("ФЕП-41"))
    print_students(service)

    show("Alembic: downgrade -1 і назад")
    command.downgrade(config, "-1")
    print("  students після downgrade:", columns(db_path, "students"))
    command.upgrade(config, "head")
    print("  students після upgrade:  ", columns(db_path, "students"))
    engine.dispose()


def main() -> None:
    DATA.mkdir(exist_ok=True)
    dbapi_demo(DATA / "raw_students.db")
    orm_demo(DATA / "students.db")


if __name__ == "__main__":
    main()
