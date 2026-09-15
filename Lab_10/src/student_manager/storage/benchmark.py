"""Experiments: strict vs tolerant on 1 000 valid + 10 invalid records, and eager vs streaming CSV
reading on 10 000 / 100 000 / 500 000 records with the peak memory from tracemalloc."""

from __future__ import annotations

import csv
import gc
import tracemalloc
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from student_manager.storage.context import open_text
from student_manager.storage.dataset import write_large_csv
from student_manager.storage.dto import Row
from student_manager.storage.exceptions import RecordValidationError
from student_manager.storage.exporters import write_rows
from student_manager.storage.services import STRICT, TOLERANT, ImportStatistics, import_students

SIZES: tuple[int, ...] = (10_000, 100_000, 500_000)
MIB = 1024 * 1024


@dataclass(frozen=True, slots=True)
class PolicyRun:
    mode: str
    total: int
    valid: int
    invalid: int
    exported: int
    outcome: str
    output_exists: bool


def strict_vs_tolerant(data_dir: Path, *, valid: int = 1_000, invalid: int = 10) -> list[PolicyRun]:
    """The same file, the same code, only the policy differs."""
    source = write_large_csv(data_dir / "exp1_students.csv", valid=valid, invalid=invalid)
    runs = []
    for policy in (STRICT, TOLERANT):
        statistics = ImportStatistics()
        output = data_dir / f"exp1_{policy.mode}.json"
        output.unlink(missing_ok=True)
        try:
            rows = import_students(source, policy=policy, statistics=statistics)
            exported = write_rows((row.to_dict() for row in rows), output)
        except RecordValidationError as error:
            exported = 0
            outcome = f"перервано ({error.location})"
        else:
            outcome = "завершено успішно"
        runs.append(
            PolicyRun(
                policy.mode, statistics.total, statistics.valid, statistics.invalid, exported, outcome, output.exists()
            )
        )
    return runs


def format_policy_table(runs: list[PolicyRun]) -> str:
    strict, tolerant = runs
    lines = [f"{'Параметр':<24}{'Strict':>26}{'Tolerant':>26}", "-" * 76]
    lines += [
        f"{'Оброблено записів':<24}{strict.total:>26}{tolerant.total:>26}",
        f"{'Valid':<24}{strict.valid:>26}{tolerant.valid:>26}",
        f"{'Invalid':<24}{strict.invalid:>26}{tolerant.invalid:>26}",
        f"{'Exported':<24}{strict.exported:>26}{tolerant.exported:>26}",
        f"{'Завершення':<24}{strict.outcome:>26}{tolerant.outcome:>26}",
        f"{'Файл результату':<24}{'є' if strict.output_exists else 'немає':>26}{'є' if tolerant.output_exists else 'немає':>26}",
    ]
    return "\n".join(lines)


def eager_import(path: Path) -> list[Row]:
    """Everything in memory at once: list(csv.DictReader(...))."""
    with open_text(path, "r") as file:
        return list(csv.DictReader(file))


def streaming_import(path: Path) -> Iterator[Row]:
    """One row at a time; the file stays open only while the consumer iterates."""
    with open_text(path, "r") as file:
        yield from csv.DictReader(file)


def measure(operation: Callable[[], int]) -> tuple[int, float, int]:
    """(rows counted, seconds, peak bytes) under tracemalloc; gc first so the previous run's garbage does not count."""
    gc.collect()
    tracemalloc.start()
    start = perf_counter()
    count = operation()
    elapsed = perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return count, elapsed, peak


@dataclass(frozen=True, slots=True)
class MemoryRun:
    records: int
    eager_seconds: float
    streaming_seconds: float
    eager_peak: int
    streaming_peak: int


def eager_vs_streaming(data_dir: Path, sizes: tuple[int, ...] = SIZES) -> list[MemoryRun]:
    runs = []
    for size in sizes:
        path = write_large_csv(data_dir / f"exp2_{size}.csv", valid=size)
        _, eager_seconds, eager_peak = measure(lambda: len(eager_import(path)))
        _, streaming_seconds, streaming_peak = measure(lambda: sum(1 for _ in streaming_import(path)))
        runs.append(MemoryRun(size, eager_seconds, streaming_seconds, eager_peak, streaming_peak))
        path.unlink()  # 500 000 rows is ~35 MB; no need to keep it
    return runs


def format_memory_table(runs: list[MemoryRun]) -> str:
    lines = [
        f"{'records':>9} {'eager, s':>10} {'stream, s':>10} {'eager MiB':>11} {'stream MiB':>11} {'ratio':>7}",
        "-" * 63,
    ]
    lines += [
        f"{r.records:>9,} {r.eager_seconds:>10.3f} {r.streaming_seconds:>10.3f} "
        f"{r.eager_peak / MIB:>11.2f} {r.streaming_peak / MIB:>11.2f} {r.eager_peak / r.streaming_peak:>6.0f}x"
        for r in runs
    ]
    return "\n".join(lines).replace(",", " ")
