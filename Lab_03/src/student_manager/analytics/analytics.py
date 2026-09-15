"""Number-level analytics: averages, best student, ranking, thresholds, summaries, pipelines."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from statistics import mean
from typing import Any

from student_manager.analytics.data import GradeRecord
from student_manager.analytics.decorators import log_calls, measure_time
from student_manager.analytics.processors import group_by, index_by_student, unique_groups

Score = tuple[str, float]                 # (student, average) — a tuple, because a pair is a pair
ScoreFilter = Callable[[Score], bool]
Step = Callable[[list[Score]], list[Score]]


def mean_of(*values: float) -> float:
    """*args: any number of positional numbers."""
    return mean(values) if values else 0.0


def make_record(**fields: Any) -> GradeRecord:
    """**kwargs: build a record from named fields; NamedTuple validates the names."""
    return GradeRecord(**fields)


@measure_time
def student_averages(records: Iterable[GradeRecord]) -> dict[str, float]:
    """Dict comprehension over the student index; generator expression feeds mean_of via *."""
    return {
        student: mean_of(*(r.grade for r in rows))
        for student, rows in index_by_student(records).items()
    }


def group_averages(records: Iterable[GradeRecord]) -> dict[str, float]:
    return {
        group: mean(r.grade for r in members)
        for group, members in group_by(records, lambda r: r.group).items()
    }


def discipline_averages(records: Iterable[GradeRecord]) -> dict[str, float]:
    return {
        discipline: mean(r.grade for r in members)
        for discipline, members in group_by(records, lambda r: r.discipline).items()
    }


@log_calls("analytics", show_result=True)
def best_student(records: Iterable[GradeRecord]) -> Score:
    """max() with a lambda key over (student, average) pairs."""
    return max(student_averages(records).items(), key=lambda pair: pair[1])


@log_calls("analytics")
def ranking(records: Iterable[GradeRecord]) -> list[Score]:
    """Sorted by average, best first; ties broken by name thanks to the tuple key."""
    return sorted(student_averages(records).items(), key=lambda pair: (-pair[1], pair[0]))


def make_threshold_filter(minimum: float) -> ScoreFilter:
    """Closure: `predicate` remembers `minimum` after this function has returned."""

    def predicate(score: Score) -> bool:
        return score[1] >= minimum

    return predicate


def above_threshold(records: Iterable[GradeRecord], minimum: float) -> list[Score]:
    is_good_enough = make_threshold_filter(minimum)
    return [score for score in ranking(records) if is_good_enough(score)]


def grade_range(records: Iterable[GradeRecord]) -> tuple[float, float]:
    """(min, max) as a tuple: two values that belong together and never change."""
    grades = [r.grade for r in records]
    return (min(grades), max(grades))


def summary(records: list[GradeRecord]) -> dict[str, Any]:
    """Aggregation in one dict, ready to print or export."""
    averages = student_averages(records)
    low, high = grade_range(records)
    return {
        "records": len(records),
        "students": len(averages),
        "groups": len(unique_groups(records)),
        "mean": mean(averages.values()),
        "min_grade": low,
        "max_grade": high,
        "best": best_student(records),
    }


def pipeline(scores: list[Score], *steps: Step) -> list[Score]:
    """Function pipeline: *args of callables applied left to right."""
    for step in steps:
        scores = step(scores)
    return scores
