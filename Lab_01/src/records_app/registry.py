"""Business logic: an in-memory registry of students. Knows nothing about the console."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from statistics import mean

from records_app.exceptions import StudentNotFoundError
from records_app.models import Student


class StudentRegistry:
    """Keeps students and answers questions about them."""

    def __init__(self, students: Iterable[Student] = ()) -> None:
        self._students: list[Student] = []
        for student in students:
            self.add(student)

    def __len__(self) -> int:
        return len(self._students)

    def __iter__(self) -> Iterator[Student]:
        return iter(self._students)

    def add(self, student: Student) -> Student:
        """Register a student; the same person in the same group twice is a mistake."""
        if any(s.full_name == student.full_name and s.group == student.group for s in self._students):
            raise ValueError(f"{student.full_name} уже зареєстрований у групі {student.group}")
        self._students.append(student)
        return student

    def all(self) -> list[Student]:
        return list(self._students)

    def groups(self) -> list[str]:
        return sorted({s.group for s in self._students})

    def by_group(self, group: str) -> list[Student]:
        wanted = group.strip().casefold()
        return [s for s in self._students if s.group.casefold() == wanted]

    def best(self, group: str | None = None) -> Student:
        """Top student overall, or inside one group."""
        candidates = self._students if group is None else self.by_group(group)
        if not candidates:
            raise StudentNotFoundError("немає студентів" if group is None else f"у групі {group} немає студентів")
        return max(candidates, key=lambda s: s.average_grade)

    def group_average(self, group: str) -> float:
        members = self.by_group(group)
        if not members:
            raise StudentNotFoundError(f"у групі {group} немає студентів")
        return mean(s.average_grade for s in members)

    def sorted_by_grade(self, descending: bool = True) -> list[Student]:
        """Rating. Sort is stable, so equal grades keep alphabetical order."""
        alphabetical = sorted(self._students, key=lambda s: s.full_name)
        return sorted(alphabetical, key=lambda s: s.average_grade, reverse=descending)

    def search(self, *, last_name: str | None = None, group: str | None = None,
               min_grade: float | None = None) -> list[Student]:
        """Multi-criteria search; every criterion given narrows the result."""
        result = self._students
        if last_name is not None:
            prefix = last_name.strip().casefold()
            result = [s for s in result if s.last_name.casefold().startswith(prefix)]
        if group is not None:
            wanted = group.strip().casefold()
            result = [s for s in result if s.group.casefold() == wanted]
        if min_grade is not None:
            result = [s for s in result if s.average_grade >= min_grade]
        return list(result)

    def statistics(self) -> dict[str, float]:
        if not self._students:
            return {"count": 0, "mean": 0.0, "min": 0.0, "max": 0.0, "excellent": 0}
        grades = [s.average_grade for s in self._students]
        return {
            "count": len(grades),
            "mean": mean(grades),
            "min": min(grades),
            "max": max(grades),
            "excellent": sum(s.is_excellent for s in self._students),
        }
