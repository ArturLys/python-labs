"""Persistence errors, wrapped so that callers never import SQLAlchemy to catch them."""

from __future__ import annotations

from student_manager.exceptions import StudentManagerError


class PersistenceError(StudentManagerError):
    """Base of everything the db package raises."""


class RecordNotFoundError(PersistenceError, LookupError):
    def __init__(self, table: str, record_id: int) -> None:
        super().__init__(f"у таблиці {table} немає запису з id={record_id}")
        self.table = table
        self.record_id = record_id


class ConstraintViolationError(PersistenceError, ValueError):
    """The database refused the change (CHECK, UNIQUE or FOREIGN KEY); the transaction was rolled back."""
