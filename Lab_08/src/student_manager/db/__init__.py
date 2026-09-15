"""Persistence layer: SQLite + SQLAlchemy ORM, repositories, transactions and Alembic migrations (ЛР7)."""

from student_manager.db.engine import DEFAULT_URL, create_schema, make_engine, make_session_factory, session_scope
from student_manager.db.exceptions import ConstraintViolationError, PersistenceError, RecordNotFoundError
from student_manager.db.orm import Base, GroupRecord, StudentRecord
from student_manager.db.repositories import GroupRepository, GroupStats, SqlRepository, StudentRepository
from student_manager.db.services import NewStudent, StudentService

__all__ = [
    "Base", "ConstraintViolationError", "DEFAULT_URL", "GroupRecord", "GroupRepository", "GroupStats",
    "NewStudent", "PersistenceError", "RecordNotFoundError", "SqlRepository", "StudentRecord",
    "StudentRepository", "StudentService", "create_schema", "make_engine", "make_session_factory",
    "session_scope",
]
