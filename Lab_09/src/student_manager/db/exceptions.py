"""Persistence errors, wrapped so that callers never import SQLAlchemy to catch them."""

from __future__ import annotations

from student_manager.exceptions import StudentManagerError


class PersistenceError(StudentManagerError):
    """Base of everything the db package raises."""


class RecordNotFoundError(PersistenceError, LookupError):
    def __init__(self, table: str, record_id: int | str) -> None:
        key = f"id={record_id}" if isinstance(record_id, int) else repr(record_id)
        super().__init__(f"у таблиці {table} немає запису з {key}")
        self.table = table
        self.record_id = record_id


class ConstraintViolationError(PersistenceError, ValueError):
    """The database refused the change (CHECK, UNIQUE or FOREIGN KEY); the transaction was rolled back."""
