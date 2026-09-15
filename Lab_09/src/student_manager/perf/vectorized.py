"""NumPy: the same statistics as array operations — no Python-level loop over students."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from student_manager.models import Student
from student_manager.perf.baseline import Stats


@dataclass(frozen=True, slots=True)
class Arrays:
    grades: NDArray[np.float64]
    group_ids: NDArray[np.int64]
    codes: list[str]  # group id -> code


def to_arrays(students: Sequence[Student]) -> Arrays:
    """One-time conversion (this is the cost NumPy has to pay back)."""
    codes = sorted({s.group for s in students})
    index = {code: i for i, code in enumerate(codes)}
    grades = np.fromiter((s.average_grade for s in students), dtype=np.float64, count=len(students))
    group_ids = np.fromiter((index[s.group] for s in students), dtype=np.int64, count=len(students))
    return Arrays(grades, group_ids, codes)


def compute_stats_numpy(arrays: Arrays) -> Stats:
    grades, ids = arrays.grades, arrays.group_ids
    if grades.size == 0:
        raise ValueError("порожній набір студентів")
    sums = np.bincount(ids, weights=grades, minlength=len(arrays.codes))
    counts = np.bincount(ids, minlength=len(arrays.codes))
    group_means = {code: float(sums[i] / counts[i]) for i, code in enumerate(arrays.codes) if counts[i]}
    ranking = np.argsort(-grades, kind="stable")  # stable: ties keep input order, like sorted(reverse=True)
    return Stats(int(grades.size), float(grades.mean()), float(grades.min()), float(grades.max()),
                 float(grades.std()), group_means, ranking.tolist())


def compute_stats_numpy_from_students(students: Sequence[Student]) -> Stats:
    """Conversion + computation together, for a fair comparison with the loop-based versions."""
    return compute_stats_numpy(to_arrays(students))
