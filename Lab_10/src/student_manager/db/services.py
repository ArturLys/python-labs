"""Business operations of the variant on top of the repositories. Each public method is one transaction."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from student_manager.db.engine import session_scope
from student_manager.db.exceptions import ConstraintViolationError
from student_manager.db.orm import StudentRecord
from student_manager.db.repositories import GroupRepository, GroupStats, StudentRepository
from student_manager.models import Student


@dataclass(frozen=True, slots=True)
class NewStudent:
    first_name: str
    last_name: str
    group: str
    average_grade: float
    email: str | None = None


class StudentService:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    # --- Create ---------------------------------------------------------------------------------------------

    def add(self, data: NewStudent) -> int:
        with self._transaction() as session:
            group = GroupRepository(session).get_or_create(data.group)
            record = StudentRepository(session).add(
                StudentRecord(
                    first_name=data.first_name.strip(),
                    last_name=data.last_name.strip(),
                    average_grade=data.average_grade,
                    email=data.email,
                    group=group,
                )
            )
            return record.id

    def import_many(self, rows: Iterable[NewStudent]) -> int:
        """All or nothing: one bad row rolls back every row inserted before it (atomicity)."""
        added = 0
        with self._transaction(on_row=lambda: added + 1) as session:
            for row in rows:
                group = GroupRepository(session).get_or_create(row.group)
                StudentRepository(session).add(
                    StudentRecord(
                        first_name=row.first_name,
                        last_name=row.last_name,
                        average_grade=row.average_grade,
                        email=row.email,
                        group=group,
                    )
                )
                added += 1
        return added

    # --- Read -----------------------------------------------------------------------------------------------

    def listing(self) -> list[Student]:
        with self._transaction() as session:
            return [r.to_domain() for r in StudentRepository(session).all(StudentRecord.id)]

    def find(self, last_name: str) -> list[Student]:
        with self._transaction() as session:
            return [r.to_domain() for r in StudentRepository(session).by_last_name(last_name)]

    def in_group(self, code: str) -> list[Student]:
        with self._transaction() as session:
            return [r.to_domain() for r in StudentRepository(session).filter_by_group(code)]

    def best(self, code: str | None = None) -> Student | None:
        with self._transaction() as session:
            record = StudentRepository(session).best(code)
            return None if record is None else record.to_domain()

    def group_average(self, code: str) -> float | None:
        with self._transaction() as session:
            return GroupRepository(session).average(code)

    def group_statistics(self) -> list[GroupStats]:
        with self._transaction() as session:
            return GroupRepository(session).statistics()

    # --- Update ---------------------------------------------------------------------------------------------

    def set_grade(self, student_id: int, grade: float) -> Student:
        with self._transaction() as session:
            return StudentRepository(session).update_grade(student_id, grade).to_domain()

    def transfer(self, student_id: int, group_code: str) -> Student:
        """Move to another group, creating it if needed: two writes that must succeed or fail together."""
        with self._transaction() as session:
            student = StudentRepository(session).require(student_id)
            student.group = GroupRepository(session).get_or_create(group_code)
            session.flush()
            return student.to_domain()

    # --- Delete ---------------------------------------------------------------------------------------------

    def remove(self, student_id: int) -> bool:
        with self._transaction() as session:
            return StudentRepository(session).remove(student_id)

    def remove_group(self, code: str) -> int:
        """Deleting a group cascades to its students; returns how many students went with it."""
        with self._transaction() as session:
            groups = GroupRepository(session)
            group = groups.by_code(code)
            if group is None:
                return 0
            count = len(StudentRepository(session).filter_by_group(code))
            session.delete(group)
            session.flush()
            return count

    # --- helpers --------------------------------------------------------------------------------------------

    @contextmanager
    def _transaction(self, on_row: Callable[[], int] | None = None) -> Iterator[Session]:
        """session_scope plus translation of IntegrityError into the package's own exception.
        The rollback has already happened (inside session_scope) by the time the error is re-raised."""
        try:
            with session_scope(self._factory) as session:
                yield session
        except IntegrityError as error:
            where = f" (рядок {on_row()})" if on_row is not None else ""
            raise ConstraintViolationError(f"база даних відхилила зміну{where}: {error.orig}") from error
