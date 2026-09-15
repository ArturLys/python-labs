"""Baseline: plain Python loops. Every optimised implementation must reproduce exactly these numbers."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import inf, isclose, sqrt

from student_manager.models import Student


@dataclass(frozen=True, slots=True)
class Stats:
    count: int
    mean: float
    minimum: float
    maximum: float
    std: float                      # population standard deviation
    group_means: dict[str, float]   # group code -> mean, sorted by code
    ranking: Sequence[int]          # indices of students, best first (ties keep input order)


def compute_stats(students: Sequence[Student]) -> Stats:
    if not students:
        raise ValueError("порожній набір студентів")
    total, low, high = 0.0, inf, -inf
    sums: dict[str, float] = {}
    counts: dict[str, int] = {}
    for student in students:
        grade = student.average_grade
        total += grade
        low = min(low, grade)
        high = max(high, grade)
        sums[student.group] = sums.get(student.group, 0.0) + grade
        counts[student.group] = counts.get(student.group, 0) + 1
    n = len(students)
    mean = total / n
    squares = 0.0
    for student in students:
        squares += (student.average_grade - mean) ** 2
    group_means = {code: sums[code] / counts[code] for code in sorted(sums)}
    ranking = sorted(range(n), key=lambda i: students[i].average_grade, reverse=True)
    return Stats(n, mean, low, high, sqrt(squares / n), group_means, ranking)


def stats_close(left: Stats, right: Stats, *, rel: float = 1e-9) -> bool:
    """Equality up to floating-point noise; the ranking must match exactly."""
    return (
        left.count == right.count
        and isclose(left.mean, right.mean, rel_tol=rel)
        and left.minimum == right.minimum and left.maximum == right.maximum
        and isclose(left.std, right.std, rel_tol=1e-7)
        and left.group_means.keys() == right.group_means.keys()
        and all(isclose(left.group_means[k], right.group_means[k], rel_tol=rel) for k in left.group_means)
        and list(left.ranking) == list(right.ranking)
    )
