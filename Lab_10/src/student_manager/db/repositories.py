"""Repository pattern over SQLAlchemy sessions.

``SqlRepository[T]`` holds the generic CRUD; ``StudentRepository`` and ``GroupRepository`` add the queries of
the variant. Repositories never commit: the transaction belongs to the caller (service / session_scope).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from sqlalchemy import ColumnExpressionArgument, func, select
from sqlalchemy.orm import Session

from student_manager.db.exceptions import RecordNotFoundError
from student_manager.db.orm import Base, GroupRecord, StudentRecord

T = TypeVar("T", bound=Base)


class SqlRepository(Generic[T]):
    def __init__(self, session: Session, model: type[T]) -> None:
        self._session = session
        self._model = model

    def add(self, item: T) -> T:
        self._session.add(item)
        self._session.flush()  # INSERT now, so constraint errors surface here and the id is assigned
        return item

    def get(self, item_id: int) -> T | None:
        return self._session.get(self._model, item_id)

    def require(self, item_id: int) -> T:
        item = self.get(item_id)
        if item is None:
            raise RecordNotFoundError(str(self._model.__tablename__), item_id)
        return item

    def all(self, *order_by: ColumnExpressionArgument[Any], limit: int | None = None, offset: int = 0) -> list[T]:
        statement = select(self._model).order_by(*order_by).offset(offset).limit(limit)
        return list(self._session.scalars(statement).all())

    def remove(self, item_id: int) -> bool:
        item = self.get(item_id)
        if item is None:
            return False
        self._session.delete(item)
        self._session.flush()
        return True

    def count(self) -> int:
        return self._session.scalar(select(func.count()).select_from(self._model)) or 0


@dataclass(frozen=True, slots=True)
class GroupStats:
    code: str
    students: int
    average: float | None


class GroupRepository(SqlRepository[GroupRecord]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, GroupRecord)

    def by_code(self, code: str) -> GroupRecord | None:
        return self._session.scalar(select(GroupRecord).where(GroupRecord.code == code.strip()))

    def get_or_create(self, code: str) -> GroupRecord:
        return self.by_code(code) or self.add(GroupRecord(code=code.strip()))

    def statistics(self) -> list[GroupStats]:
        """JOIN + GROUP BY + COUNT/AVG in one round trip; groups without students give average None."""
        statement = (
            select(GroupRecord.code, func.count(StudentRecord.id), func.avg(StudentRecord.average_grade))
            .outerjoin(StudentRecord, StudentRecord.group_id == GroupRecord.id)
            .group_by(GroupRecord.id)
            .order_by(GroupRecord.code)
        )
        return [GroupStats(code, students, average) for code, students, average in self._session.execute(statement)]

    def average(self, code: str) -> float | None:
        statement = (
            select(func.avg(StudentRecord.average_grade))
            .join(GroupRecord, GroupRecord.id == StudentRecord.group_id)
            .where(GroupRecord.code == code)
        )
        return self._session.scalar(statement)


class StudentRepository(SqlRepository[StudentRecord]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, StudentRecord)

    def by_last_name(self, last_name: str) -> list[StudentRecord]:
        prefix = last_name.strip().casefold()
        statement = (
            select(StudentRecord)
            .where(func.casefold(StudentRecord.last_name).like(f"{prefix}%"))  # casefold: see engine.py
            .order_by(StudentRecord.last_name, StudentRecord.first_name)
        )
        return list(self._session.scalars(statement).all())

    def filter_by_group(self, code: str) -> list[StudentRecord]:
        statement = (
            select(StudentRecord)
            .join(StudentRecord.group)
            .where(GroupRecord.code == code.strip())
            .order_by(StudentRecord.last_name)
        )
        return list(self._session.scalars(statement).all())

    def best(self, code: str | None = None) -> StudentRecord | None:
        statement = select(StudentRecord).order_by(StudentRecord.average_grade.desc(), StudentRecord.id).limit(1)
        if code is not None:
            statement = statement.join(StudentRecord.group).where(GroupRecord.code == code)
        return self._session.scalar(statement)

    def update_grade(self, student_id: int, grade: float) -> StudentRecord:
        student = self.require(student_id)
        student.average_grade = grade
        self._session.flush()  # UPDATE now: the CHECK constraint answers immediately
        return student

    def page(self, number: int, size: int, *, descending: bool = False) -> Sequence[StudentRecord]:
        order = StudentRecord.average_grade.desc() if descending else StudentRecord.average_grade.asc()
        return self.all(order, StudentRecord.id, limit=size, offset=(number - 1) * size)
