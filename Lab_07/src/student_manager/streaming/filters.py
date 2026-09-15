"""Filtering stage: generators that let a record through or drop it, one record at a time."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from itertools import takewhile

from student_manager.streaming.models import StudentRecord

Predicate = Callable[[StudentRecord], bool]


def with_min_grade(records: Iterable[StudentRecord], minimum: float) -> Iterator[StudentRecord]:
    """Variant 1: students with grade >= threshold."""
    for record in records:
        if record.grade >= minimum:
            yield record


def in_groups(records: Iterable[StudentRecord], groups: Iterable[str]) -> Iterator[StudentRecord]:
    """Keep the given groups only; the set is built once, the stream is never materialised."""
    wanted = set(groups)
    return (record for record in records if record.group in wanted)


def where(records: Iterable[StudentRecord], predicate: Predicate) -> Iterator[StudentRecord]:
    """Universal lazy filter — the streaming twin of analytics.processors.filter_items(). Built-in filter() is lazy."""
    return filter(predicate, records)


def head_by_id(records: Iterable[StudentRecord], last_id: int) -> Iterator[StudentRecord]:
    """Records while student_id <= last_id. Ids grow along the file, so takewhile stops reading it early."""
    return takewhile(lambda record: record.student_id <= last_id, records)
