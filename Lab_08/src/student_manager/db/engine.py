"""Engine, session factory and the unit-of-work context manager (``session_scope``)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from student_manager.db.orm import Base

DEFAULT_URL = "sqlite:///data/students.db"


def _casefold(value: str | None) -> str | None:
    return None if value is None else value.casefold()


def make_engine(url: str = DEFAULT_URL, *, echo: bool = False) -> Engine:
    """SQLite ignores FOREIGN KEY unless every connection turns enforcement on; the connect hook does that."""
    engine = create_engine(url, echo=echo)

    @event.listens_for(engine, "connect")
    def configure_connection(dbapi_connection: Any, _record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()
        # SQLite's LIKE and lower() are case-insensitive for ASCII only; register Python's casefold as an
        # SQL function so that a search for "гн" finds "Гнатишин".
        dbapi_connection.create_function("casefold", 1, _casefold, deterministic=True)

    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    """expire_on_commit=False: objects stay readable after the transaction ends (the service returns them)."""
    return sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    """One transaction per ``with`` block: commit on success, rollback on any exception, close always."""
    session = factory()
    try:
        yield session
        session.commit()
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()


def create_schema(engine: Engine) -> None:
    """Tests build the schema straight from the models; the real database is built by Alembic."""
    Base.metadata.create_all(engine)
