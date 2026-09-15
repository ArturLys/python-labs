"""The API's view of the persistence layer: repositories of lab 7 wrapped into schema-returning operations.

Every method is one transaction and converts ORM records to Pydantic models *inside* the session, so no lazy
load ever happens after the session is closed.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Literal

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, contains_eager, sessionmaker

from student_manager.api.schemas import GroupStatisticsOut, StudentCreate, StudentOut, StudentPage, StudentPatch
from student_manager.db import (
    ConstraintViolationError,
    GroupRecord,
    GroupRepository,
    RecordNotFoundError,
    StudentRecord,
    StudentRepository,
    session_scope,
)

SortKey = Literal["id", "last_name", "grade", "-grade"]


class StudentStore:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    @contextmanager
    def _transaction(self) -> Iterator[Session]:
        try:
            with session_scope(self._factory) as session:
                yield session
        except IntegrityError as error:
            raise ConstraintViolationError(f"база даних відхилила зміну: {error.orig}") from error

    # --- students ---------------------------------------------------------------------------------------------

    def search(
        self,
        *,
        last_name: str | None = None,
        group: str | None = None,
        page: int = 1,
        size: int = 20,
        sort: SortKey = "id",
    ) -> StudentPage:
        with self._transaction() as session:
            statement = select(StudentRecord).join(StudentRecord.group).options(contains_eager(StudentRecord.group))
            if last_name:
                statement = statement.where(func.casefold(StudentRecord.last_name).like(f"{last_name.casefold()}%"))
            if group:
                statement = statement.where(GroupRecord.code == group)
            total = session.scalar(select(func.count()).select_from(statement.subquery())) or 0
            order = {
                "id": StudentRecord.id,
                "last_name": StudentRecord.last_name,
                "grade": StudentRecord.average_grade,
                "-grade": StudentRecord.average_grade.desc(),
            }[sort]
            rows = session.scalars(statement.order_by(order, StudentRecord.id).offset((page - 1) * size).limit(size))
            return StudentPage(items=[StudentOut.from_record(r) for r in rows], total=total, page=page, size=size)

    def get(self, student_id: int) -> StudentOut:
        with self._transaction() as session:
            return StudentOut.from_record(StudentRepository(session).require(student_id))

    def create(self, data: StudentCreate) -> StudentOut:
        with self._transaction() as session:
            group = GroupRepository(session).get_or_create(data.group)
            record = StudentRepository(session).add(
                StudentRecord(
                    first_name=data.first_name,
                    last_name=data.last_name,
                    average_grade=data.average_grade,
                    email=data.email,
                    group=group,
                )
            )
            return StudentOut.from_record(record)

    def patch(self, student_id: int, data: StudentPatch) -> StudentOut:
        with self._transaction() as session:
            record = StudentRepository(session).require(student_id)
            if data.average_grade is not None:
                record.average_grade = data.average_grade
            if data.group is not None:
                record.group = GroupRepository(session).get_or_create(data.group)
            if data.email is not None:
                record.email = data.email
            session.flush()
            return StudentOut.from_record(record)

    def delete(self, student_id: int) -> bool:
        with self._transaction() as session:
            return StudentRepository(session).remove(student_id)

    def best(self, group: str | None = None) -> StudentOut | None:
        with self._transaction() as session:
            record = StudentRepository(session).best(group)
            return None if record is None else StudentOut.from_record(record)

    # --- groups -----------------------------------------------------------------------------------------------

    def group_statistics(self, code: str) -> GroupStatisticsOut:
        with self._transaction() as session:
            groups = GroupRepository(session)
            if groups.by_code(code) is None:
                raise RecordNotFoundError("groups", code)
            stats = next(s for s in groups.statistics() if s.code == code.strip())
            best = StudentRepository(session).best(code)
            return GroupStatisticsOut(
                code=stats.code,
                students=stats.students,
                average=stats.average,
                best=None if best is None else StudentOut.from_record(best),
            )

    def groups(self) -> list[GroupStatisticsOut]:
        with self._transaction() as session:
            codes = [s.code for s in GroupRepository(session).statistics()]
        return [self.group_statistics(code) for code in codes]

    def group_students(self, code: str) -> list[StudentOut]:
        with self._transaction() as session:
            if GroupRepository(session).by_code(code) is None:
                raise RecordNotFoundError("groups", code)
            return [StudentOut.from_record(r) for r in StudentRepository(session).filter_by_group(code)]

    # --- ops --------------------------------------------------------------------------------------------------

    def ping(self) -> bool:
        """One trivial round trip; /health reports the database as down if it fails."""
        try:
            with self._transaction() as session:
                session.execute(text("SELECT 1"))
        except Exception:  # noqa: BLE001 - any failure means "not healthy"
            return False
        return True
