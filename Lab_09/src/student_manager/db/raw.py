"""The same two tables through the standard DB-API (sqlite3), without the ORM.

Shows what SQLAlchemy hides: CREATE TABLE text, parameterised queries with ``?``, ``commit()``/``rollback()``
and an aggregate query with JOIN and GROUP BY.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS groups (
    id   INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS students (
    id            INTEGER PRIMARY KEY,
    first_name    TEXT NOT NULL,
    last_name     TEXT NOT NULL,
    average_grade REAL NOT NULL CHECK (average_grade BETWEEN 0 AND 100),
    group_id      INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_students_last_name ON students(last_name);
"""


def connect(path: Path | str) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row  # rows behave like dicts: row["last_name"]
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def create_tables(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA)


def insert_group(connection: sqlite3.Connection, code: str) -> int:
    cursor = connection.execute("INSERT INTO groups (code) VALUES (?)", (code,))
    return int(cursor.lastrowid or 0)


def insert_student(connection: sqlite3.Connection, first: str, last: str, group_id: int, grade: float) -> int:
    cursor = connection.execute(
        "INSERT INTO students (first_name, last_name, group_id, average_grade) VALUES (?, ?, ?, ?)",
        (first, last, group_id, grade),
    )
    return int(cursor.lastrowid or 0)


def find_by_last_name(connection: sqlite3.Connection, last_name: str) -> list[sqlite3.Row]:
    """Parameterised: the value travels separately from the SQL text, so it can never become SQL."""
    cursor = connection.execute(
        "SELECT s.id, s.first_name, s.last_name, g.code, s.average_grade "
        "FROM students s JOIN groups g ON g.id = s.group_id "
        "WHERE s.last_name = ? ORDER BY s.last_name, s.first_name",
        (last_name,),
    )
    return list(cursor.fetchall())


def find_by_last_name_unsafe(connection: sqlite3.Connection, last_name: str) -> list[sqlite3.Row]:
    """Anti-example for the report: string formatting lets the input rewrite the query."""
    query = f"SELECT id, last_name FROM students WHERE last_name = '{last_name}'"
    return list(connection.execute(query).fetchall())


def group_averages(connection: sqlite3.Connection) -> list[tuple[str, int, float | None]]:
    cursor = connection.execute(
        "SELECT g.code, COUNT(s.id) AS students, AVG(s.average_grade) AS average "
        "FROM groups g LEFT JOIN students s ON s.group_id = g.id "
        "GROUP BY g.id ORDER BY g.code"
    )
    return [(row["code"], row["students"], row["average"]) for row in cursor.fetchall()]


def transfer(connection: sqlite3.Connection, student_id: int, group_code: str) -> None:
    """Transactional move: the UPDATE is committed only if the target group exists; otherwise rolled back."""
    try:
        row = connection.execute("SELECT id FROM groups WHERE code = ?", (group_code,)).fetchone()
        if row is None:
            raise LookupError(f"групи {group_code} не існує")
        connection.execute("UPDATE students SET group_id = ? WHERE id = ?", (row["id"], student_id))
        connection.commit()
    except Exception:
        connection.rollback()
        raise
