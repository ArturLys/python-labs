"""Threads and processes: split the students into chunks, compute mergeable partial results, merge.

Partial results are designed so that merging is exact: sums, sums of squares, min/max, per-group sums and
counts, and a chunk ranking (sorted runs) that the final sort merges with the same key as the baseline sort.

Two payload shapes are supported: the Student objects themselves (fine for threads, expensive to pickle for
processes) and "columns" (a list of grades + a list of small group ids), which cross the process boundary
cheaply.
"""

from __future__ import annotations

import sys
import threading
from collections.abc import Iterable, Sequence
from itertools import chain
from concurrent.futures import Executor, ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass, field
from math import inf, sqrt

from student_manager.models import Student
from student_manager.perf.baseline import Stats

GroupKey = str | int


@dataclass(slots=True)
class Partial:
    count: int = 0
    total: float = 0.0
    squares: float = 0.0
    minimum: float = inf
    maximum: float = -inf
    group_sum: dict[GroupKey, float] = field(default_factory=dict)
    group_count: dict[GroupKey, int] = field(default_factory=dict)
    neg_grades: list[float] = field(default_factory=list)  # -grade, ascending (= grades descending)
    indices: list[int] = field(default_factory=list)       # global student index in the same order


@dataclass(frozen=True, slots=True)
class Columns:
    grades: list[float]
    group_ids: list[int]
    codes: list[str]


def to_columns(students: Sequence[Student]) -> Columns:
    codes = sorted({s.group for s in students})
    index = {code: i for i, code in enumerate(codes)}
    return Columns([s.average_grade for s in students], [index[s.group] for s in students], codes)


def split(students: Sequence[Student], parts: int) -> list[tuple[int, Sequence[Student]]]:
    """(offset, chunk) pairs; the offset keeps ranking indices global."""
    size = max(1, -(-len(students) // parts))
    return [(start, students[start:start + size]) for start in range(0, len(students), size)]


def _accumulate(grades: Iterable[float], keys: Iterable[GroupKey], offset: int) -> Partial:
    total, squares, low, high = 0.0, 0.0, inf, -inf
    group_sum: dict[GroupKey, float] = {}
    group_count: dict[GroupKey, int] = {}
    neg: list[float] = []
    for grade, key in zip(grades, keys, strict=True):
        total += grade
        squares += grade * grade
        if grade < low:
            low = grade
        if grade > high:
            high = grade
        group_sum[key] = group_sum.get(key, 0.0) + grade
        group_count[key] = group_count.get(key, 0) + 1
        neg.append(-grade)
    order = sorted(range(len(neg)), key=neg.__getitem__)  # stable: equal grades keep input order
    return Partial(len(neg), total, squares, low, high, group_sum, group_count,
                   [neg[i] for i in order], [i + offset for i in order])


def partial_stats(chunk: Sequence[Student], offset: int) -> Partial:
    """Same as _accumulate, written out for Student objects so that no generator sits in the hot loop."""
    total, squares, low, high = 0.0, 0.0, inf, -inf
    group_sum: dict[GroupKey, float] = {}
    group_count: dict[GroupKey, int] = {}
    neg: list[float] = []
    for student in chunk:
        grade = student.average_grade
        code = student.group
        total += grade
        squares += grade * grade
        if grade < low:
            low = grade
        if grade > high:
            high = grade
        group_sum[code] = group_sum.get(code, 0.0) + grade
        group_count[code] = group_count.get(code, 0) + 1
        neg.append(-grade)
    order = sorted(range(len(neg)), key=neg.__getitem__)
    return Partial(len(chunk), total, squares, low, high, group_sum, group_count,
                   [neg[i] for i in order], [i + offset for i in order])


def partial_stats_columns(grades: list[float], group_ids: list[int], offset: int) -> Partial:
    return _accumulate(grades, group_ids, offset)


def merge(parts: Iterable[Partial], codes: Sequence[str] | None = None) -> Stats:
    parts = list(parts)
    count = sum(p.count for p in parts)
    if count == 0:
        raise ValueError("порожній набір студентів")
    total = sum(p.total for p in parts)
    squares = sum(p.squares for p in parts)
    mean = total / count
    variance = max(squares / count - mean * mean, 0.0)
    sums: dict[GroupKey, float] = {}
    counts: dict[GroupKey, int] = {}
    for p in parts:
        for key, value in p.group_sum.items():
            sums[key] = sums.get(key, 0.0) + value
            counts[key] = counts.get(key, 0) + p.group_count[key]
    def name(key: GroupKey) -> str:
        return codes[int(key)] if codes is not None else str(key)

    group_means = dict(sorted((name(key), sums[key] / counts[key]) for key in sums))
    # k sorted runs -> one list; Timsort detects the runs and merges them in C (heapq.merge would do it in Python)
    neg = list(chain.from_iterable(p.neg_grades for p in parts))
    indices = list(chain.from_iterable(p.indices for p in parts))
    ranking = [indices[i] for i in sorted(range(len(neg)), key=neg.__getitem__)]
    return Stats(count, mean, min(p.minimum for p in parts), max(p.maximum for p in parts), sqrt(variance),
                 group_means, ranking)


def stats_threads(students: Sequence[Student], workers: int = 4) -> Stats:
    """ThreadPoolExecutor: the chunks are processed by threads that share one interpreter (and one GIL)."""
    pieces = split(students, workers)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return merge(pool.map(partial_stats, [c for _, c in pieces], [o for o, _ in pieces]))


def stats_processes(students: Sequence[Student], workers: int = 4) -> Stats:
    """ProcessPoolExecutor, naive: Student objects are pickled to the workers, a new pool every call."""
    pieces = split(students, workers)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        return merge(pool.map(partial_stats, [c for _, c in pieces], [o for o, _ in pieces]))


def stats_processes_columns(columns: Columns, workers: int = 4, pool: Executor | None = None) -> Stats:
    """ProcessPoolExecutor, tuned: primitive columns cross the boundary, and an existing (warm) pool is reused."""
    n = len(columns.grades)
    size = max(1, -(-n // workers))
    offsets = list(range(0, n, size))
    grades = [columns.grades[o:o + size] for o in offsets]
    ids = [columns.group_ids[o:o + size] for o in offsets]
    if pool is None:
        with ProcessPoolExecutor(max_workers=workers) as own:
            return merge(own.map(partial_stats_columns, grades, ids, offsets), columns.codes)
    return merge(pool.map(partial_stats_columns, grades, ids, offsets), columns.codes)


def stats_raw_threads(students: Sequence[Student], workers: int = 4) -> Stats:
    """The same with threading.Thread by hand: start/join and a Lock around the shared result list."""
    results: list[Partial] = []
    lock = threading.Lock()

    def work(chunk: Sequence[Student], offset: int) -> None:
        part = partial_stats(chunk, offset)  # computed outside the lock: long, no shared state
        with lock:                           # critical section: the shared list
            results.append(part)

    threads = [threading.Thread(target=work, args=(chunk, offset)) for offset, chunk in split(students, workers)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return merge(results)


# --- race condition demo -----------------------------------------------------------------------------------------


class Counter:
    def __init__(self) -> None:
        self.value = 0
        self.lock = threading.Lock()

    def increment_unsafe(self) -> None:
        current = self.value                 # read
        self.value = self._plus_one(current)  # write; the call in between is where the interpreter may switch
                                             # threads, so another thread's write gets overwritten (lost update)

    @staticmethod
    def _plus_one(value: int) -> int:
        return value + 1

    def increment_safe(self) -> None:
        with self.lock:
            self.value += 1


def race(increments: int, threads: int = 4, *, use_lock: bool, switch_interval: float | None = None) -> int:
    """Every thread adds `increments`. Without the lock updates get lost whenever the interpreter switches
    threads between the read and the write; a small `switch_interval` makes that happen often."""
    counter = Counter()
    step = counter.increment_safe if use_lock else counter.increment_unsafe

    def work() -> None:
        for _ in range(increments):
            step()

    previous = sys.getswitchinterval()
    if switch_interval is not None:
        sys.setswitchinterval(switch_interval)
    try:
        pool = [threading.Thread(target=work) for _ in range(threads)]
        for t in pool:
            t.start()
        for t in pool:
            t.join()
    finally:
        sys.setswitchinterval(previous)
    return counter.value
