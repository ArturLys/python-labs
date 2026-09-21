"""Business logic: an in-memory registry of persons. Knows nothing about the console."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from statistics import mean

from student_manager.exceptions import PersonNotFoundError
from student_manager.models import Person


class PersonRegistry:
    """Keeps persons and answers questions about them."""

    def __init__(self, persons: Iterable[Person] = ()) -> None:
        self._persons: list[Person] = []
        for person in persons:
            self.add(person)

    def __len__(self) -> int:
        return len(self._persons)

    def __iter__(self) -> Iterator[Person]:
        return iter(self._persons)

    def add(self, person: Person) -> Person:
        """Register a person; the same person in the same group twice is a mistake."""
        if any(s.full_name == person.full_name and s.group == person.group for s in self._persons):
            raise ValueError(f"{person.full_name} уже зареєстрований у групі {person.group}")
        self._persons.append(person)
        return person

    def all(self) -> list[Person]:
        return list(self._persons)

    def groups(self) -> list[str]:
        return sorted({s.group for s in self._persons})

    def by_group(self, group: str) -> list[Person]:
        wanted = group.strip().casefold()
        return [s for s in self._persons if s.group.casefold() == wanted]

    def best(self, group: str | None = None) -> Person:
        """Top person overall, or inside one group."""
        candidates = self._persons if group is None else self.by_group(group)
        if not candidates:
            raise PersonNotFoundError("немає студентів" if group is None else f"у групі {group} немає студентів")
        return max(candidates, key=lambda s: s.average_grade)

    def group_average(self, group: str) -> float:
        members = self.by_group(group)
        if not members:
            raise PersonNotFoundError(f"у групі {group} немає студентів")
        return mean(s.average_grade for s in members)

    def sorted_by_grade(self, descending: bool = True) -> list[Person]:
        """Rating. Sort is stable, so equal grades keep alphabetical order."""
        alphabetical = sorted(self._persons, key=lambda s: s.full_name)
        return sorted(alphabetical, key=lambda s: s.average_grade, reverse=descending)

    def search(self, *, last_name: str | None = None, group: str | None = None,
               min_grade: float | None = None) -> list[Person]:
        """Multi-criteria search; every criterion given narrows the result."""
        result = self._persons
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
        if not self._persons:
            return {"count": 0, "mean": 0.0, "min": 0.0, "max": 0.0, "excellent": 0}
        grades = [s.average_grade for s in self._persons]
        return {
            "count": len(grades),
            "mean": mean(grades),
            "min": min(grades),
            "max": max(grades),
            "excellent": sum(s.is_excellent for s in self._persons),
        }
