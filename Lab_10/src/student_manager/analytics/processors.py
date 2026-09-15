"""Structure-level operations on records: filtering, sorting, grouping, indexing, counting."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Callable, Iterable

from student_manager.analytics.data import GradeRecord

Predicate = Callable[[GradeRecord], bool]
KeyFunc = Callable[[GradeRecord], str]


def unique_groups(records: Iterable[GradeRecord]) -> set[str]:
    """Set comprehension: duplicates vanish on their own."""
    return {r.group for r in records}


def unique_disciplines(records: Iterable[GradeRecord]) -> set[str]:
    return {r.discipline for r in records}


def filter_items(records: Iterable[GradeRecord], predicate: Predicate) -> list[GradeRecord]:
    """Universal filter: the caller decides what 'matches' means."""
    return [r for r in records if predicate(r)]


def sort_items(
    records: Iterable[GradeRecord], key: KeyFunc | Callable[[GradeRecord], float], reverse: bool = False
) -> list[GradeRecord]:
    """Universal sort, O(n log n)."""
    return sorted(records, key=key, reverse=reverse)


def group_by(records: Iterable[GradeRecord], key: KeyFunc) -> dict[str, list[GradeRecord]]:
    """Universal grouping. defaultdict spares the 'if key not in dict' dance."""
    groups: defaultdict[str, list[GradeRecord]] = defaultdict(list)
    for r in records:
        groups[key(r)].append(r)
    return dict(groups)


def nested_grouping(records: Iterable[GradeRecord]) -> dict[str, dict[str, list[GradeRecord]]]:
    """Group -> discipline -> records. Dict comprehension over a first-level grouping."""
    return {
        group: group_by(members, lambda r: r.discipline)
        for group, members in group_by(records, lambda r: r.group).items()
    }


def index_by_student(records: Iterable[GradeRecord]) -> dict[str, list[GradeRecord]]:
    """Dict index: O(n) to build, then O(1) average per lookup instead of O(n)."""
    return group_by(records, lambda r: r.student)


def find_linear(records: Iterable[GradeRecord], student: str) -> list[GradeRecord]:
    """The slow way, kept for the complexity experiment: scans everything, O(n)."""
    return [r for r in records if r.student == student]


def count_records_by_group(records: Iterable[GradeRecord]) -> Counter[str]:
    """Counter over a generator expression: no intermediate list."""
    return Counter(r.group for r in records)


def students_per_group(records: Iterable[GradeRecord]) -> dict[str, int]:
    """Dict comprehension; the inner set comprehension de-duplicates students."""
    return {group: len({r.student for r in members}) for group, members in group_by(records, lambda r: r.group).items()}
