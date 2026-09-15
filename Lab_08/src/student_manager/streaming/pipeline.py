"""The lazy pipeline: CSV -> read -> clean -> parse -> validate -> normalize -> filter -> sink."""

from __future__ import annotations

import csv
import logging
from collections.abc import Generator, Iterable, Iterator
from itertools import chain
from pathlib import Path
from typing import TypeVar

from student_manager.streaming.filters import with_min_grade
from student_manager.streaming.models import COLUMNS, StudentRecord
from student_manager.streaming.parsers import ValidationReport, clean_lines, parse_rows, validate
from student_manager.streaming.readers import read_lines
from student_manager.streaming.transforms import normalize

log = logging.getLogger("student_manager.streaming")
T = TypeVar("T")


def traced(name: str, items: Iterable[T]) -> Generator[T, None, None]:
    """Logging wrapper around a stage: counts what passed and reports it once the stage is drained.

    If the consumer stops early (islice, find_first) the stage is never drained and nothing is logged:
    a generator only runs as far as it is pulled.
    """
    passed = 0
    for item in items:
        passed += 1
        yield item
    log.info("stage %-8s drained, %d items passed", name, passed)


def assemble(lines: Iterable[str], minimum: float = 0.0,
             report: ValidationReport | None = None) -> Generator[StudentRecord, None, None]:
    """Chain the stages over any source of lines; nothing runs until the consumer asks for a record."""
    rows = parse_rows(clean_lines(traced("read", lines)))
    valid = traced("validate", validate(rows, report))
    return traced("filter", with_min_grade(normalize(valid), minimum))


def build_pipeline(path: Path, minimum: float = 0.0,
                   report: ValidationReport | None = None) -> Generator[StudentRecord, None, None]:
    """The pipeline over one CSV file. The file is not even opened until the first next(); close() releases it."""
    return assemble(read_lines(path), minimum, report)


def build_multi_pipeline(paths: Iterable[Path], minimum: float = 0.0) -> Iterator[StudentRecord]:
    """One stream over several files: chain.from_iterable opens each file only when its turn comes."""
    return chain.from_iterable(build_pipeline(path, minimum) for path in paths)


def export_csv(records: Iterable[StudentRecord], path: Path) -> int:
    """Streaming sink: write records to a new CSV as they arrive; returns how many were written."""
    written = 0
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(COLUMNS)
        for record in records:
            writer.writerow(record)
            written += 1
    return written
