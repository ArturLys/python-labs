"""Asynchronous facade over a remote student gateway (the university API in a later lab).

The gateway is a Protocol with ``async`` methods; the service composes them with ``asyncio.gather``.
Tests inject an ``AsyncMock`` and check both the results and how the gateway was awaited.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from typing import Protocol

from student_manager.exceptions import StudentNotFoundError
from student_manager.models import Student


class StudentGateway(Protocol):
    async def fetch(self, student_id: int) -> Student | None: ...

    async def save(self, student_id: int, student: Student) -> None: ...


class AsyncStudentService:
    def __init__(self, gateway: StudentGateway) -> None:
        self._gateway = gateway

    async def require(self, student_id: int) -> Student:
        student = await self._gateway.fetch(student_id)
        if student is None:
            raise StudentNotFoundError(f"студента з id={student_id} не знайдено")
        return student

    async def average_of(self, student_ids: Iterable[int]) -> float:
        """All fetches run concurrently; an empty id list is an error, not a silent 0.0."""
        ids = list(student_ids)
        if not ids:
            raise ValueError("порожній список студентів")
        students = await asyncio.gather(*(self.require(i) for i in ids))
        return sum(s.average_grade for s in students) / len(students)

    async def bump_grade(self, student_id: int, delta: float) -> Student:
        student = await self.require(student_id)
        updated = Student(student.first_name, student.last_name, student.group,
                          min(100.0, student.average_grade + delta))
        await self._gateway.save(student_id, updated)
        return updated
