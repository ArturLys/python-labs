"""ORM models: two related tables. `groups` 1 --- * `students` (FOREIGN KEY students.group_id -> groups.id).

The same rules as the lab-1 model are enforced by the database itself: a CHECK constraint on the grade range,
UNIQUE on the group code and on the email. The `email` column was added later by migration 0002.
"""

from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from student_manager.config import GRADE_MAX, GRADE_MIN
from student_manager.models import Student


class Base(DeclarativeBase):
    """Declarative base; ``Base.metadata`` knows every table below (used by create_all and Alembic)."""


class GroupRecord(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True)

    # one-to-many; deleting a group deletes its students on the database side (ON DELETE CASCADE),
    # passive_deletes tells the ORM not to load them first just to delete them one by one.
    students: Mapped[list[StudentRecord]] = relationship(
        back_populates="group", cascade="all, delete-orphan", passive_deletes=True,
        order_by="StudentRecord.last_name",
    )

    def __repr__(self) -> str:
        return f"GroupRecord(id={self.id}, code={self.code!r})"


class StudentRecord(Base):
    __tablename__ = "students"
    __table_args__ = (
        CheckConstraint(f"average_grade >= {GRADE_MIN:g} AND average_grade <= {GRADE_MAX:g}",
                        name="ck_students_grade_range"),
        UniqueConstraint("email", name="uq_students_email"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(64))
    last_name: Mapped[str] = mapped_column(String(64), index=True)
    average_grade: Mapped[float]
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    email: Mapped[str | None] = mapped_column(String(120))  # migration 0002

    group: Mapped[GroupRecord] = relationship(back_populates="students")

    @property
    def full_name(self) -> str:
        return f"{self.last_name} {self.first_name}"

    def to_domain(self) -> Student:
        """The lab-1 dataclass, so the registry, analytics and reports keep working unchanged."""
        return Student(self.first_name, self.last_name, self.group.code, self.average_grade)

    def __repr__(self) -> str:
        return f"StudentRecord(id={self.id}, name={self.full_name!r}, grade={self.average_grade})"
