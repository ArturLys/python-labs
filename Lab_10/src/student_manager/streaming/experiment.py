"""Experiment: eager (a list at every stage) vs lazy (a generator at every stage), 10 000 / 100 000 / 500 000 rows."""

from __future__ import annotations

import csv
import tracemalloc
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import TypeVar

from student_manager.streaming.aggregates import Stats, find_first, streaming_stats
from student_manager.streaming.filters import Predicate
from student_manager.streaming.generate import ensure_dataset
from student_manager.streaming.models import RawRow, StudentRecord
from student_manager.streaming.parsers import parse_record
from student_manager.streaming.pipeline import assemble, build_pipeline
from student_manager.streaming.readers import LineReader
from student_manager.streaming.transforms import tidy

SIZES: tuple[int, ...] = (10_000, 100_000, 500_000)
EARLY_SIZE = 1_000_000
MINIMUM = 85.0
T = TypeVar("T")


# ------------------------------------------------------------------ eager
def read_all_rows(path: Path) -> list[RawRow]:
    """Eager source: the whole file becomes a list of dicts before anything else happens."""
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def _parse_or_none(row: RawRow) -> StudentRecord | None:
    try:
        return parse_record(row)
    except ValueError:
        return None


def eager_records(path: Path, minimum: float = MINIMUM) -> list[StudentRecord]:
    """Eager pipeline: every stage returns a full list, so several copies of the data coexist at the peak."""
    rows = read_all_rows(path)
    parsed = [_parse_or_none(row) for row in rows]
    valid = [record for record in parsed if record is not None]
    clean = [tidy(record) for record in valid]
    return [record for record in clean if record.grade >= minimum]


def eager_stats(path: Path, minimum: float = MINIMUM) -> Stats:
    return streaming_stats(eager_records(path, minimum))


# ------------------------------------------------------------------ lazy
def lazy_stats(path: Path, minimum: float = MINIMUM) -> Stats:
    """Lazy pipeline drained by the aggregation sink; one record is alive at a time."""
    return streaming_stats(build_pipeline(path, minimum))


def first_lazy(path: Path, minimum: float = MINIMUM) -> StudentRecord:
    """First record of the lazy pipeline; close() makes read_lines() release the file now, not «eventually»."""
    pipeline = build_pipeline(path, minimum)
    try:
        return next(pipeline)
    finally:
        pipeline.close()


# ------------------------------------------------------------------ measuring
def timed(function: Callable[[], T]) -> tuple[T, float]:
    """(result, elapsed seconds) of one call."""
    started = perf_counter()
    result = function()
    return result, perf_counter() - started


def peak_memory(function: Callable[[], T]) -> tuple[T, int]:
    """(result, peak bytes allocated by Python objects). tracemalloc slows the code 2-3x, so elapsed time
    is always taken from a separate, untraced run."""
    tracemalloc.start()
    try:
        result = function()
        return result, tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


@dataclass(frozen=True)
class Measurement:
    rows: int
    eager_time: float
    lazy_time: float
    eager_peak: int
    lazy_peak: int
    eager_first: float
    lazy_first: float


def compare(path: Path, rows: int, minimum: float = MINIMUM) -> Measurement:
    """Same file, same stages, same result: only the evaluation strategy differs."""
    eager, eager_time = timed(lambda: eager_stats(path, minimum))
    lazy, lazy_time = timed(lambda: lazy_stats(path, minimum))
    if eager != lazy:
        raise AssertionError("eager and lazy pipelines disagree")
    _, eager_peak = peak_memory(lambda: eager_stats(path, minimum))
    _, lazy_peak = peak_memory(lambda: lazy_stats(path, minimum))
    _, eager_first = timed(lambda: eager_records(path, minimum)[0])
    _, lazy_first = timed(lambda: first_lazy(path, minimum))
    return Measurement(rows, eager_time, lazy_time, eager_peak, lazy_peak, eager_first, lazy_first)


def run(data_dir: Path, sizes: tuple[int, ...] = SIZES) -> list[Measurement]:
    return [compare(ensure_dataset(data_dir / f"students_{rows}.csv", rows), rows) for rows in sizes]


@dataclass(frozen=True)
class EarlyResult:
    rows: int
    lazy_hit: StudentRecord | None
    lazy_time: float
    lines_pulled: int
    eager_hit: StudentRecord | None
    eager_time: float


def early_termination(path: Path, rows: int, predicate: Predicate, minimum: float = MINIMUM) -> EarlyResult:
    """find_first() on the lazy pipeline vs filtering the full eager list; LineReader shows how far lazy got."""
    reader = LineReader(path)
    lazy_hit, lazy_time = timed(lambda: find_first(assemble(reader, minimum), predicate))
    lines_pulled = reader.lines_read
    reader.close()

    def eager_search() -> StudentRecord | None:
        matches = [record for record in eager_records(path, minimum) if predicate(record)]
        return matches[0] if matches else None

    eager_hit, eager_time = timed(eager_search)
    return EarlyResult(rows, lazy_hit, lazy_time, lines_pulled, eager_hit, eager_time)


# ------------------------------------------------------------------ formatting
def fmt_int(value: int) -> str:
    """Thousands separated by a space, the way numbers are written in Ukrainian: 1 000 000."""
    return f"{value:,}".replace(",", " ")


def fmt_seconds(seconds: float) -> str:
    if seconds < 0.001:
        return f"{seconds * 1e6:.0f} µs"
    if seconds < 1:
        return f"{seconds * 1e3:.1f} ms"
    return f"{seconds:.2f} s"


def fmt_bytes(size: int) -> str:
    return f"{size / 2**20:.2f} MB" if size >= 2**20 else f"{size / 2**10:.0f} KB"


def format_table(results: list[Measurement]) -> str:
    header = (
        f"{'rows':>9} {'eager time':>11} {'lazy time':>11} {'eager peak':>11} {'lazy peak':>11} "
        f"{'eager 1st':>11} {'lazy 1st':>11}"
    )
    lines = [header, "-" * len(header)]
    for m in results:
        lines.append(
            f"{fmt_int(m.rows):>9} {fmt_seconds(m.eager_time):>11} {fmt_seconds(m.lazy_time):>11} "
            f"{fmt_bytes(m.eager_peak):>11} {fmt_bytes(m.lazy_peak):>11} "
            f"{fmt_seconds(m.eager_first):>11} {fmt_seconds(m.lazy_first):>11}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    print(format_table(run(Path("data"))))
