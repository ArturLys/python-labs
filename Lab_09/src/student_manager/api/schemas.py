"""Pydantic schemas: what the API accepts and what it returns. Validation rules mirror the lab-1 model."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from student_manager.config import GRADE_MAX, GRADE_MIN, GROUP_PATTERN
from student_manager.db.orm import StudentRecord

Grade = Annotated[float, Field(ge=GRADE_MIN, le=GRADE_MAX, examples=[88.5], description="Середній бал, 0..100")]
GroupCode = Annotated[str, Field(pattern=f"^{GROUP_PATTERN}$", examples=["ФЕП-31с"], description="Код групи")]
Name = Annotated[str, Field(min_length=1, max_length=64, examples=["Марта"])]
Email = Annotated[str, Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=120, examples=["marta@lnu.edu.ua"])]


class StudentCreate(BaseModel):
    """POST /students body. Unknown fields are rejected (extra="forbid"), strings are stripped."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    first_name: Name
    last_name: Name
    group: GroupCode
    average_grade: Grade
    email: Email | None = None


class StudentPatch(BaseModel):
    """PATCH /students/{id} body: every field optional, at least one must be present."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    average_grade: Grade | None = None
    group: GroupCode | None = None
    email: Email | None = None

    def is_empty(self) -> bool:
        return not self.model_fields_set


class StudentOut(BaseModel):
    """Response model: the ORM record flattened to JSON-friendly fields."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str
    full_name: str
    group: str
    average_grade: float
    email: str | None = None

    @classmethod
    def from_record(cls, record: StudentRecord) -> StudentOut:
        return cls(id=record.id, first_name=record.first_name, last_name=record.last_name,
                   full_name=record.full_name, group=record.group.code, average_grade=record.average_grade,
                   email=record.email)


class StudentPage(BaseModel):
    items: list[StudentOut]
    total: int
    page: int
    size: int


class GroupStatisticsOut(BaseModel):
    code: str
    students: int
    average: float | None
    best: StudentOut | None


class ErrorOut(BaseModel):
    """Structured error body used by every custom exception handler."""

    error: str
    detail: str
