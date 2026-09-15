"""Aggregation stage (the sinks): one-pass statistics, bounded top-N, running values, lazy search, grouping."""

from __future__ import annotations

import heapq
from collections import Counter
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from itertools import accumulate, count, groupby, pairwise

from student_manager.streaming.models import StudentRecord


@dataclass
class Stats:
    """Everything variant 1 asks for, gathered in one pass without keeping a single record."""

    count: int = 0
    total: float = 0.0
    minimum: float | None = None
    maximum: float | None = None
    per_group: Counter[str] = field(default_factory=Counter)

    @property
    def average(self) -> float:
        return self.total / self.count if self.count else 0.0

    def add(self, record: StudentRecord) -> None:
        self.count += 1
        self.total += record.grade
        self.per_group[record.group] += 1
        if self.minimum is None or record.grade < self.minimum:
            self.minimum = record.grade
        if self.maximum is None or record.grade > self.maximum:
            self.maximum = record.grade


def streaming_stats(records: Iterable[StudentRecord]) -> Stats:
    """Count, average, min, max and records per group in one pass; peak memory does not depend on n."""
    stats = Stats()
    for record in records:
        stats.add(record)
    return stats


def count_by_group(records: Iterable[StudentRecord]) -> Counter[str]:
    """Records per group; the generator expression feeds Counter one group name at a time."""
    return Counter(record.group for record in records)


def top_n(records: Iterable[StudentRecord], n: int) -> list[StudentRecord]:
    """The n best grades of a stream: heapq keeps only n items while the whole stream flows past."""
    return heapq.nlargest(n, records, key=lambda record: (record.grade, -record.student_id))


def find_first(records: Iterable[StudentRecord], predicate: Callable[[StudentRecord], bool]) -> StudentRecord | None:
    """Lazy search: stops pulling from the stream at the first match (early termination)."""
    return next((record for record in records if predicate(record)), None)


def running_average(grades: Iterable[float]) -> Iterator[float]:
    """Lazy cumulative mean: accumulate() gives running sums, count() the divisors."""
    return (total / n for total, n in zip(accumulate(grades), count(1)))


def grade_changes(records: Iterable[StudentRecord]) -> Iterator[float]:
    """Difference between neighbouring grades in the stream (pairwise)."""
    return (current.grade - previous.grade for previous, current in pairwise(records))


def by_group(records: Iterable[StudentRecord]) -> Iterator[tuple[str, list[StudentRecord]]]:
    """Group a batch with groupby(): it only joins neighbours, so the batch is sorted by the same key first."""
    ordered = sorted(records, key=lambda record: record.group)
    for group, members in groupby(ordered, key=lambda record: record.group):
        yield group, list(members)
