"""Caching of a repeated expensive query: statistics of one group over the whole dataset.

The cache key includes a data version, so adding a student invalidates every cached answer automatically;
`invalidate()` is the explicit form. `info()` exposes hits and misses for the cold/warm analysis.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from math import inf

from student_manager.models import Student


@dataclass(frozen=True, slots=True)
class GroupStats:
    code: str
    count: int
    mean: float
    minimum: float
    maximum: float


class GroupStatisticsService:
    def __init__(self, students: Sequence[Student], maxsize: int = 64) -> None:
        self._students = list(students)
        self._version = 0
        self._cached = lru_cache(maxsize=maxsize)(self._compute)

    def _compute(self, code: str, version: int) -> GroupStats:  # noqa: ARG002 - version is part of the key
        total, count, low, high = 0.0, 0, inf, -inf
        for student in self._students:
            if student.group == code:
                grade = student.average_grade
                total += grade
                count += 1
                low = min(low, grade)
                high = max(high, grade)
        if count == 0:
            raise KeyError(code)
        return GroupStats(code, count, total / count, low, high)

    def group_statistics(self, code: str) -> GroupStats:
        return self._cached(code, self._version)

    def add(self, student: Student) -> None:
        """Data changed -> new version -> every old key misses (implicit invalidation)."""
        self._students.append(student)
        self._version += 1

    def invalidate(self) -> None:
        self._cached.cache_clear()

    def info(self) -> tuple[int, int, int]:
        """(hits, misses, current size)."""
        info = self._cached.cache_info()
        return info.hits, info.misses, info.currsize
