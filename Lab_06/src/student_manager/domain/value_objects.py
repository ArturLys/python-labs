"""Value objects: immutable, compared by value, validated once in __post_init__.

A Grade of 95 is the same grade wherever it appears, so it has no identity — that is what makes it a
value object rather than an entity. frozen=True gives immutability and hashability, slots=True keeps
the instances small and forbids accidental new attributes.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from functools import total_ordering
from typing import TypeVar

from student_manager.config import EXCELLENT_THRESHOLD, GRADE_MAX, GRADE_MIN, GROUP_PATTERN
from student_manager.exceptions import InvalidGradeError, InvalidGroupError

PASSING_THRESHOLD = 60.0

# Constrained TypeVar: the function accepts int OR float and promises to return the same one.
Points = TypeVar("Points", int, float)


def validated_points(value: Points) -> Points:
    """Range check on the 100-point scale that hands the value back with the type it came with."""
    if not GRADE_MIN <= value <= GRADE_MAX:
        raise InvalidGradeError(value)
    return value


class AcademicStatus(StrEnum):
    """Result of an academic status policy; a str subclass, so it serialises as plain text."""

    NO_GRADES = "без оцінок"
    EXCELLENT = "відмінник"
    GOOD = "встигає"
    AT_RISK = "ризик відрахування"


@dataclass(frozen=True, slots=True)
class PersonName:
    """First and last name, normalised and never empty."""

    first: str
    last: str

    def __post_init__(self) -> None:
        # A frozen dataclass blocks plain assignment; object.__setattr__ is the documented way
        # to normalise fields inside __post_init__.
        object.__setattr__(self, "first", self.first.strip())
        object.__setattr__(self, "last", self.last.strip())
        if not self.first or not self.last:
            raise ValueError("ім'я та прізвище не можуть бути порожніми")

    @property
    def full(self) -> str:
        return f"{self.last} {self.first}"

    @property
    def initials(self) -> str:
        return f"{self.last} {self.first[0]}."

    def __str__(self) -> str:
        return self.full


@dataclass(frozen=True, slots=True)
class GroupCode:
    """Academic group name such as ФЕП-31с; validated against the lab-1 pattern."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", self.value.strip())
        if not re.fullmatch(GROUP_PATTERN, self.value):
            raise InvalidGroupError(self.value)

    @property
    def faculty(self) -> str:
        """Letters before the dash: ФЕП."""
        return self.value.split("-", 1)[0]

    @property
    def stream(self) -> str:
        """Digits after the dash: 31."""
        return re.sub(r"\D", "", self.value.split("-", 1)[1])

    def __str__(self) -> str:
        return self.value


@total_ordering
@dataclass(frozen=True, slots=True)
class Grade:
    """One mark on the 100-point scale with its ECTS letter.

    dataclass generates __eq__; __lt__ is written by hand and total_ordering derives <=, >, >=.
    """

    points: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "points", float(validated_points(self.points)))

    @property
    def ects(self) -> str:
        """ECTS letter by the LNU scale."""
        for floor, letter in ((90, "A"), (81, "B"), (71, "C"), (61, "D"), (PASSING_THRESHOLD, "E")):
            if self.points >= floor:
                return letter
        return "FX"

    @property
    def is_passing(self) -> bool:
        return self.points >= PASSING_THRESHOLD

    @property
    def is_excellent(self) -> bool:
        return self.points >= EXCELLENT_THRESHOLD

    def to_dict(self) -> Mapping[str, object]:
        return {"points": self.points, "ects": self.ects}

    def __lt__(self, other: Grade) -> bool:
        return self.points < other.points

    def __str__(self) -> str:
        return f"{self.points:.1f} ({self.ects})"


@dataclass(frozen=True, slots=True)
class Credits:
    """ECTS credits of a course; supports + so that sum() over courses works."""

    ects: int

    def __post_init__(self) -> None:
        if self.ects < 0:
            raise ValueError("кількість кредитів не може бути від'ємною")

    def __add__(self, other: Credits) -> Credits:
        return Credits(self.ects + other.ects)

    def __str__(self) -> str:
        return f"{self.ects} кред."


ZERO_CREDITS = Credits(0)
